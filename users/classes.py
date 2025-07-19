from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=False)
class User:
    username: str
    uid: str

    _last_activity_str: str = None

    def __init__(self, username: str, uid: str, last_activity: datetime):
        self.username = username
        self.uid = uid
        self.last_activity = last_activity

    @property
    def last_activity(self) -> datetime:
        return datetime.strptime(self._last_activity_str, "%Y-%m-%dT%H:%M:%S.%f")

    @last_activity.setter
    def last_activity(self, value: datetime | str):
        if type(value) is str:
            self._last_activity_str = value
        else:
            self._last_activity_str = value.strftime("%Y-%m-%dT%H:%M:%S.%f")
