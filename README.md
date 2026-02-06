# Yellowjacket Honeypot Bot
Yes, this was written pretty much entirely by generative AI. Yes, I did due dilligence to see if any other human options were possible. I looked at other existing bots but their creators either did not want to share the bot, or did not want to update their bot to account for the new (mid 2025ish) attack vector of scammers only posting images at a slow enough rate to not be caught by user management bots. 

## What it does
- Monitors a honeypot channel and reacts to any text message or image-only message.
- Deletes the user’s recent messages across the guild for the configured lookback window.
- Optionally bans the user if `BAN_ON_TRIGGER = True`.
- Logs actions to the log channel and keeps track of the number of victims in the honeypot channel.

## Create the bot in the Discord Developer Portal
1. Go to the Developer Portal and create a new application.
2. Open the **Bot** tab, click **Add Bot**, then **Reset Token** and copy the token. Save the token in `config.py`, keep the quotation marks.
3. Go to **OAuth2 > URL Generator**, select the `bot` scope and the permissions listed below, then open the generated URL to invite the bot to your server.

Developer Portal: https://discord.com/developers/applications
Guide for invite URL generation: https://discordjs.guide/legacy/preparations/adding-your-app

## Developer Portal settings (required)
Enable/Select the **Message Content Intent** for this bot under **Bot > Privileged Gateway Intents**.

Minimum recommended permissions when generating the OAuth2 invite URL:
- View Channel
- Read Message History
- Manage Messages
- Send Messages
- Embed Links
- (Optional) Ban Members — required if `BAN_ON_TRIGGER = True`

Also ensure that the bot is able to view all channels in your discord, or at least has view/manage messages in all the channels that new users have access to. 

Ensure that the bot is able to view/send messages in the log and honeypot channel by viewing your server as its role.

Permissions reference:
- https://support.discord.com/hc/en-us/articles/10543994968087-Channel-Permissions-Settings-101
- https://discord.com/moderation/1500000176222-201%3A-Permissions-on-Discord
Privileged intents info:
- https://support-dev.discord.com/hc/en-us/articles/4404772028055-Message-Content-Privileged-Intent-FAQ
- https://support-dev.discord.com/hc/en-us/articles/6207308062871-What-are-Privileged-Intents
- https://support-dev.discord.com/hc/en-us/articles/6205754771351-How-do-I-get-Privileged-Intents-for-my-bot

## Local setup and launch (virtual environment)
### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Configure
Edit `config.py` in any IDE and set:
- `BOT_TOKEN`
- `HONEYPOT_CHANNEL_ID`
- `LOG_CHANNEL_ID`
- Any optional flags (e.g., `BAN_ON_TRIGGER`, `CHANNEL_WARMER_ENABLED`)

### Run
```bash
python honeypot_bot.py
```

Notes:
- The bot creates `stung_count.json` to persist the stung count across restarts.
