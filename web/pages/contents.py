from nicegui import ui

import globals
from web.custom_widgets import draw_header, ContentCard
from web.misc import check_user, is_portrait


async def page():
    ui.page_title("Watch With Friends - Contents")

    if not await check_user():
        ui.navigate.to("/")

    portrait = await is_portrait()

    await draw_header()

    if portrait:
        container = ui.column(wrap=False).classes("w-full items-center").style("margin: auto; gap: auto;")
    else:
        container = ui.row().classes("items-center").style("margin: auto; gap: auto;")

    with container:
        for content in globals.MOVIES_DATABASE.contents:
            ContentCard(content.tmdb_id)
