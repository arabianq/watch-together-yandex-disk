import asyncio
import copy
import itertools
import logging

from cachetools import TTLCache
from cachetools_async import cached
from yndx_disk.classes import Directory, File
from yndx_disk.clients import AsyncDiskClient

import config
from movies.classes import Movie, TVShow, Season, Episode

NAME_DELIMITER = "#"
EXTENSION_DELIMITER = "."

_YANDEX_DISK_REQUEST_SEMAPHORE = asyncio.Semaphore(config.YANDEX_DISK_CONCURRENT_REQUESTS_LIMIT)


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _parse_tv_show(disk_client: AsyncDiskClient, directory: Directory) -> TVShow:
    logging.info("Parsing TV show directory: %s", directory.path)

    parts = [p.strip() for p in directory.name.split(NAME_DELIMITER)]
    if len(parts) < 3:
        logging.error("Invalid TV show directory name format: %s", directory.name)
        raise ValueError(f"Invalid TV show directory name: {directory.name}")

    file_type, tmdb_id_str, name = parts[0], parts[1], parts[2]
    if file_type != "tv":
        logging.warning("Directory %s expected to be 'tv' type, but found '%s'. Skipping.", directory.name, file_type)
        raise ValueError(f"Unexpected file type '{file_type}' for TV show directory: {directory.name}")

    try:
        tmdb_id = int(tmdb_id_str)
    except ValueError:
        logging.error("Invalid TMDB ID format for TV show: %s", tmdb_id_str)
        raise ValueError(f"Invalid TMDB ID format: {tmdb_id_str}")

    seasons_map = {}

    async with _YANDEX_DISK_REQUEST_SEMAPHORE:
        contents = await disk_client.listdir(path=directory.path, limit=10000)
    for obj in contents:
        if not isinstance(obj, File):
            continue

        obj_name_parts = obj.name.split(EXTENSION_DELIMITER)
        if len(obj_name_parts) < 2:
            logging.warning("Skipping file with invalid name (no extension): %s", obj.name)
            continue

        obj_name_without_ext = obj_name_parts[0].strip()
        episode_parts = [p.strip() for p in obj_name_without_ext.split(NAME_DELIMITER)]

        if len(episode_parts) < 2:
            logging.warning("Skipping file with invalid episode name format: %s", obj.name)
            continue

        season_number_str, episode_number_str = episode_parts[0], episode_parts[1]

        try:
            season_number = int(season_number_str)
            episode_number = int(episode_number_str)
        except ValueError:
            logging.warning("Skipping file with invalid season/episode number: %s", obj.name)
            continue

        if season_number not in seasons_map:
            seasons_map[season_number] = []

        episode = Episode(
            episode_number=episode_number,
            season_number=season_number,
            file_url=obj.file_url
        )
        seasons_map[season_number].append(episode)

    seasons_list = []
    for season_number, episodes in seasons_map.items():
        season = Season(
            season_number=season_number,
            episodes_count=len(episodes),
            episodes=tuple(copy.deepcopy(episodes))
        )
        seasons_list.append(season)

    seasons_list.sort(key=lambda s: s.season_number)

    all_episodes = list(itertools.chain.from_iterable([s.episodes for s in seasons_list]))

    return TVShow(
        tmdb_id=tmdb_id,
        number_of_episodes=len(all_episodes),
        number_of_seasons=len(seasons_list),
        title=name,
        seasons=tuple(seasons_list)
    )


async def _get_contents_on_disk(token: str, path: str) -> list[Movie | TVShow]:
    logging.info("Fetching contents from disk for token ending with ...%s, path: %s", token[-10:], path)

    disk_client = AsyncDiskClient(token=token, auto_update_info=False)
    async with _YANDEX_DISK_REQUEST_SEMAPHORE:
        contents_on_disk = await disk_client.listdir(path, limit=10000)

    logging.info("Found %s items on disk for token ending with ...%s", len(contents_on_disk), token[-10:])

    movies = []
    tv_show_tasks = []

    for obj in contents_on_disk:
        parts = [p.strip() for p in obj.name.split(NAME_DELIMITER)]
        if len(parts) < 3:
            logging.warning("Skipping item with invalid name format: %s", obj.name)
            continue

        file_type, tmdb_id_str, name_or_filename = parts[0], parts[1], parts[2]

        try:
            if file_type == "movie" and isinstance(obj, File):
                name_parts = name_or_filename.split(EXTENSION_DELIMITER)
                if len(name_parts) < 2:
                    logging.warning("Skipping movie file with no extension: %s", obj.name)
                    continue
                title = name_parts[0].strip()

                movie = Movie(
                    tmdb_id=int(tmdb_id_str),
                    file_size=int(obj.size),
                    file_url=obj.file_url,
                    title=title
                )
                movies.append(movie)
            elif file_type == "tv" and isinstance(obj, Directory):
                tv_show_tasks.append(_parse_tv_show(disk_client=disk_client, directory=obj))
            else:
                logging.warning("Skipping unknown/unsupported item type or mismatch: %s (Type: %s, Is Directory: %s)",
                                obj.name, file_type, isinstance(obj, Directory))
        except ValueError as e:
            logging.error("Error parsing item %s: %s", obj.name, e)
        except Exception as e:
            logging.critical("Unexpected error processing item %s: %s", obj.name, e, exc_info=True)

    tv_shows = await asyncio.gather(*tv_show_tasks)

    all_contents = movies + tv_shows
    logging.info("Found %s total contents on disk for token ending with ...%s", len(all_contents), token[-10:])

    return all_contents


async def get_all_contents() -> list[Movie | TVShow]:
    logging.info("Fetching all contents from all disks...")

    tasks = [_get_contents_on_disk(token, path) for token, path in config.YANDEX_CONFIGS]
    all_contents_lists = await asyncio.gather(*tasks)

    all_contents = list(itertools.chain.from_iterable(all_contents_lists))

    logging.info("Found %s total contents on all disks.", len(all_contents))

    return all_contents
