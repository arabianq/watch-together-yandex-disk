from nicegui import ui

from web.misc import logout, check_user


async def draw_header():
    with ui.header(wrap=False):
        with ui.row(wrap=False).classes("w-full justify-between") as header_row:
            ui.button(icon="home", on_click=lambda: ui.navigate.to("/"))
            ui.button(text="Rooms", icon="movie", on_click=lambda: ui.navigate.to("/rooms"))

            with ui.row(wrap=False).classes("items-center"):
                if user := await check_user():
                    ui.html(f"<b>{user.username}</b>")
                ui.button(icon="logout", on_click=lambda: logout(redirect=True))
