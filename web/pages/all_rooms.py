from nicegui import ui

import globals
from web.custom_widgets import draw_header
from web.misc import check_user


async def page():
    ui.page_title("Watch With Friends - Rooms")

    if not await check_user():
        ui.navigate.to("/")

    await draw_header()

    main_row = ui.row().classes("w-full")

    for room in globals.ROOMS_DATABASE.rooms:
        with main_row, ui.link(target=f"/room/{room.uid}"), ui.card().style("border-radius: 15px"):
            content = globals.MOVIES_DATABASE.by_tmdb_id[room.tmdb_id]

            with ui.row(wrap=False):
                ui.image(content.poster_url).style("width: 20%")

                with ui.column(wrap=False).classes("").style("gap: 0px"):
                    ui.html(f"{room.uid}")
                    ui.html(f"<b>{content.title}</b>")

                    users = [globals.USERS_DATABASE.by_uid[uid] for uid in room.connected_users]
                    ui.html(f"<i>{", ".join(u.username for u in users)}</i>")
