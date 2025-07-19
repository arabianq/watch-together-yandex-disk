import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta

import bcrypt
import jwt

import config
from users.classes import User


def generate_uid(username: str) -> str:
    uid_bytes = (username + uuid.uuid4().hex).encode("utf-8")
    uid_hash = bcrypt.hashpw(uid_bytes, bcrypt.gensalt())
    return uid_hash.decode("utf-8")


def generate_token(user: User) -> str:
    user.last_activity = datetime.now()
    user_dict = asdict(user)
    encoded_jwt = jwt.encode(user_dict, config.SECRET, algorithm="HS256")
    return encoded_jwt


def decode_token(token: str) -> User | None:
    decoded_dict = jwt.decode(token, config.SECRET, algorithms="HS256")
    decoded_dict["last_activity"] = decoded_dict["_last_activity_str"]
    del decoded_dict["_last_activity_str"]
    try:
        return User(**decoded_dict)
    except Exception as e:
        logging.error(e)
        return None


def is_inactive_too_long(user: User) -> bool:
    dt1 = user.last_activity
    dt2 = datetime.now()

    diff = dt2 - dt1
    max_diff = timedelta(hours=config.MAX_USER_INACTIVE_HOURS)

    if diff > max_diff:
        return True
    return False
