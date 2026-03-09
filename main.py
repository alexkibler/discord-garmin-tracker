"""
Entry point for the Garmin LiveTrack Discord bot.

Required environment variables
-------------------------------
DISCORD_BOT_TOKEN   Discord bot token
GMAIL_ADDRESS       Gmail address to monitor
GMAIL_APP_PASSWORD  Google App Password for the above account

Optional environment variables
-------------------------------
POLL_INTERVAL       How often to check Gmail in seconds (default: 60)
CONFIG_PATH         Path to the JSON config file (default: /data/config.json)
LOG_LEVEL           Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from bot import LiveTrackBot
from config_store import ConfigStore
from gmail_monitor import GmailMonitor

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"ERROR: Required environment variable '{name}' is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def _setup_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main():
    _setup_logging()
    logger = logging.getLogger(__name__)

    discord_token = _require_env("DISCORD_BOT_TOKEN")
    gmail_address = _require_env("GMAIL_ADDRESS")
    gmail_password = _require_env("GMAIL_APP_PASSWORD")
    poll_interval = int(os.getenv("POLL_INTERVAL", "60"))

    config_store = ConfigStore()
    discord_bot = LiveTrackBot(config_store=config_store)

    gmail_monitor = GmailMonitor(
        email_address=gmail_address,
        app_password=gmail_password,
        callback=discord_bot.post_livetrack,
        poll_interval=poll_interval,
    )

    async def run_monitor():
        # Wait until the bot is ready before starting the monitor so that
        # post_livetrack can immediately send messages if a URL is found.
        await discord_bot.wait_until_ready()
        logger.info("Bot ready – starting Gmail monitor.")
        await gmail_monitor.run()

    async with discord_bot:
        discord_bot.loop.create_task(run_monitor())
        await discord_bot.start(discord_token)


if __name__ == "__main__":
    asyncio.run(main())
