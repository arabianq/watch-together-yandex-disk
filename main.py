import asyncio
import logging
import os
import pathlib

from nicegui import background_tasks, app

import config
import globals
import web
from movies.db import MoviesDB
from rooms.db import RoomsDB
from users.db import UsersDB

working_dir = pathlib.Path(__file__).resolve().parent
os.chdir(working_dir)

if config.ENABLE_LOGGING:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S"
                        )


async def init_movies_db():
    globals.MOVIES_DATABASE = MoviesDB(db_path="data/movies_db.json")
    await globals.MOVIES_DATABASE.load_from_disk()
    await globals.MOVIES_DATABASE.update()


async def init_users_db():
    globals.USERS_DATABASE = UsersDB(db_path="data/users_db.json")
    await globals.USERS_DATABASE.load_from_disk()
    await globals.USERS_DATABASE.remove_inactive()


async def init_rooms_db():
    globals.ROOMS_DATABASE = RoomsDB()


async def before_startup():
    if not os.path.exists("data"):
        os.mkdir("data")

    await init_movies_db()
    await init_users_db()
    await init_rooms_db()


async def after_startup():
    background_tasks.create_lazy(globals.MOVIES_DATABASE.auto_update(), name="movies_db_auto_update")
    background_tasks.create_lazy(globals.USERS_DATABASE.auto_remove_inactive(), name="users_db_auto_remove_inactive")

    logging.info("Application successfully started!")


asyncio.run(before_startup())
app.on_startup(after_startup())

web.ui.run(
    host=config.HOST,
    port=config.PORT,
    dark=config.USE_DARK_THEME,
    reload=False,
    show=False,
    storage_secret=config.SECRET
)
