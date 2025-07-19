import asyncio
import copy
import itertools
import logging

from cachetools import TTLCache
from cachetools_async import cached
from yndx_disk.classes import Directory
from yndx_disk.clients import AsyncDiskClient

import config
from movies.classes import Movie, TVShow, Season, Episode


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _parse_tv_show(disk_client: AsyncDiskClient, directory: Directory) -> TVShow:
    file_type, tmdb_id, name = map(str.strip, directory.name.split("#"))

    logging.info(f"Parsing TV show %s", tmdb_id)

    seasons_dict = {}
    contents = await disk_client.listdir(path=directory.path, limit=10000)
    for obj in contents:
        if type(obj) is Directory:
            continue

        obj_name, obj_extension = map(str.strip, obj.name.split("."))
        season_number, episode_number = map(str.strip, obj_name.split("#"))

        if not seasons_dict.get(season_number):
            seasons_dict[season_number] = []

        episode = Episode(
            episode_number=int(episode_number),
            season_number=int(season_number),
            file_url=obj.file_url
        )
        seasons_dict[season_number].append(episode)

    seasons = []
    for season_number, episodes in seasons_dict.items():
        season = Season(
            season_number=int(season_number),
            episodes_count=len(episodes),
            episodes=tuple(copy.deepcopy(episodes))
        )
        seasons.append(season)

    return TVShow(
        tmdb_id=int(tmdb_id),
        number_of_episodes=len(list(itertools.chain.from_iterable([s.episodes for s in seasons]))),
        number_of_seasons=len(seasons),
        title=name,
        seasons=tuple(seasons)
    )


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _get_contents_on_disk(token: str, path: str) -> list[Movie]:
    logging.info("Fetching contents from disk ...%s", token[-10:])

    disk_client = AsyncDiskClient(token=token, auto_update_info=False)
    files = await disk_client.listdir(path, limit=10000)

    logging.info("Found %s files on disk ...%s", len(files), token[-10:])

    movies = []
    tv_shows = []

    for obj in files:
        file_type, tmdb_id, name = map(str.strip, obj.name.split("#"))

        match file_type:
            case "movie":
                name, extension = map(str.strip, name.split("."))
                movie = Movie(
                    tmdb_id=int(tmdb_id),
                    file_size=int(obj.size),
                    file_url=obj.file_url,
                    title=name
                )
                movies.append(movie)
            case "tv":
                pass
                tv_show = await _parse_tv_show(disk_client=disk_client, directory=obj)
                tv_shows.append(tv_show)
            case _:
                continue

    logging.info("Found %s contents on disk ...%s", len(movies), token[-10:])

    return movies + tv_shows


async def get_all_contents() -> list[Movie]:
    logging.info("Fetching all contents on all disks")

    tasks = [_get_contents_on_disk(token, path) for token, path in config.YANDEX_CONFIGS]
    movies = await asyncio.gather(*tasks)
    movies = list(itertools.chain.from_iterable(movies))

    logging.info("Found %s contents on all disks", len(movies))

    return movies
