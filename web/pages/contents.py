from nicegui import ui

import globals
from web.custom_widgets import draw_header, ContentCard
from web.misc import check_user


async def page():
    ui.page_title("Watch With Friends - Contents")

    if not await check_user():
        ui.navigate.to("/")

    await draw_header()

    with ui.row(wrap=True).classes("w-full").style("margin: auto; gap: 16px"):
        for content in globals.MOVIES_DATABASE.contents:
            ContentCard(content.tmdb_id)
