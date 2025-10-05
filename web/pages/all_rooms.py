import asyncio

from nicegui import ui

import globals
from web.custom_widgets import draw_header
from web.misc import check_user, is_portrait


async def page():
    ui.page_title("Watch With Friends - Rooms")

    if not await check_user():
        ui.navigate.to("/")

    if not (rooms := globals.ROOMS_DATABASE.rooms):
        ui.notify("No rooms found, redirecting to /contents...")
        await asyncio.sleep(1)
        ui.navigate.to("/contents")

    portrait = await is_portrait()

    await draw_header()

    if portrait:
        container = ui.column().classes("w-full items-center")
    else:
        container = ui.row().classes("w-full items-center")

    for room in rooms:
        with (container, ui.link(target=f"/room/{room.uid}").style("text-decoration: none"),
              ui.card().classes("no-shadow").style("border-radius: 15px;")):
            content = globals.MOVIES_DATABASE.by_tmdb_id[room.tmdb_id]

            with ui.row(wrap=False):
                ui.image(content.poster_url).style("width: 100px; border-radius: 15px")

                with ui.column(wrap=False).style("gap: 0px;"):
                    ui.html(f"{room.uid}")
                    ui.html(f"<b>{content.title}</b>")

                    users = [globals.USERS_DATABASE.by_uid[uid] for uid in room.connected_users]
                    ui.html(f"<i>{", ".join(u.username for u in users)}</i>")
