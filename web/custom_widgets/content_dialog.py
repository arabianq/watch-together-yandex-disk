import itertools

from nicegui import ui

import globals
from web.misc import convert_runtime


class ContentDialog(ui.dialog):
    def __init__(self, tmdb_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.content = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]

        with self:
            self.card = ui.card()
            self.card.classes("h-max no-shadow")
            self.card.style("min-width: 20%; border-radius: 15px")

        with self.card:
            self.title_column = ui.column(wrap=False)
            self.title_column.classes("w-full")
            self.title_column.style("gap: 0; margin: 0; padding: 0;")

        with self.title_column:
            ui.html(f"<b>{self.content.title}</b>").style("font-size: 22px")
            ui.html(f"<i>{self.content.og_title}</i>").style("font-size: 14px")
            ui.html(f"<b><i>{", ".join(self.content.genres)}</i></b>").style("font-size: 12px")

        with self.card:
            self.additional_info_column = ui.column(wrap=False)
            self.additional_info_column.classes("w-full")
            self.additional_info_column.style("width: 50%; gap: 0; white-space: nowrap")

        with self.additional_info_column:
            release_date = self.content.release_date.split("-")[::-1]
            release_date = ".".join(release_date)
            ui.html(f"<b>Release Date: </b>{release_date}").style("font-size: 12px")
            ui.html(f"<b>Average Score: </b>{round(self.content.vote_average, 2)}").style("font-size: 12px")

            if self.content.type == "movie":
                budget = "$" + f"{self.content.budget:_}".replace("_", ".")
                ui.html(f"<b>Budget: </b>{budget}").style("font-size: 12px")
                ui.html(f"<b>Runtime: </b>{convert_runtime(self.content.runtime)}").style("font-size: 12px")
            elif self.content.type == "tv":
                ui.html(f"<b>Number of Seasons: </b>{self.content.number_of_seasons}").style("font-size: 12px")
                ui.html(f"<b>Number of Episodes: </b>{self.content.number_of_episodes}").style("font-size: 12px")
                total_runtime = sum([ep.runtime for ep in
                                     itertools.chain.from_iterable([s.episodes for s in self.content.seasons])])
                ui.html(f"<b>Total Runtime: </b>{convert_runtime(total_runtime)}").style("font-size: 12px")
                if self.content.in_production:
                    ui.html(f"<b><i>Currently in production</i></b>").style("font-size: 12px")
                else:
                    ui.html(f"<b><i>Finished</i></b>").style("font-size: 12px")

        with self.card, ui.row(wrap=False).classes("w-full").style("display: flex; justify-content: center;"):
            ui.button("Create Room").on_click(self.create_room)

    async def create_room(self):
        room = await globals.ROOMS_DATABASE.create_room(self.content.tmdb_id)
        ui.navigate.to(f"/room/{room.uid}")
