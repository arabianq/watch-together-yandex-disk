from nicegui import ui, app

import config
import globals
from users.classes import User


def convert_runtime(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0 and minutes > 0:
        return f"{hours} h {minutes} m"
    elif hours > 0:
        return f"{hours} h"
    elif minutes > 0:
        return f"{minutes} m"
    else:
        return "0 m"


def logout(redirect: bool = False):
    if app.storage.user.get("token"):
        app.storage.user.pop("token")

    if redirect:
        ui.navigate.to("/")


async def check_user() -> User | None:
    if token := app.storage.user.get("token"):
        user = await globals.USERS_DATABASE.get_user_by_token(token)
        if user:
            return user
        else:
            logout()
            return None
    else:
        return None


async def update_user():
    if token := app.storage.user.get("token"):
        user = await globals.USERS_DATABASE.get_user_by_token(token)
        if user:
            await globals.USERS_DATABASE.update_user(user.uid)
        else:
            app.storage.user.pop("token")
            ui.navigate.to("/")
    else:
        ui.navigate.to("/")


async def default_page_setup():
    ui.add_head_html("<meta name=\"referrer\" content=\"no-referrer\" />")
    await ui.context.client.connected(timeout=config.CONNECTION_TIMEOUT_SECONDS)
    ui.timer(60, update_user)


async def is_portrait():
    try:
        width, height = await ui.run_javascript("return [window.screen.availWidth, window.screen.availHeight]")
    except TimeoutError:
        return False

    if width > height:
        return False
    return True
