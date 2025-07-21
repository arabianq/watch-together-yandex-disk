import asyncio
import logging
from functools import partial

from nicegui import ui

import config
import globals
from rooms.state import PlayerState
from web.custom_widgets import PlyrVideoPlayer
from web.custom_widgets.header import draw_header
from web.misc import check_user


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
    video_player.set_source(new_episode.file_url)

    seasons_column.clear()
    _draw_seasons(room_uid, tmdb_id, seasons_column, video_player, player_data)


def _draw_users_list(room_uid: str, users_card: ui.card):
    users_card.clear()
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    for user_uid in room.connected_users:
        user = globals.USERS_DATABASE.by_uid[user_uid]
        with users_card, ui.card().classes("w-full"):
            ui.label(user.username)


def _draw_seasons(room_uid: str, tmdb_id: int, seasons_column: ui.column, video_player: PlyrVideoPlayer,
                  player_data: dict):
    room = globals.ROOMS_DATABASE.by_uid[room_uid]
    tv_show = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]

    for season_number in range(1, tv_show.number_of_seasons + 1):
        season = tv_show.seasons[season_number - 1]

        with seasons_column, ui.card().classes("w-full"):
            ui.html(f"<b>{season.title}</b>")

            with ui.row().classes("w-full"):
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

    await draw_header()

    await _join_room(room_uid, user.uid)

    player_data = {
        "state": PlayerState.PAUSED,
        "position": 0,
        "season": None,
        "episode": None
    }

    with ui.row(wrap=False).classes("w-full"):
        player_card = ui.card()
        player_card.classes("no-shadow")
        player_card.style("width: 80%; min-height: 80vh; max-height: 80vh; border-radius: 15px")
        player_card.style("display: flex; justify-content: center; align-items: center;")

        users_card = ui.card()
        users_card.classes("no-shadow")
        users_card.style("width: 20%; min-height: 80vh; max-height: 80vh; border-radius: 15px")
        ui.timer(1, partial(_draw_users_list, room_uid, users_card))

    with player_card:
        video_player = PlyrVideoPlayer(src="")

        video_player.on("play", partial(_on_play, room_uid, player_data))
        video_player.on("pause", partial(_on_pause, room_uid, player_data))
        video_player.on("seeked", partial(_on_seeked, room_uid, video_player, player_data))
        video_player.on("end", partial(_on_stop, room_uid, video_player, player_data))

    seasons_column = ui.column().classes("w-full")
    seasons_column.visible = False

    tmdb_id = globals.ROOMS_DATABASE.by_uid[room_uid].tmdb_id
    content = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]

    if content.type == "movie":
        video = content.file_url
        poster = content.backdrop_url
    elif content.type == "tv":
        video = content.seasons[0].episodes[0].file_url
        poster = ""

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
