import asyncio
import copy
import logging
import random

import aiohttp
from cachetools import TTLCache
from cachetools_async import cached

import config
from movies.classes import Movie, TVShow, Season, Episode

_BASE_API_URL = "https://api.themoviedb.org/3"
_BASE_IMAGE_URL = None


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _fetch_tmdb_data():
    global _BASE_IMAGE_URL

    logging.info("Fetching TMDB configuration data")

    headers = {
        "Authorization": f"Bearer {config.TMDB_API_KEY}",
        "Accept": "application/json"
    }

    proxy = random.choice(config.PROXIES) if config.PROXIES else None
    async with aiohttp.ClientSession(proxy=proxy) as session:
        async with session.get(
                url=f"{_BASE_API_URL}/configuration",
                headers=headers,
                params={"language": config.TMDB_LANG}
        ) as response:
            assert response.status == 200, "Failed to fetch TMDB configuration data"

            response_json = await response.json()

    _BASE_IMAGE_URL = response_json["images"]["base_url"]


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _fetch_movie(movie: Movie) -> Movie:
    headers = {
        "Authorization": f"Bearer {config.TMDB_API_KEY}",
        "Accept": "application/json"
    }

    proxy = random.choice(config.PROXIES) if config.PROXIES else None
    async with aiohttp.ClientSession(proxy=proxy) as session:
        async with session.get(
                url=f"{_BASE_API_URL}/movie/{movie.tmdb_id}",
                headers=headers,
                params={"language": config.TMDB_LANG}
        ) as response:
            assert response.status == 200, f"Failed to fetch information for {movie.tmdb_id}"

            response_json = await response.json()

    return Movie(
        tmdb_id=movie.tmdb_id,
        file_size=movie.file_size,
        file_url=movie.file_url,
        title=response_json.get("title", movie.title),
        budget=response_json.get("budget"),
        runtime=response_json.get("runtime"),
        vote_average=response_json.get("vote_average"),
        adult=response_json.get("adult"),
        og_title=response_json.get("original_title"),
        homepage=response_json.get("homepage"),
        poster_url=f"{_BASE_IMAGE_URL}original{response_json["poster_path"]}" if response_json.get(
            "poster_path") else None,
        backdrop_url=f"{_BASE_IMAGE_URL}original{response_json["backdrop_path"]}" if response_json.get(
            "backdrop_path") else None,
        release_date=response_json.get("release_date"),
        genres=tuple(sorted([genre["name"].capitalize() for genre in response_json.get("genres", [])], key=len)),
    )


@cached(TTLCache(maxsize=config.CACHE_MAXSIZE, ttl=config.CACHE_TTL))
async def _fetch_tv_show(tv_show: TVShow) -> TVShow:
    headers = {
        "Authorization": f"Bearer {config.TMDB_API_KEY}",
        "Accept": "application/json"
    }

    proxy = random.choice(config.PROXIES) if config.PROXIES else None
    async with aiohttp.ClientSession(proxy=proxy) as session:
        async with session.get(
                url=f"{_BASE_API_URL}/tv/{tv_show.tmdb_id}",
                headers=headers,
                params={"language": config.TMDB_LANG}
        ) as tv_response:
            assert tv_response.status == 200, f"Failed to fetch information for {tv_show.tmdb_id}"

            tv_response_json = await tv_response.json()

        seasons_responses_jsons = {}
        for i in range(len(tv_show.seasons)):
            season_number = tv_show.seasons[i].season_number

            async with session.get(
                    url=f"{_BASE_API_URL}/tv/{tv_show.tmdb_id}/season/{season_number}",
                    headers=headers,
                    params={"language": config.TMDB_LANG}
            ) as season_response:
                assert tv_response.status == 200, f"Failed to fetch information for {tv_show.tmdb_id}"

                seasons_responses_jsons[season_number] = await season_response.json()

    seasons_dict = {}
    for season_number, season_response_json in seasons_responses_jsons.items():
        for episode_response_json in season_response_json.get("episodes", []):
            episode_number = episode_response_json["episode_number"]

            raw_season = None
            for season in tv_show.seasons:
                if season.season_number == season_number:
                    raw_season = season
                    break

            if raw_season is None:
                continue

            raw_episode = None
            for episode in raw_season.episodes:
                if episode.episode_number == episode_number:
                    raw_episode = episode
                    break

            if raw_episode is None:
                continue

            if not seasons_dict.get(season_number):
                seasons_dict[season_number] = []

            episode = Episode(
                episode_number=episode_number,
                season_number=season_number,
                runtime=episode_response_json.get("runtime"),
                vote_average=episode_response_json.get("vote_average"),
                title=episode_response_json.get("name", str(episode_number)),
                file_url=raw_episode.file_url,
                episode_type=episode_response_json.get("episode_type"),
                release_date=episode_response_json.get("air_date"),
            )
            seasons_dict[season_number].append(episode)

    seasons = []
    for season_number, season_response_json in seasons_responses_jsons.items():
        raw_season = None
        for season in tv_show.seasons:
            if season.season_number == season_number:
                raw_season = season
                break

        if raw_season is None:
            continue

        season = Season(
            season_number=season_number,
            episodes_count=len(seasons_dict[season_number]),
            vote_average=season_response_json.get("vote_average"),
            title=season_response_json.get("name", str(season_number)),
            poster_url=f"{_BASE_IMAGE_URL}original{season_response_json["poster_path"]}" if season_response_json.get(
                "poster_path") else None,
            release_date=season_response_json.get("air_date"),
            episodes=tuple(copy.deepcopy(seasons_dict[season_number]))
        )
        seasons.append(season)

    return TVShow(
        tmdb_id=tv_show.tmdb_id,
        number_of_episodes=tv_show.number_of_episodes,
        number_of_seasons=len(seasons),
        vote_average=tv_response_json.get("vote_average"),
        adult=tv_response_json.get("adult"),
        title=tv_response_json.get("name"),
        og_title=tv_response_json.get("original_name"),
        homepage=tv_response_json.get("homepage"),
        poster_url=f"{_BASE_IMAGE_URL}original{tv_response_json["poster_path"]}" if tv_response_json.get(
            "poster_path") else None,
        backdrop_url=f"{_BASE_IMAGE_URL}original{tv_response_json["backdrop_path"]}" if tv_response_json.get(
            "backdrop_path") else None,
        release_date=tv_response_json.get("first_air_date"),
        in_production=tv_response_json.get("production"),
        seasons=tuple(seasons),
        genres=tuple(sorted([genre["name"].capitalize() for genre in tv_response_json.get("genres", [])], key=len)),
    )


async def _fetch_data(content: Movie | TVShow) -> Movie | TVShow:
    logging.info("Fetching data for %s", content.tmdb_id)

    match content.type:
        case "movie":
            return await _fetch_movie(content)
        case "tv":
            return await _fetch_tv_show(content)
        case _:
            raise TypeError(f"Unknown content type: {content.type}")


async def fetch_all_data(contents: list[Movie | TVShow]) -> list[Movie | TVShow]:
    logging.info("Fetching data for %s contents", len(contents))

    await _fetch_tmdb_data()

    tasks = [_fetch_data(content) for content in contents]
    return await asyncio.gather(*tasks)
