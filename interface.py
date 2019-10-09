# Worms Bot
# Entelect Challenge 2019
# Mallin Moolman


import json
from pathlib import Path

from state import State


def move_to_string(move):
    if move.target is None:
        # Nothing
        return move.move_type.value

    # Check for select
    if move.select is None:
        move_str = ""
    else:
        move_str = "select {};".format(move.select.id + 1)

    if not isinstance(move.target, tuple):
        # Shoot
        return move_str + "{} {}".format(move.move_type.value,
                                         move.target.value)
    else:
        # Dig, Move, Banana, Snowball
        x, y = move.target
        return move_str + "{} {} {}".format(move.move_type.value, x, y)


def output_move(round_num, move):
    move_str = move_to_string(move)
    print(f"C;{round_num};{move_str}")


def load_path(file_path):
    with file_path.open("r") as f:
        json_state = json.load(f)
        return State(json_state)


def load_state(round_num):
    file_path = Path("./rounds/") / round_num / "state.json"
    return load_path(file_path)
