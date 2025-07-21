import uuid

from nicegui import ui


class PlyrVideoPlayer:
    _plyr_installed = False

    def __init__(self, src: str, poster_url: str = None):
        if not PlyrVideoPlayer._plyr_installed:
            install_plyr()
            PlyrVideoPlayer._plyr_installed = True

        self.src = src
        self.poster_url = poster_url

        self.element_id = f"plyr_{uuid.uuid4().hex}"
        self.player_var = f"player_{self.element_id}"
        self.event_play = f"{self.element_id}_playing"
        self.event_pause = f"{self.element_id}_pause"
        self.event_end = f"{self.element_id}_ended"
        self.event_seeked = f"{self.element_id}_seeked"

        poster_attr = f"data-poster=\"{poster_url}\"" if poster_url else ""
        source_html = f"<source src=\"{src}\" type=\"video/mp4\" />"
        video_html = (
            f"<video id=\"{self.element_id}\" playsinline controls {poster_attr}>"
            f"{source_html}"
            "</video>"
        )

        with ui.element("div").classes("plyr-container"):
            ui.html(video_html)

        options = {}
        options.setdefault("settings", [])
        options.setdefault("ratio", "16:9")
        options.setdefault("controls",
                           ["play-large", "play", "rewind", "fast-forward", "current-time", "progress", "duration",
                            "mute", "volume", "pip", "airplay", "download", "fullscreen"]
                           )
        js_options = str(options).replace("True", "true").replace("'", '"')

        js = f"""
            (async () => {{
                const video = document.getElementById('{self.element_id}');
                const player = new Plyr(video, {js_options});
                window.{self.player_var} = player;

                player.on('play', () => emitEvent('{self.event_play}'));
                player.on('pause', () => emitEvent('{self.event_pause}'));
                player.on('ended', () => emitEvent('{self.event_end}'));
                player.on('seeked', () => emitEvent('{self.event_seeked}'));
            }})();
        """
        ui.run_javascript(js)

    def on(self, event: str, callback: callable):
        mapping = {
            "play": self.event_play,
            "pause": self.event_pause,
            "end": self.event_end,
            "seeked": self.event_seeked
        }
        if event not in mapping:
            raise ValueError("Supported events: 'play', 'pause', 'end', 'seeked'")
        ui.on(mapping[event], callback)

    async def is_seeking(self):
        return await ui.run_javascript(f"window.{self.player_var}.seeking")

    async def get_audio_tracks(self):
        return await ui.run_javascript(f"window.{self.player_var}.audio_tracks")

    def play(self):
        ui.run_javascript(f"window.{self.player_var}.play();")

    def pause(self):
        ui.run_javascript(f"window.{self.player_var}.pause();")

    def seek(self, time: float):
        ui.run_javascript(f"window.{self.player_var}.currentTime = {time};")

    def set_source(self, src: str, poster_url: str = "", type: str = 'video/mp4'):
        self.src = src
        self.poster_url = poster_url
        ui.run_javascript(f"""
            window.{self.player_var}.source = {{
                type: 'video',
                sources: [
                    {{
                        src: '{src}',
                        type: '{type}',
                    }},
                ],
                poster: '{poster_url}',
            }};
        """)

    async def get_current_position(self) -> float:
        result = await ui.run_javascript(f"return window.{self.player_var}.currentTime;")
        return float(result)


def install_plyr(css: str = "https://cdn.plyr.io/3.7.8/plyr.css",
                 js: str = "https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"):
    ui.add_head_html(f'''
        <link rel="stylesheet" href="{css}" />
        <script src="{js}"></script>
        <style>
            .plyr-container {{
                border-radius: 15px;
                overflow: hidden;
                width: 100%;
                height: 100%;
            }}
        </style>
    ''')
