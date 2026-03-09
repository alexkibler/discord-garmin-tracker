"""
Persistent storage for per-guild bot configuration (channel, role).

Data is saved to a JSON file so settings survive container restarts.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(os.getenv("CONFIG_PATH", "/data/config.json"))


class GuildConfig:
    """Holds the channel and role IDs for a single Discord guild."""

    def __init__(self, channel_id: Optional[int] = None, role_id: Optional[int] = None):
        self.channel_id = channel_id
        self.role_id = role_id

    def to_dict(self) -> dict:
        return {"channel_id": self.channel_id, "role_id": self.role_id}

    @classmethod
    def from_dict(cls, data: dict) -> "GuildConfig":
        return cls(
            channel_id=data.get("channel_id"),
            role_id=data.get("role_id"),
        )


class ConfigStore:
    """
    Loads and saves guild configurations to a JSON file.

    The file schema is::

        {
            "<guild_id>": {"channel_id": 123, "role_id": 456},
            ...
        }
    """

    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self._data: dict[str, GuildConfig] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        if not self.path.exists():
            logger.info("Config file not found at %s, starting fresh.", self.path)
            return
        try:
            raw = json.loads(self.path.read_text())
            self._data = {gid: GuildConfig.from_dict(v) for gid, v in raw.items()}
            logger.info("Loaded config for %d guild(s).", len(self._data))
        except Exception as exc:
            logger.error("Failed to load config from %s: %s", self.path, exc)

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {gid: cfg.to_dict() for gid, cfg in self._data.items()}
            self.path.write_text(json.dumps(payload, indent=2))
        except Exception as exc:
            logger.error("Failed to save config to %s: %s", self.path, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, guild_id: int) -> GuildConfig:
        return self._data.get(str(guild_id), GuildConfig())

    def set_channel(self, guild_id: int, channel_id: int):
        cfg = self._data.setdefault(str(guild_id), GuildConfig())
        cfg.channel_id = channel_id
        self._save()

    def set_role(self, guild_id: int, role_id: int):
        cfg = self._data.setdefault(str(guild_id), GuildConfig())
        cfg.role_id = role_id
        self._save()

    def all_guilds(self) -> list[int]:
        return [int(gid) for gid in self._data.keys()]
