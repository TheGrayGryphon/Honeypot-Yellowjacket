# Discord bot configuration
# Fill in these values before running the bot, keep the quotation marks.
BOT_TOKEN = "BOT_TOKEN_HERE"

# Channel IDs are integers. Example: 123456789012345678
HONEYPOT_CHANNEL_ID = 0
LOG_CHANNEL_ID = 0

# How far back to delete a user's messages (in hours)
DELETE_LOOKBACK_HOURS = 24

# If True, ban the user after triggering. If False, only delete messages.
BAN_ON_TRIGGER = True

# Channel warmer options (sends a message then quickly deletes it)
CHANNEL_WARMER_ENABLED = False
CHANNEL_WARMER_RUN_ON_STARTUP = True
CHANNEL_WARMER_DELETE_DELAY_SECONDS = 1
CHANNEL_WARMER_MESSAGE = "Keeping the honeypot channel active!"

# Message templates
# Available fields: author, author_id, author_mention, deleted_count, lookback_hours, stung_count, message_content, attachments
LOG_FELL_FOR_HONEYPOT = (
    "{author_mention} ({author_id}) fell for the honeypot channel. "
    "Deleted {deleted_count} message(s) from the past {lookback_hours} hour(s)."
)
LOG_NEEDS_DELETE = "{author_mention} ({author_id}) needs to be deleted."
LOG_BANNED = "{author_mention} has been banned."
LOG_MESSAGE_COPY = "Message copy: {message_content}\nAttachments: {attachments}"
HONEYPOT_STUNG_EMBED = "I have stung {stung_count} account(s) in defense of this honeypot."

# Stung counter persistence
STUNG_COUNT_FILE = "stung_count.json"
