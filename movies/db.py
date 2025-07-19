import asyncio
import logging
from datetime import datetime
from pathlib import Path

import aiofiles
import orjson

import config
import movies.tmdb as tmdb
import movies.yandex_disk as yandex_disk
from movies.classes import Movie, TVShow
from singleton import Singleton


class MoviesDB(metaclass=Singleton):
    def __init__(self, db_path: Path | str):
        self.path = Path(db_path).resolve()
        self.contents = []
        self.by_tmdb_id: dict[int, Movie | TVShow] = {}
        self.by_title: dict[str, Movie | TVShow] = {}
        self.last_updated = None

    def _assign_content(self):
        self.by_tmdb_id = {}
        self.by_title = {}

        for content in self.contents:
            tmdb_id = content.tmdb_id
            self.by_tmdb_id[tmdb_id] = content

            title, og_title = content.title, content.og_title
            title = title if title else ""
            og_title = og_title if og_title else ""
            full_title = title + og_title
            if full_title:
                self.by_title[full_title] = content

    async def auto_update(self):
        while True:
            await asyncio.sleep(config.MOVIES_DB_UPDATE_INTERVAL_SECONDS)
            await self.update()

    async def update(self):
        logging.info("Updating Movies DB")

        raw_contents = await yandex_disk.get_all_contents()
        self.contents = await tmdb.fetch_all_data(raw_contents)
        self.last_updated = datetime.now()
        await self.save_to_disk()
        self._assign_content()

        logging.info("Finished updating Movies DB")

    async def save_to_disk(self):
        logging.info("Saving Movies DB to disk")

        to_save = await asyncio.to_thread(orjson.dumps, {
            "last_updated": self.last_updated,
            "contents": self.contents
        })
        async with aiofiles.open(self.path, "wb") as file:
            await file.write(to_save)

        logging.info("Finished Saving Movies DB to disk")

    async def load_from_disk(self):
        if not self.path.exists():
            return

        logging.info("Loading Movies DB from disk")

        async with aiofiles.open(self.path, "rb") as file:
            file_content = await file.read()

            if len(file_content) == 0:
                return

            loaded_db = await asyncio.to_thread(orjson.loads, file_content)
            self.last_updated = loaded_db.get("last_updated", None)
            contents = loaded_db.get("contents", [])

        new_contents = []
        for content in contents:
            match content["type"]:
                case "movie":
                    new_contents.append(Movie(**content))
                case "tv":
                    new_contents.append(TVShow(**content))
                case _:
                    continue
        self.contents = new_contents
        self._assign_content()

        logging.info("Finished Loading Movies DB from disk")
