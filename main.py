# Worms Bot
# Entelect Challenge 2019
# Mallin Moolman


import logging
import sys
from pathlib import Path

import bot
import history
import interface


logging.basicConfig(stream=sys.stderr, level=logging.WARNING)


def run_bot():
    last_state = None
    last_move = None
    previous = None

    while True:
        try:
            round_num = input()

            state = interface.load_state(round_num)
            previous = history.calculate(last_state, state, last_move,
                                         previous)
            history.update_state(state, previous)
            last_state = state

            move = bot.get_move(state)
            interface.output_move(round_num, move)

            last_move = move

        except Exception as e:
            logging.exception(e)


def run_debug():
    # Debug mode - load one state file
    file_path = Path(sys.argv[1])
    bananas = int(sys.argv[2])
    state = interface.load_path(file_path)
    previous = history.DEFAULT
    previous["bananas_used"] = 3 - bananas
    history.update_state(state, previous)
    move = bot.get_move(state)
    print(interface.move_to_string(move))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_bot()
    else:
        run_debug()
