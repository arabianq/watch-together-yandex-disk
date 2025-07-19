import asyncio
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import aiofiles
import orjson

import config
from singleton import Singleton
from users.classes import User
from users.utils import is_inactive_too_long, decode_token, generate_uid


class UsersDB(metaclass=Singleton):
    def __init__(self, db_path: Path | str):
        self.path = Path(db_path)
        self.users = []
        self.by_uid = {}

    def _assign_users(self):
        self.by_uid = {}

        for user in self.users:
            self.by_uid[user.uid] = user

    async def auto_remove_inactive(self):
        while True:
            await asyncio.sleep(config.REMOVE_INACTIVE_USERS_INTERVAL_SECONDS)
            await self.remove_inactive()

    async def remove_inactive(self):
        logging.info("Removing inactive users")

        new_users = []
        for user in self.users:
            if not is_inactive_too_long(user):
                new_users.append(user)
                continue

            logging.info(f"Removing inactive user {user.uid}")

        self.users = new_users

        await self.save_to_disk()
        self._assign_users()

        logging.info("Finished Removing inactive users")

    async def get_user_by_token(self, token: str) -> User | None:
        user = decode_token(token)

        if user is None:
            return None

        if user.uid not in self.by_uid.keys():
            return None

        if is_inactive_too_long(user):
            await self.delete_user(user.uid)
            return None

        return user

    async def create_user(self, username: str) -> User:
        user = User(
            username=username,
            uid=generate_uid(username),
            last_activity=datetime.now(),
        )
        self.users.append(user)

        await self.save_to_disk()
        self._assign_users()

        logging.info("Created new user - %s", user.uid)

        return user

    async def delete_user(self, uid: str):
        user = self.by_uid.get(uid)

        if not user:
            return

        self.users.remove(user)

        await self.save_to_disk()
        self._assign_users()

        logging.info("Deleted user - %s", user.uid)

    async def update_user(self, uid: str):
        user = self.by_uid.get(uid)

        if not user:
            return

        self.users.remove(user)
        del self.by_uid[uid]

        user.last_activity = datetime.now()

        self.users.append(user)
        self.by_uid[uid] = user

        await self.save_to_disk()
        self._assign_users()

        logging.info("Updated user - %s", user.uid)

    async def save_to_disk(self):
        logging.info("Saving Users DB to disk")

        users = [asdict(user) for user in self.users]
        for i in range(len(users)):
            users[i]["last_activity"] = self.users[i]._last_activity_str
            del users[i]["_last_activity_str"]

        to_save = await asyncio.to_thread(orjson.dumps, users)
        async with aiofiles.open(self.path, "wb") as file:
            await file.write(to_save)

        logging.info("Finished Saving Users DB to disk")

    async def load_from_disk(self):
        logging.info("Loading Users DB from disk")

        if not self.path.exists():
            return

        async with aiofiles.open(self.path, "rb") as file:
            file_content = await file.read()

            if len(file_content) == 0:
                return

            loaded_db = await asyncio.to_thread(orjson.loads, file_content)

        new_users = []
        for user in loaded_db:
            new_user = User(**user)
            new_users.append(new_user)
        self.users = new_users
        self._assign_users()

        logging.info("Finished Loading Users DB from disk")
