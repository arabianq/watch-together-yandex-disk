import random
import string

CHARACTERS = string.ascii_letters


def generate_uid(length: int = 6) -> str:
    return "".join(random.choice(CHARACTERS) for _ in range(length))
