import asyncio
import logging
from functools import partial

from nicegui import ui

import config
import globals
from rooms.state import PlayerState
from web.custom_widgets import PlyrVideoPlayer
from web.custom_widgets.header import draw_header
from web.misc import check_user, is_portrait


def _check_room(room_uid: str):
    return not globals.ROOMS_DATABASE.by_uid.get(room_uid) is None


async def _join_room(room_uid: str, user_uid: str):
    for _ in range(10):
        if globals.ROOMS_DATABASE.by_uid.get(room_uid) is None:
            await asyncio.sleep(0.1)
            continue
        break

    if globals.ROOMS_DATABASE.by_uid.get(room_uid) is None:
        ui.notify(f"Failed to join room {room_uid}, redirecting to /rooms...", type="warning")
        await asyncio.sleep(1)
        ui.navigate.to("/rooms")
        return

    globals.ROOMS_DATABASE.by_uid[room_uid].connected_users.append(user_uid)

    logging.info(f"{user_uid} joined room {room_uid}")


def _leave_room(room_uid: str, user_uid: str):
    if user_uid in globals.ROOMS_DATABASE.by_uid[room_uid].connected_users:
        globals.ROOMS_DATABASE.by_uid[room_uid].connected_users.remove(user_uid)
        logging.info(f"{user_uid} left room {room_uid}")


def _change_episode(room_uid: str, tmdb_id: int, season_number: int, episode_number: int, seasons_column: ui.column,
                    video_player: PlyrVideoPlayer, player_data: dict):
    try:
        new_episode = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id].seasons[season_number - 1].episodes[
            episode_number - 1]
    except KeyError:
        ui.notify("Episode not found", type="negative")
        return

    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    room.current_season, room.current_episode = season_number, episode_number
    room.player_position = 0
    room.player_state = PlayerState.PAUSED
    player_data["season"], player_data["episode"] = season_number, episode_number
    player_data["position"] = 0
    video_player.pause()
    video_player.seek(0)

    video_player.pause()
    video_player.set_source(new_episode.file_url, new_episode.still_url)

    seasons_column.clear()
    _draw_seasons(room_uid, tmdb_id, seasons_column, video_player, player_data)


def _draw_users_list(room_uid: str, users_card: ui.card):
    users_card.clear()
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    with users_card, ui.scroll_area():
        for user_uid in list(dict.fromkeys(room.connected_users)):
            user = globals.USERS_DATABASE.by_uid[user_uid]
            with ui.card().classes("w-full"):
                ui.label(user.username)


def _draw_messages(room_uid: str, current_user_uid: str, messages_scroll_area: ui.scroll_area, scroll_position: dict):
    messages_scroll_area.clear()
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    with messages_scroll_area:
        for user_uid, message_text in room.messages:
            user = globals.USERS_DATABASE.by_uid.get(user_uid)
            username = user.username if user else "DELETED"
            ui.chat_message(name=username, text=message_text, sent=user_uid == current_user_uid).classes("w-full")

    if scroll_position["_"] == 1:
        messages_scroll_area.scroll_to(percent=100)


def _draw_seasons(room_uid: str, tmdb_id: int, seasons_column: ui.column, video_player: PlyrVideoPlayer,
                  player_data: dict):
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    tv_show = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]

    for season_number in range(1, tv_show.number_of_seasons + 1):
        season = tv_show.seasons[season_number - 1]

        with seasons_column, ui.card().classes("w-full no-shadow").style("border-radius: 15px"):
            with ui.expansion(text=season.title, value=True).classes("w-full"), ui.row().classes("w-full"):
                episodes = tv_show.seasons[season_number - 1].episodes
                for episode_number in range(1, len(episodes) + 1):
                    episode_button = ui.button(str(episode_number),
                                               on_click=partial(_change_episode, room_uid, tmdb_id, season_number,
                                                                episode_number, seasons_column, video_player,
                                                                player_data))
                    if room.current_season == season_number and room.current_episode == episode_number:
                        episode_button.disable()


async def _on_seeked(room_uid: str, video_player: PlyrVideoPlayer, player_data: dict):
    try:
        position = await video_player.get_current_position()
    except TimeoutError:
        return
    globals.ROOMS_DATABASE.by_uid[room_uid].seek(position)
    player_data["position"] = position


async def _on_play(room_uid: str, player_data: dict):
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    room.play()
    player_data["state"] = PlayerState.PLAYING


async def _on_pause(room_uid: str, player_data: dict):
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    room.pause()
    player_data["state"] = PlayerState.PAUSED


async def _on_stop(room_uid: str, video_player: PlyrVideoPlayer, player_data: dict):
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    room.stop()
    player_data["state"] = PlayerState.STOPPED
    video_player.pause()


