from nicegui import ui

import globals
from web.custom_widgets import ContentDialog


class ContentCard:
    def __init__(self, tmdb_id: int):
        self.content = globals.MOVIES_DATABASE.by_tmdb_id[tmdb_id]

        self.dialog = ContentDialog(tmdb_id)

        self.card = ui.card()
        self.card.classes("no-shadow")
        self.card.style("margin: 0; padding: 6px; border-radius: 20px")

        with self.card:
            self.poster_image = ui.image(source=self.content.poster_url)
            self.poster_image.style("width: 200px; height: 100%; border-radius: 15px")

        with self.poster_image:
            self.poster_column = ui.column()
            self.poster_column.classes("w-full h-full justify-between")
            self.poster_column.style(
                "margin: 0; padding:0; opacity: 0; transition-duration: 0.5s")

        with self.poster_column:
            with ui.column(wrap=False).classes("w-full").style("gap: 0px; margin: 0; padding: 3px 3px 3px 10px;"):
                ui.html(f"<b>{self.content.title}</b>").style("font-size: 16px")
                ui.html(f"<i>{self.content.og_title}</i>").style("font-size: 10px")

            with ui.column(wrap=True).classes("w-full").style("gap: 0px; margin: 0; padding: 3px 3px 10px 10px"):
                ui.html(f"<b><i>{"<br>".join((self.content.genres))}</i></b>").style("font-size: 8px")

        self.card.on("mouseover", self.on_card_hover)
        self.card.on("mouseleave", self.on_card_unhover)
        self.card.on("click", self.on_card_click)

    def on_card_hover(self):
        self.poster_column.style("opacity: 0.9")
        self.card.style("transform: scale(1.02)")

    def on_card_unhover(self):
        self.poster_column.style("opacity: 0")
        self.card.style("transform: scale(1.0)")

    def on_card_click(self):
        self.dialog.open()
