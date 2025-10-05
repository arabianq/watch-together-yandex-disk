from nicegui import ui, app

import config
import globals
from users.utils import generate_token
from web.misc import check_user


async def page():
    ui.page_title("Watch With Friends")

    await ui.context.client.connected()

    if not await check_user():
        await handle_login()

    ui.navigate.to("/contents")


async def handle_login():
    async def try_create_user():
        login = login_input.value.strip()
        password = password_input.value.strip()

        if password != config.PASSWORD:
            ui.notify("Incorrect password!", type="negative", position="top")
            return

        new_user = await globals.USERS_DATABASE.create_user(login)
        token = generate_token(new_user)

        if token:
            app.storage.user["token"] = token
            dialog.close()
        else:
            ui.notify("Something went wrong!", type="negative", position="top")

    with ui.dialog().props("persistent") as dialog, ui.card():
        ui.label("Login")
        with ui.column():
            login_input = ui.input("Username").classes("w-full")
            password_input = ui.input("Password", password=True, password_toggle_button=True).classes("w-full")
            ui.button("Login", on_click=try_create_user).classes("w-full")

    await dialog
