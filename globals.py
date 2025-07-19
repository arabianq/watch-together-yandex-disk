from movies.db import MoviesDB
from rooms.db import RoomsDB
from users.db import UsersDB

MOVIES_DATABASE: MoviesDB | None = None
USERS_DATABASE: UsersDB | None = None
ROOMS_DATABASE: RoomsDB | None = None
