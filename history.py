# Worms Bot
# Entelect Challenge 2019
# Mallin Moolman


import logging

from state import MoveType, CellType, Profession
from bot import BANANA_DAMAGE


DEFAULT = {
    "bananas_used": 0,
    "snowballs_used": 0,
}


def calc_damage(current_worms, previous_worms):
    damage = []
    for curr, prev in zip(current_worms, previous_worms):
        diff = prev.health - curr.health
        if diff > 3:  # Nothing other than lava does < 3 damage
            damage.append(diff)

    return damage


def dug_cells(state, last_state):
    dug = set()
    for cell in state.map:
        curr = state.map[cell]
        prev = last_state.map[cell]

        if curr.type == CellType.AIR and prev.type == CellType.DIRT:
            dug.add(cell)

    return dug


def own_dug_cells(state, last_move):
    if last_move.move_type == MoveType.DIG:
        return set([last_move.target])

    if last_move.move_type != MoveType.BANANA:
        return set()

    x, y = last_move.target
    cells = set()

    for dx, dy in BANANA_DAMAGE:
        target = (x + dx, y + dy)
        if target in state.map:
            cells.add(target)

    return cells


def calculate(last_state, state, last_move, previous):

    if last_state is None or previous is None:
        # First round
        return DEFAULT

    # Check snowballs using previous move
    if "snowball" in state.opp_previous_command:
        logging.info("Opponent used snowball")
        previous["snowballs_used"] += 1

    if "banana" in state.opp_previous_command:
        logging.info("Opponent used banana")
        previous["bananas_used"] += 1

    return previous


def old_calculate(last_state, state, last_move, previous):

    if last_state is None or previous is None:
        # First round
        return DEFAULT

    # Check snowballs using previous move
    if "snowball" in state.opp_previous_command:
        previous["snowballs_used"] += 1

    own_damage = calc_damage(state.own_worms, last_state.own_worms)
    opp_damage = calc_damage(state.opponent_worms, last_state.opponent_worms)

    if own_damage or opp_damage:
        logging.info("Own damage: %s, opp damage: %s", own_damage, opp_damage)

    # Check for push back
    if (last_move.move_type == MoveType.MOVE and
            len(own_damage) == 1 and
            len(opp_damage) == 1 and
            own_damage[0] == 20 and
            opp_damage[0] == 20):
        # This was a push back - no banana
        logging.info("Push back last round")
        return previous

    if (len(own_damage) > 1 or any(damage != 8 for damage in own_damage)):
        logging.info("Damaged by banana")
        previous["bananas_used"] += 1
        return previous

    dug = dug_cells(state, last_state)
    own_dug = own_dug_cells(state, last_move)
    # logging.info("Dug: %s", dug)
    # logging.info("Own dug: %s", own_dug)

    opp_dug = dug - own_dug
    logging.info("Opp dug: %s", opp_dug)

    if len(opp_dug) > 1:
        logging.info("Opponent dug with banana")
        previous["bananas_used"] += 1
        return previous

    return previous


def update_state(state, previous):
    for worm in state.opponent_worms:
        if worm.profession == Profession.AGENT:
            worm.bananas -= previous["bananas_used"]
            if worm.health > 0:
                logging.info("Opponent has %d bananas", worm.bananas)
        if worm.profession == Profession.TECHNOLOGIST:
            worm.snowballs -= previous["snowballs_used"]
            if worm.health > 0:
                logging.info("Opponent has %d snowballs", worm.snowballs)
