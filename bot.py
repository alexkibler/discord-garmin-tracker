"""
Discord bot for posting Garmin LiveTrack links.

Admin slash commands
--------------------
/livetrack set-channel #channel
    Set the text channel where LiveTrack links will be posted.

/livetrack set-role @role
    Set the role that will be mentioned when a link is posted.

/livetrack status
    Show the currently configured channel and role.
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config_store import ConfigStore

logger = logging.getLogger(__name__)


class LiveTrackBot(commands.Bot):
    def __init__(self, config_store: ConfigStore):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.config_store = config_store
        self._livetrack_group = LiveTrackGroup(config_store)

    async def setup_hook(self):
        self.tree.add_command(self._livetrack_group)
        # Sync commands to all guilds the bot is in.  For large deployments
        # you could sync per-guild for instant propagation.
        await self.tree.sync()
        logger.info("Slash commands synced.")

    async def on_ready(self):
        logger.info("Logged in as %s (id=%s)", self.user, self.user.id)

    # ------------------------------------------------------------------
    # Called by the Gmail monitor when a new LiveTrack URL is found
    # ------------------------------------------------------------------

    async def post_livetrack(self, url: str):
        """Post a LiveTrack URL to every configured guild channel."""
        posted = 0
        for guild in self.guilds:
            cfg = self.config_store.get(guild.id)
            if cfg.channel_id is None:
                logger.debug(
                    "Guild %s (%d) has no channel configured, skipping.",
                    guild.name,
                    guild.id,
                )
                continue

            channel = guild.get_channel(cfg.channel_id)
            if channel is None:
                logger.warning(
                    "Channel %d not found in guild %s.", cfg.channel_id, guild.name
                )
                continue

            mention = f"<@&{cfg.role_id}> " if cfg.role_id else ""
            content = (
                f"{mention}A new Garmin LiveTrack session is available!\n{url}"
            )
            try:
                await channel.send(content)
                posted += 1
                logger.info(
                    "Posted LiveTrack URL to #%s in %s.", channel.name, guild.name
                )
            except discord.Forbidden:
                logger.error(
                    "Missing permission to send messages to #%s in %s.",
                    channel.name,
                    guild.name,
                )
            except discord.HTTPException as exc:
                logger.error("HTTP error posting to Discord: %s", exc)

        if posted == 0:
            logger.warning(
                "LiveTrack URL found but no guilds had a channel configured: %s", url
            )


# ---------------------------------------------------------------------------
# Slash command group
# ---------------------------------------------------------------------------


class LiveTrackGroup(app_commands.Group):
    """Commands for configuring the LiveTrack bot."""

    def __init__(self, config_store: ConfigStore):
        super().__init__(name="livetrack", description="Manage LiveTrack notifications")
        self.config_store = config_store

    # Permission check: only server administrators may use these commands
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(
                "These commands can only be used inside a server.", ephemeral=True
            )
            return False
        member = interaction.guild.get_member(interaction.user.id)
        if member is None or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need the **Administrator** permission to use these commands.",
                ephemeral=True,
            )
            return False
        return True

    # ------------------------------------------------------------------

    @app_commands.command(
        name="set-channel",
        description="Set the channel where LiveTrack links will be posted.",
    )
    @app_commands.describe(channel="The text channel to post links in")
    async def set_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        self.config_store.set_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            f"LiveTrack links will now be posted in {channel.mention}.",
            ephemeral=True,
        )
        logger.info(
            "Guild %d set LiveTrack channel to #%s (%d).",
            interaction.guild_id,
            channel.name,
            channel.id,
        )

    # ------------------------------------------------------------------

    @app_commands.command(
        name="set-role",
        description="Set the role that will be pinged when a LiveTrack link is posted.",
    )
    @app_commands.describe(role="The role to mention")
    async def set_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        self.config_store.set_role(interaction.guild_id, role.id)
        await interaction.response.send_message(
            f"{role.mention} will be pinged when a new LiveTrack link arrives.",
            ephemeral=True,
        )
        logger.info(
            "Guild %d set LiveTrack ping role to @%s (%d).",
            interaction.guild_id,
            role.name,
            role.id,
        )

    # ------------------------------------------------------------------

    @app_commands.command(
        name="status",
        description="Show the current LiveTrack notification configuration.",
    )
    async def status(self, interaction: discord.Interaction):
        cfg = self.config_store.get(interaction.guild_id)

        channel_text = (
            f"<#{cfg.channel_id}>" if cfg.channel_id else "*not set*"
        )
        role_text = (
            f"<@&{cfg.role_id}>" if cfg.role_id else "*not set*"
        )

        embed = discord.Embed(
            title="LiveTrack Notification Config",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Channel", value=channel_text, inline=False)
        embed.add_field(name="Ping role", value=role_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
