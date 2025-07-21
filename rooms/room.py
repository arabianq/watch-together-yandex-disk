import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import config
import globals
from rooms.state import PlayerState


@dataclass(frozen=False)
class Room:
    uid: str
    tmdb_id: int

    player_position: float = 0.0
    player_state: PlayerState = PlayerState.PAUSED

    current_season: int | None = None
    current_episode: int | None = None

    connected_users: list[str] = field(default_factory=list)
    messages: list[tuple[str, str]] = field(default_factory=list)

    def __init__(self, uid: str, tmdb_id: int):
        self.uid = uid
        self.tmdb_id = tmdb_id

        self.player_position = 0.0
        self.player_state = PlayerState.PAUSED

        self.current_season = None
        self.current_episode = None

        self.connected_users = []
        self.messages = []

        content = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]
        if content.type == "tv":
            self.current_season = 1
            self.current_episode = 1

        self.last_update = datetime.now()

    async def _delete(self):
        await globals.ROOMS_DATABASE.delete_room(self.uid)

    async def _update(self):
        if not self.connected_users:
            for _ in range(100):
                await asyncio.sleep(0.1)
                if self.connected_users:
                    break

            if not self.connected_users:
                logging.info("No users connected to %s, deleting it", self.uid)
                await self._delete()

        now = datetime.now()

        if self.player_state == PlayerState.PLAYING:
            self.player_position += (now - self.last_update).total_seconds()

        self.last_update = now

    async def update(self):
        self.last_update = datetime.now()

        while True:
            await asyncio.sleep(config.ROOMS_UPDATE_INTERVAL_SECONDS)
            await self._update()

    def pause(self):
        self.player_state = PlayerState.PAUSED

    def play(self):
        self.player_state = PlayerState.PLAYING

    def stop(self):
        self.player_state = PlayerState.STOPPED

    def seek(self, seconds: float):
        self.player_position = seconds
        self.last_update = datetime.now()