async def _sync(room_uid: str, tmdb_id: int, seasons_column: ui.column, video_player: PlyrVideoPlayer,
                player_data: dict):
    try:
        player_data["position"] = await video_player.get_current_position()
    except TimeoutError:
        return
    room = globals.ROOMS_DATABASE.by_uid[room_uid]

    if player_data["state"] != room.player_state:
        match room.player_state:
            case PlayerState.PLAYING:
                video_player.play()
                player_data["state"] = PlayerState.PLAYING
            case PlayerState.PAUSED:
                video_player.pause()
                player_data["state"] = PlayerState.PAUSED
            case PlayerState.STOPPED:
                video_player.pause()
                player_data["state"] = PlayerState.STOPPED

    if not await video_player.is_seeking():
        if (player_data["state"] != PlayerState.PLAYING
                or abs(player_data["position"] - room.player_position) > config.MAX_DELAY_SECONDS):
            video_player.seek(room.player_position)
            player_data["position"] = room.player_position

    if player_data["season"] != room.current_season or player_data["episode"] != room.current_episode:
        player_data["season"], player_data["episode"] = room.current_season, room.current_episode
        _change_episode(room_uid, tmdb_id, room.current_season, room.current_episode, seasons_column, video_player,
                        player_data)


async def page(room_uid: str):
    if not _check_room(room_uid):
        ui.navigate.to("/rooms")
        return

    user = await check_user()
    if not user:
        ui.navigate.to("/")
        return

    portrait = await is_portrait()

    await draw_header()

    await _join_room(room_uid, user.uid)

    player_data = {
        "state": PlayerState.PAUSED,
        "position": 0,
        "season": None,
        "episode": None
    }

    with ui.column(wrap=False).classes("w-full") if portrait else ui.row(wrap=False).classes("w-full"):
        player_card = ui.card()
        player_card.classes("no-shadow")
        player_card.style("display: flex; justify-content: center; align-items: center; border-radius: 15px")
        if portrait:
            player_card.style("width: 100%;")
        else:
            player_card.style("width: 80%; min-height: 80vh; max-height: 80vh;")

        with ui.column(wrap=False) as column:
            if portrait:
                column.classes("w-full")
            else:
                column.style("width: 20%")

            users_card = ui.card()
            users_card.classes("w-full no-shadow")
            users_card.style("border-radius: 15px")
            if portrait:
                users_card.style("max-height: 20vh;")
            else:
                users_card.style("min-height: 39vh; max-height: 39vh;")
            ui.timer(0.1, partial(_draw_users_list, room_uid, users_card))

            messages_card = ui.card()
            messages_card.classes("w-full no-shadow")
            messages_card.style("border-radius: 15px")
            if portrait:
                messages_card.style("max-height: 20vh;")
            else:
                messages_card.style("min-height: 39vh; max-height: 39vh;")

            with messages_card:
                messages_scroll_position = {"_": 0}

                def on_messages_scroll(e):
                    messages_scroll_position["_"] = e.vertical_percentage

                messages_scroll_area = ui.scroll_area(on_scroll=on_messages_scroll).classes("w-full")

                def send_message():
                    if text := message_input.value.strip():
                        globals.ROOMS_DATABASE.by_uid[room_uid].messages.append((user.uid, text))
                        message_input.value = ""
                        _draw_messages(room_uid, user.uid, messages_scroll_area, messages_scroll_position)
                        messages_scroll_area.scroll_to(percent=100)

                with ui.row(wrap=False).classes("w-full justify-between"):
                    message_input = ui.input("Message").classes("w-full")
                    ui.button(icon="send", on_click=send_message)

            ui.timer(0.1, partial(_draw_messages, room_uid, user.uid, messages_scroll_area, messages_scroll_position))

    with player_card:
        video_player = PlyrVideoPlayer(src="", poster_url="", minimal=portrait)

        video_player.on("play", partial(_on_play, room_uid, player_data))
        video_player.on("pause", partial(_on_pause, room_uid, player_data))
        video_player.on("seeked", partial(_on_seeked, room_uid, video_player, player_data))
        video_player.on("end", partial(_on_stop, room_uid, video_player, player_data))

    seasons_column = ui.column().classes("w-full")
    seasons_column.visible = False

    tmdb_id = globals.ROOMS_DATABASE.by_uid[room_uid].tmdb_id
    content = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]

    ui.page_title(content.title)

    if content.type == "movie":
        video = content.file_url
        poster = content.backdrop_url
    elif content.type == "tv":
        video = content.seasons[0].episodes[0].file_url
        poster = content.seasons[0].episodes[0].still_url

        room = globals.ROOMS_DATABASE.by_uid[room_uid]
        room.current_season, room.current_episode = 1, 1
        player_data["season"], player_data["episode"] = 1, 1

        seasons_column.visible = True
        _draw_seasons(room_uid, tmdb_id, seasons_column, video_player, player_data)
    else:
        video = ""
        poster = ""

    video_player.set_source(video, poster)

    ui.timer(1, partial(_sync, room_uid, tmdb_id, seasons_column, video_player, player_data))

    await ui.context.client.disconnected()

    _leave_room(room_uid, user.uid)
