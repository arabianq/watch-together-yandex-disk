from nicegui import ui

import config
from web.misc import update_user
from web.pages import *


@ui.page("/")
async def index():
    ui.add_head_html("<meta name=\"referrer\" content=\"no-referrer\" />")
    await ui.context.client.connected(timeout=config.CONNECTION_TIMEOUT_SECONDS)
    await index_page.page()


@ui.page("/contents")
async def movies():
    ui.add_head_html("<meta name=\"referrer\" content=\"no-referrer\" />")
    await ui.context.client.connected(timeout=config.CONNECTION_TIMEOUT_SECONDS)
    ui.timer(60, update_user)
    await movies_page.page()


@ui.page("/rooms")
async def rooms():
    ui.add_head_html("<meta name=\"referrer\" content=\"no-referrer\" />")
    await ui.context.client.connected(timeout=config.CONNECTION_TIMEOUT_SECONDS)
    ui.timer(60, update_user)
    await rooms_page.page()


@ui.page("/room/{room_uid}")
async def room(room_uid: str):
    ui.add_head_html("<meta name=\"referrer\" content=\"no-referrer\" />")
    ui.add_head_html('''
                    <link href="https://vjs.zencdn.net/7.21.1/video-js.css" rel="stylesheet" />
                    <script src="https://vjs.zencdn.net/7.21.1/video.min.js"></script>
                    ''')
    await ui.context.client.connected(timeout=config.CONNECTION_TIMEOUT_SECONDS)
    ui.timer(60, update_user)
    await room_page.page(room_uid)
