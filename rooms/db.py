import logging

from nicegui import background_tasks

from rooms.room import Room
from rooms.utils import generate_uid


class RoomsDB:
    def __init__(self):
        self.rooms = []
        self.by_uid: dict[str, Room] = {}

    async def create_room(self, tmdb_id: int) -> Room:
        logging.info("Creating new room")

        uid = generate_uid()
        while uid in self.by_uid.keys():
            uid = generate_uid()

        room = Room(uid=uid, tmdb_id=tmdb_id)
        self.rooms.append(room)
        self.by_uid[uid] = room

        background_tasks.create_lazy(room.update(), name=f"room_update_{uid}")

        logging.info(f"Created new room {room.uid}")

        return room

    async def delete_room(self, uid: str):
        logging.info(f"Deleting room {uid}")

        background_tasks.lazy_tasks_running.get(f"room_update_{uid}").cancel()
        room = self.by_uid[uid]
        del self.by_uid[uid]
        self.rooms.remove(room)

        logging.info(f"Deleted room {uid}")
