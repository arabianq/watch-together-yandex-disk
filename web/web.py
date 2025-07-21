from nicegui import ui

from web.custom_widgets.PlyrVideoPlayer import install_plyr
from web.misc import default_page_setup
from web.pages import *


@ui.page("/")
async def index():
    await default_page_setup()
    await index_page.page()


@ui.page("/contents")
async def movies():
    await default_page_setup()
    await movies_page.page()


@ui.page("/rooms")
async def rooms():
    await default_page_setup()
    await rooms_page.page()


@ui.page("/room/{room_uid}")
async def room(room_uid: str):
    install_plyr()
    await default_page_setup()
    await room_page.page(room_uid)
