# discord-garmin-tracker

A Discord bot that monitors a Gmail inbox for Garmin LiveTrack share emails and automatically posts the session link to a configured Discord channel, optionally pinging a designated role.

## How it works

1. The bot polls Gmail via IMAP (using a Google App Password) at a configurable interval.
2. When it spots an unread email from `noreply@garmin.com` with "livetrack" in the subject, it extracts the `livetrack.garmin.com` URL.
3. It posts the URL to every Discord server's configured channel, mentioning the configured role.

## Requirements

- A Gmail account with [2-Step Verification](https://myaccount.google.com/security) enabled
- A [Google App Password](https://myaccount.google.com/apppasswords) for that account
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- Docker (recommended) **or** Python 3.12+

## Quick start (Docker)

```bash
# 1. Clone the repo
git clone https://github.com/alexkibler/discord-garmin-tracker.git
cd discord-garmin-tracker

# 2. Configure environment variables
cp .env.example .env
$EDITOR .env          # fill in DISCORD_BOT_TOKEN, GMAIL_ADDRESS, GMAIL_APP_PASSWORD

# 3. Build & run
docker compose up -d
```

Configuration (channel and role) is stored in a named Docker volume (`bot_data`) and persists across restarts.

## Quick start (local Python)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
$EDITOR .env

python main.py
```

## Discord setup

### Bot permissions

When creating your bot in the [Discord Developer Portal](https://discord.com/developers/applications), make sure to:

1. Enable the bot under **Bot** → add a bot.
2. Under **OAuth2 → URL Generator**, select scopes: `bot`, `applications.commands`.
3. Under **Bot Permissions**, select at minimum:
   - **Send Messages**
   - **Mention Everyone** (needed to ping roles that aren't `@everyone`)
4. Invite the bot to your server using the generated URL.

### Admin slash commands

These commands are restricted to server **Administrators**.

| Command | Description |
|---|---|
| `/livetrack set-channel #channel` | Set the channel where links are posted |
| `/livetrack set-role @role` | Set the role that gets pinged |
| `/livetrack status` | Show the current configuration |

> **Tip:** You can run `/livetrack set-channel` without `/livetrack set-role` if you don't want role pings.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | Yes | — | Discord bot token |
| `GMAIL_ADDRESS` | Yes | — | Gmail address to monitor |
| `GMAIL_APP_PASSWORD` | Yes | — | [Google App Password](https://myaccount.google.com/apppasswords) |
| `POLL_INTERVAL` | No | `60` | Seconds between inbox checks |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `CONFIG_PATH` | No | `/data/config.json` | Path for persisted guild settings |

## Gmail App Password setup

1. Go to your Google Account → **Security**.
2. Ensure **2-Step Verification** is on.
3. Search for **App passwords** and create one (select "Mail" + "Other device").
4. Copy the 16-character password into `GMAIL_APP_PASSWORD` in your `.env`.

> The bot only reads **unread** emails from `noreply@garmin.com`. It does not mark emails as read or delete them.

## License

Apache 2.0 – see [LICENSE](LICENSE).
