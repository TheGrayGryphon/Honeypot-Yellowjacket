import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord

import config


def _is_image_only(message: discord.Message) -> bool:
    if message.content and message.content.strip():
        return False
    if not message.attachments:
        return False
    image_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif")
    for attachment in message.attachments:
        content_type = attachment.content_type or ""
        if content_type.startswith("image/"):
            continue
        if not attachment.filename.lower().endswith(image_exts):
            return False
    return True


def _seconds_until_midnight_utc() -> float:
    now = datetime.now(timezone.utc)
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(0.0, (next_midnight - now).total_seconds())


def _load_state():
    try:
        path = Path(config.STUNG_COUNT_FILE)
        if not path.exists():
            return 0, None
        data = json.loads(path.read_text(encoding="utf-8"))
        value = int(data.get("stung_count", 0))
        msg_id = data.get("stung_message_id")
        if msg_id is None:
            msg_id = data.get("stung_embed_message_id")
        if msg_id is not None:
            try:
                msg_id = int(msg_id)
            except (TypeError, ValueError):
                msg_id = None
        return max(0, value), msg_id
    except Exception:
        return 0, None


def _save_state(value: int, message_id) -> None:
    try:
        path = Path(config.STUNG_COUNT_FILE)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps({"stung_count": value, "stung_message_id": message_id}),
            encoding="utf-8",
        )
        tmp_path.replace(path)
    except Exception:
        pass


async def delete_recent_messages(guild: discord.Guild, user: discord.abc.User, cutoff: datetime) -> int:
    deleted_count = 0
    me = guild.me
    for channel in guild.text_channels:
        # Skip channels where the bot can't read history or delete messages
        if me is not None:
            perms = channel.permissions_for(me)
            if not (perms.read_message_history and perms.view_channel and perms.manage_messages):
                continue

        try:
            async for msg in channel.history(after=cutoff, oldest_first=False, limit=None):
                if msg.author.id != user.id:
                    continue
                try:
                    await msg.delete()
                    deleted_count += 1
                except discord.Forbidden:
                    continue
                except discord.HTTPException:
                    # Avoid hard stop on transient API errors
                    await asyncio.sleep(1)
        except discord.Forbidden:
            continue
        except discord.HTTPException:
            await asyncio.sleep(1)

    return deleted_count


class HoneypotClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.stung_count, self._stung_message_id = _load_state()
        self._channel_warmer_task = None

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        await self._update_stung_embed()
        if config.CHANNEL_WARMER_ENABLED:
            if self._channel_warmer_task is None or self._channel_warmer_task.done():
                self._channel_warmer_task = asyncio.create_task(
                    self._channel_warmer_loop()
                )

    async def _get_honeypot_channel(self):
        channel = self.get_channel(config.HONEYPOT_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.fetch_channel(config.HONEYPOT_CHANNEL_ID)
            except discord.HTTPException:
                return None
        if not isinstance(channel, discord.TextChannel):
            return None
        return channel

    def _stung_embed_description_for(self, stung_count: int) -> str:
        return config.HONEYPOT_STUNG_EMBED.format(
            author="System",
            author_id=0,
            deleted_count=0,
            lookback_hours=config.DELETE_LOOKBACK_HOURS,
            stung_count=stung_count,
            message_content="",
            attachments="",
        )

    def _is_stung_embed_description(self, description: str) -> bool:
        template = config.HONEYPOT_STUNG_EMBED
        if "{stung_count}" in template:
            prefix, suffix = template.split("{stung_count}", 1)
            prefix = prefix.format(
                author="System",
                author_id=0,
                deleted_count=0,
                lookback_hours=config.DELETE_LOOKBACK_HOURS,
                stung_count="",
                message_content="",
                attachments="",
            )
            suffix = suffix.format(
                author="System",
                author_id=0,
                deleted_count=0,
                lookback_hours=config.DELETE_LOOKBACK_HOURS,
                stung_count="",
                message_content="",
                attachments="",
            )
            return description.startswith(prefix) and description.endswith(suffix)
        return description == self._stung_embed_description_for(self.stung_count)

    async def _find_stung_message(self, channel: discord.TextChannel):
        if self._stung_message_id and self.user is not None:
            try:
                msg = await channel.fetch_message(self._stung_message_id)
                if msg.author.id == self.user.id:
                    return msg
            except discord.HTTPException:
                pass
        try:
            async for msg in channel.history(limit=100, oldest_first=False):
                if self.user is None or msg.author.id != self.user.id:
                    continue
                for emb in msg.embeds:
                    if emb.description and self._is_stung_embed_description(emb.description):
                        self._stung_message_id = msg.id
                        _save_state(self.stung_count, self._stung_message_id)
                        return msg
        except discord.HTTPException:
            pass
        return None

    async def _update_stung_embed(self) -> None:
        channel = await self._get_honeypot_channel()
        if channel is None:
            return
        embed = discord.Embed(
            description=self._stung_embed_description_for(self.stung_count),
            color=discord.Color.red(),
        )
        msg = await self._find_stung_message(channel)
        if msg is not None:
            try:
                await msg.edit(embed=embed)
                return
            except discord.HTTPException:
                pass
        try:
            sent = await channel.send(embed=embed)
            self._stung_message_id = sent.id
            _save_state(self.stung_count, self._stung_message_id)
        except discord.HTTPException:
            pass

    async def _channel_warmer_once(self) -> None:
        channel = await self._get_honeypot_channel()
        if channel is None:
            return
        try:
            msg = await channel.send(config.CHANNEL_WARMER_MESSAGE)
            await asyncio.sleep(config.CHANNEL_WARMER_DELETE_DELAY_SECONDS)
            await msg.delete()
        except discord.HTTPException:
            pass

    async def _channel_warmer_loop(self) -> None:
        await self.wait_until_ready()
        if config.CHANNEL_WARMER_RUN_ON_STARTUP:
            await self._channel_warmer_once()
        while not self.is_closed():
            await asyncio.sleep(_seconds_until_midnight_utc())
            await self._channel_warmer_once()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            return
        if message.channel.id != config.HONEYPOT_CHANNEL_ID:
            return

        triggered = False
        if message.content and message.content.strip():
            triggered = True
        elif _is_image_only(message):
            triggered = True

        if not triggered:
            return

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=config.DELETE_LOOKBACK_HOURS)

        deleted_count = await delete_recent_messages(message.guild, message.author, cutoff)

        ban_failed = False
        ban_succeeded = False
        if config.BAN_ON_TRIGGER:
            try:
                await message.guild.ban(message.author, reason="Fell for honeypot channel")
                ban_succeeded = True
            except discord.Forbidden:
                ban_failed = True
            except discord.HTTPException:
                ban_failed = True

        log_channel = message.guild.get_channel(config.LOG_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):
            message_content = message.content.strip() if message.content and message.content.strip() else "(no text)"
            attachments = ", ".join(a.url for a in message.attachments) if message.attachments else "(none)"
            author_mention = message.author.mention
            log_text = config.LOG_FELL_FOR_HONEYPOT.format(
                author=message.author,
                author_id=message.author.id,
                author_mention=author_mention,
                deleted_count=deleted_count,
                lookback_hours=config.DELETE_LOOKBACK_HOURS,
                stung_count=self.stung_count,
                message_content=message_content,
                attachments=attachments,
            )
            log_text = log_text + "\n" + config.LOG_MESSAGE_COPY.format(
                author=message.author,
                author_id=message.author.id,
                author_mention=author_mention,
                deleted_count=deleted_count,
                lookback_hours=config.DELETE_LOOKBACK_HOURS,
                stung_count=self.stung_count,
                message_content=message_content,
                attachments=attachments,
            )
            try:
                await log_channel.send(
                    log_text,
                    allowed_mentions=discord.AllowedMentions(
                        users=[message.author], roles=False, everyone=False
                    ),
                )
            except discord.HTTPException:
                pass
            if ban_succeeded:
                try:
                    await log_channel.send(
                        config.LOG_BANNED.format(
                            author=message.author,
                            author_id=message.author.id,
                            author_mention=author_mention,
                            deleted_count=deleted_count,
                            lookback_hours=config.DELETE_LOOKBACK_HOURS,
                            stung_count=self.stung_count,
                            message_content=message_content,
                            attachments=attachments,
                        ),
                        allowed_mentions=discord.AllowedMentions(
                            users=[message.author], roles=False, everyone=False
                        ),
                    )
                except discord.HTTPException:
                    pass
            if ban_failed:
                try:
                    await log_channel.send(
                        config.LOG_NEEDS_DELETE.format(
                            author=message.author,
                            author_id=message.author.id,
                            author_mention=author_mention,
                            deleted_count=deleted_count,
                            lookback_hours=config.DELETE_LOOKBACK_HOURS,
                            stung_count=self.stung_count,
                            message_content=message_content,
                            attachments=attachments,
                        )
                        , allowed_mentions=discord.AllowedMentions(
                            users=[message.author], roles=False, everyone=False
                        )
                    )
                except discord.HTTPException:
                    pass

        self.stung_count += 1
        _save_state(self.stung_count, self._stung_message_id)
        await self._update_stung_embed()


def main() -> None:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True

    client = HoneypotClient(intents=intents)
    client.run(config.BOT_TOKEN)


if __name__ == "__main__":
    main()
