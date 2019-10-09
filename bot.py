# Worms Bot
# Entelect Challenge 2019
# Mallin Moolman


import logging
import random
import math
import operator
from collections import defaultdict

from state import MoveType, CellType, Direction, Player, Move

DELTAS = {
    Direction.NW: (-1, -1),
    Direction.N: (0, -1),
    Direction.NE: (1, -1),
    Direction.W: (-1, 0),
    Direction.E: (1, 0),
    Direction.SW: (-1, 1),
    Direction.S: (0, 1),
    Direction.SE: (1, 1),
}

BANANA_DAMAGE = {
    (-2, 0): 7,
    (-1, -1): 11,
    (-1, 0): 13,
    (-1, 1): 11,
    (0, -2): 7,
    (0, -1): 13,
    (0, 0): 20,
    (0, 1): 13,
    (0, 2): 7,
    (1, -1): 11,
    (1, 0): 13,
    (1, 1): 11,
    (2, 0): 7,
}

SNOWBALL_DELTAS = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 0),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
]


CENTRE = (16, 16)
DAMAGE_MIN = 20
BANANA_DIG_MINIMUM = 8
MAX_DO_NOTHINGS = 11


def valid_moves(state, subject=None, include_lava=False):
    if subject is None:
        subject = state.current_worm

    moves = [Move(MoveType.NOTHING)]
    for dx, dy in DELTAS.values():
        x = subject.x + dx
        y = subject.y + dy
        if (x, y) in state.map:
            cell = state.map[(x, y)]
            if cell.type == CellType.DIRT:
                moves.append(Move(MoveType.DIG, (x, y)))
            elif cell.type == CellType.AIR or (include_lava and
                                               cell.type == CellType.LAVA):
                if cell.worm is None:
                    moves.append(Move(MoveType.MOVE, (x, y)))

    return moves


def hot_cells(state):
    if state.round < 100:
        return set()
    if state.round >= 302:
        return set([pos for pos, cell in state.map.items()
                    if cell.type != CellType.AIR])

    # Lava and everything adjacent to lava is hot
    hot = set()
    for pos, cell in state.map.items():
        x, y = pos
        if cell.type == CellType.LAVA:
            hot.add(pos)
            for dx, dy in DELTAS.values():
                new_pos = (x + dx, y + dy)
                if new_pos in state.map:
                    hot.add(new_pos)

    return hot


def can_shoot(state, subject=None):
    if subject is None:
        subject = state.current_worm

    valid = []
    for direction, (dx, dy) in DELTAS.items():
        (x, y) = subject.position
        while True:
            x += dx
            y += dy
            if int(dist((x, y), subject.position)) > 4:
                break
            if (x, y) not in state.map:
                break
            cell = state.map[(x, y)]
            if cell.type != CellType.AIR:
                break
            if cell.worm is not None:
                if cell.worm.player == Player.SELF:
                    break
                else:
                    valid.append((direction, cell.worm))
                    break

    return valid


def danger_to_current_worm(state):

    danger = set()
    for opponent_worm in state.opponent_worms:
        if not opponent_worm.alive:
            continue
        if not opponent_worm.active_before_next_turn:
            continue
        # Gun
        for direction, (dx, dy) in DELTAS.items():
            (x, y) = opponent_worm.position
            while True:
                x += dx
                y += dy
                if int(dist((x, y), opponent_worm.position)) > 4:
                    break
                if (x, y) not in state.map:
                    break
                cell = state.map[(x, y)]
                if cell.type != CellType.AIR:
                    break
                if cell.worm is not None:
                    if cell.worm != state.current_worm:
                        break
                    else:
                        danger.add(opponent_worm)

        # Banana
        if opponent_worm.bananas > 0:
            for cell in state.map:
                if int(dist(opponent_worm.position, cell)) <= 5:
                    for (dx, dy), damage in BANANA_DAMAGE.items():
                        base_x, base_y = cell
                        x = base_x + dx
                        y = base_y + dy
                        target = (x, y)
                        if target in state.map:
                            damage_cell = state.map[target]
                            if (damage_cell.worm is not None and
                                    damage_cell.worm == state.current_worm):
                                danger.add(opponent_worm)

    return danger


def banana_moves(state, subject=None):
    if subject is None:
        subject = state.current_worm

    move_list = []

    for target_cell in state.map:
        target_x, target_y = target_cell
        if int(dist(subject.position, target_cell)) <= 5:
            own_damage = 0
            opponent_damage = 0
            for (dx, dy), damage in BANANA_DAMAGE.items():
                damage_position = (target_x + dx, target_y + dy)
                if damage_position in state.map:
                    damage_cell = state.map[damage_position]
                    if damage_cell.worm is not None:
                        if damage_cell.worm.player == Player.SELF:
                            own_damage += damage
                        else:
                            opponent_damage += damage

            if own_damage == 0 and opponent_damage > 0:
                if DAMAGE_MIN is None or opponent_damage >= DAMAGE_MIN:
                    move_list.append((Move(MoveType.BANANA, target_cell), opponent_damage))

    return move_list


def snowball_move(state):

    if state.current_worm.snowballs <= 0:
        return None

    move_list = []

    for target_cell in state.map:
        if int(dist(state.current_worm.position, target_cell)) <= 5:
            own_hit = 0
            opp_hit = 0
            target_x, target_y = target_cell
            for dx, dy in SNOWBALL_DELTAS:
                hit_position = (target_x + dx, target_y + dy)
                if hit_position in state.map:
                    hit_cell = state.map[hit_position]
                    if hit_cell.worm is not None:
                        if hit_cell.worm.player == Player.SELF:
                            own_hit += 1
                        else:
                            if hit_cell.worm.rounds_until_unfrozen == 0:
                                opp_hit += 1

            if own_hit == 0 and opp_hit > 0:
                move_list.append((Move(MoveType.SNOWBALL, target_cell), opp_hit))

    if move_list:
        # Return highest number of opponents hit
        def has_worm(r):
            move, _ = r
            worm = state.map[move.target].worm
            if worm is not None and worm.player == Player.OPPONENT:
                return 1
            else:
                return 0

        move_list.sort(key=has_worm, reverse=True)
        move_list.sort(key=operator.itemgetter(1), reverse=True)
        return move_list[0][0]
    else:
        return None


def dist(a, b):
    a_x, a_y = a
    b_x, b_y = b
    return math.sqrt((a_x - b_x) ** 2 + (a_y - b_y) ** 2)


def filter_type(moves, t):
    return [m for m in moves if m.move_type == t]


def choose_max(move_list):
    return max(move_list, key=operator.itemgetter(1))[0]


def choose_min(move_list):
    return min(move_list, key=operator.itemgetter(1))[0]


def min_lava_radius(state):
    dists = [dist(pos, CENTRE) for pos, cell in state.map.items()
             if cell.type == CellType.LAVA]
    if dists:
        return min(dists)
    else:
        # Bigger than any possible radius
        return 1000


def weight_to_dirt(state, moves):
    move_list = []
    mlr = min_lava_radius(state)
    for move in moves:
        weight = 0
        for cell_pos, cell in state.map.items():
            if dist(cell_pos, CENTRE) < mlr and cell.type == CellType.DIRT:
                weight += 1 / (dist(cell_pos, move.target) ** 2)
        move_list.append((move, weight))
    return move_list


def dirt_remains(state):
    mlr = min_lava_radius(state)
    for pos, cell in state.map.items():
        if dist(pos, CENTRE) < mlr and cell.type == CellType.DIRT:
            return True
    return False


def shootable_cells(worm, state, dug=None, directions=None, subject=None,
                    include_banana=True):
    shootable = []
    if directions is None:
        directions = DELTAS
    if subject is None:
        subject = state.current_worm

    # Gun
    for direction in directions:
        (dx, dy) = DELTAS[direction]
        (x, y) = worm.position
        while True:
            x += dx
            y += dy
            if int(dist((x, y), worm.position)) > 4:
                break
            if (x, y) not in state.map:
                break
            cell = state.map[(x, y)]
            if cell.type != CellType.AIR and (x, y) != dug:
                break
            if cell.worm is not None:
                # Exclude current worm as it will move
                if cell.worm != subject:
                    break

            shootable.append((x, y))

    # Banana
    banana_cells = set()
    if include_banana and worm.bananas > 0:
        for target_cell in state.map:
            if int(dist(worm.position, target_cell)) <= 5:
                target_x, target_y = target_cell
                for dx, dy in BANANA_DAMAGE:
                    damage_position = (target_x + dx, target_y + dy)
                    if damage_position in state.map:
                        banana_cells.add(damage_position)

    shootable += list(banana_cells)

    return shootable


def opponent_shots(state):
    shots = []
    worm = state.opp_current_worm
    for direction, (dx, dy) in DELTAS.items():
        (x, y) = worm.position
        while True:
            x += dx
            y += dy
            if int(dist((x, y), worm.position)) > 4:
                break
            if (x, y) not in state.map:
                break
            cell = state.map[(x, y)]
            if cell.type != CellType.AIR:
                break
            if cell.worm is not None:
                if cell.worm.player == Player.SELF:
                    shots.append(direction)
                break

    return shots


def danger_from_current_shot(state, include_banana=True):
    # Get all shots opponent might make
    shots = opponent_shots(state)
    logging.info("Opponent shots: %s", shots)

    # Mark cells that those shots will hit (excluding own current worm)
    cells = shootable_cells(state.opp_current_worm, state, directions=shots,
                            include_banana=include_banana)
    logging.info("Shootable by current shot: %s", cells)

    return set(cells)


def weight_to_opponents(state, moves):
    move_list = []
    for move in moves:
        weight = 0
        for worm in state.opponent_worms:
            if worm.alive:
                weight += dist(move.target, worm.position)
        move_list.append((move, weight))

    return move_list


def furthest_from_opponents(state, moves):

    weighted = weight_to_opponents(state, moves)
    # Sort by distance to centre
    weighted.sort(key=lambda t: dist(t[0].target, CENTRE))
    return choose_max(weighted)


def nearest_to_opponents(state, moves):

    weighted = weight_to_opponents(state, moves)
    # Sort by distance to centre
    weighted.sort(key=lambda t: dist(t[0].target, CENTRE))
    return choose_min(weighted)


def closest_to_centre(state, moves):

    move_list = moves[:]
    move_list.sort(key=lambda m: dist(m.target, CENTRE))
    danger_cells = dangerous_cells(state)
    safe_moves = [m for m in move_list if m.target not in danger_cells]

    if safe_moves:
        logging.info("Moving towards safe/centre")
        return safe_moves[0]
    else:
        logging.info("Moving towards centre (unsafe)")
        return move_list[0]


def shoot_lowest_health(state):

    shoot = can_shoot(state)

    shoot.sort(key=lambda t: t[1].health)
    direction, target = shoot[0]
    return Move(MoveType.SHOOT, direction)


def next_n_active_worms(state, n):
    active = state.opp_current_worm_id
    worms = set()
    for i in range(n):
        if state.opponent_worms[active].rounds_until_unfrozen <= i:
            worms.add(state.opponent_worms[active])

        # Select next active worm
        for _ in range(3):
            active = (active + 1) % 3
            if state.opponent_worms[active].alive:
                break

    return worms


def dangerous_cells(state, dug=None, exclude_current=False, subject=None,
                    danger_worms=None, include_banana=True):

    if danger_worms is None:
        danger_worms = [w for w in state.opponent_worms
                        if w.active_before_next_turn]

    if exclude_current:
        danger_worms = [w for w in danger_worms if not w.active]

    danger_cells = set()
    for w in danger_worms:
        danger_cells.update(shootable_cells(w, state, dug, subject=subject,
                                            include_banana=include_banana))

    return danger_cells


def shootability_count(state):
    danger_worms = [w for w in state.opponent_worms
                    if w.active_before_next_turn and not w.active]

    counts = defaultdict(int)
    for w in danger_worms:
        cells = shootable_cells(w, state)
        for cell in cells:
            counts[cell] += 1

    return counts


def exclude_dangerous_digging(state, move_list):

    return [m for m in move_list
            if state.current_worm.position not in dangerous_cells(state, dug=m.target)]


def move_to_powerup(state):
    moves = filter_type(valid_moves(state), MoveType.MOVE)

    for move in moves:
        cell = state.map[move.target]
        if cell.powerup:
            return move
    return None


def move_to_lowest_health_opponent(state):

    opp = min(state.opponent_worms, key=lambda w: w.health)
    moves = filter_type(valid_moves(state), MoveType.MOVE)
    best_move = min(moves, key=lambda m: dist(m.target, opp.position))

    return best_move


def should_engage(state, subject=None):
    if subject is None:
        subject = state.current_worm

    shoot = can_shoot(state, subject)

    if len(shoot) != 1:
        return False

    if state.own_score <= state.opp_score:
        return False

    if subject.health < 8:
        return False

    return (shoot[0][1].health < subject.health or
            (shoot[0][1].health == subject.health and
             not (len(state.own_worms) == 1 and len(state.opponent_worms) > 1)))


def banana_dig(state):

    if state.current_worm.bananas <= 0:
        return None

    moves = []
    for cell in state.map:
        x, y = cell
        own_damage = False
        digs = 0
        if int(dist(state.current_worm.position, cell)) <= 5:
            for dx, dy in BANANA_DAMAGE:
                target = (x + dx, y + dy)
                if target in state.map:
                    target_cell = state.map[target]
                    if (target_cell.worm is not None and
                            target_cell.worm.player == Player.SELF):
                        own_damage = True
                    if target_cell.type == CellType.DIRT:
                        digs += 1

        if not own_damage and digs > 0:
            moves.append((Move(MoveType.BANANA, cell), digs))

    moves = [(m, d) for m, d in moves if d >= BANANA_DIG_MINIMUM]

    if moves:
        moves.sort(key=operator.itemgetter(1), reverse=True)
        logging.info("Banana digs: %s", moves)
        return moves[0][0]


def get_select_move(state):

    if state.selects_remaining == 0:
        return None

    logging.info("Selects: %d", state.selects_remaining)

    possibilities = []
    for worm in state.own_worms:
        if not worm.alive or worm.active:
            continue
        if worm.rounds_until_unfrozen > 0:
            continue

        if should_engage(state, worm):
            # Worm is supposed to be there
            logging.info("%s belongs there", worm)
            continue

        moves = filter_type(valid_moves(state, worm), MoveType.MOVE)
        danger_worms = next_n_active_worms(state, worm.turns_till_active)
        logging.info("For %s, danger worms: %s", worm, danger_worms)
        danger_cells = dangerous_cells(state, subject=worm,
                                       danger_worms=danger_worms)
        danger_targets = dangerous_cells(state, subject=worm)

        safe_moves = [m for m in moves if m.target not in danger_targets]

        if worm.position in danger_cells and safe_moves:
            move = furthest_from_opponents(state, safe_moves)
            move.select = worm
            possibilities.append(move)

    if possibilities:
        possibilities.sort(key=lambda m: m.select.health)
        return possibilities[0]
    else:
        return None


def run_away(state):

    # Get safe moves
    danger_cells = dangerous_cells(state)
    moves = filter_type(valid_moves(state), MoveType.MOVE)
    shoot = can_shoot(state)
    safe_moves = [m for m in moves if m.target not in danger_cells]

    logging.info("Dangerous: %s", danger_cells)
    logging.info("Safe: %s", safe_moves)

    # Move to safe moves
    if safe_moves:
        logging.info("Moving to safe cell")
        return furthest_from_opponents(state, safe_moves)

    # No safe move options

    # Exclude current shot from danger cells
    danger_besides_current = (dangerous_cells(state, exclude_current=True) |
                              danger_from_current_shot(state))
    safe_besides_current = [m for m in moves
                            if m.target not in danger_besides_current]
    logging.info("Safe-ish: %s", safe_besides_current)

    if safe_besides_current:
        logging.info("Moving to safe cell (assuming current opponent shot)")
        return furthest_from_opponents(state, safe_besides_current)

    dbc_excl_banana = (dangerous_cells(state, exclude_current=True,
                                       include_banana=False) |
                       danger_from_current_shot(state, include_banana=False))
    safe_besides = [m for m in moves if m.target not in dbc_excl_banana]
    if safe_besides:
        logging.info("Moving to safe cell (assuming current opponent shot excluding banana)")
        return furthest_from_opponents(state, safe_besides)

    if moves:
        # Move to least shootable cell
        shootable_counts = shootability_count(state)
        moves.sort(key=lambda m: shootable_counts[m.target])
        least_shootability = shootable_counts[min(moves, key=lambda m: shootable_counts[m.target]).target]
        current_shootability = shootable_counts[state.current_worm.position]
        least_shootable = [m for m in moves
                           if shootable_counts[m.target] == least_shootability]
        logging.info("Least shootable: %s", least_shootable)
        if least_shootable:
            if current_shootability < least_shootability:
                # Best to stay put
                if shoot:
                    # may as well shoot back
                    logging.info("At least shootable spot - shooting back")
                    return shoot_lowest_health(state)
                else:
                    logging.info("At least shootable spot - staying there")
                    return Move(MoveType.NOTHING)
            else:
                logging.info("Moving to least shootable cell")
                return furthest_from_opponents(state, least_shootable)
        else:
            # Move to anywhere else (this must be a bad spot)
            logging.info("Moving to any other cell")
            return furthest_from_opponents(state, moves)

    # No moves at all
    dig_moves = filter_type(valid_moves(state), MoveType.DIG)

    if dig_moves:
        logging.info("Digging to run away later")
        # return random.choice(dig_moves)
        return furthest_from_opponents(state, dig_moves)

    # No dig moves
    if shoot:
        logging.info("Shooting in desperation")
        return shoot_lowest_health(state)
    else:
        logging.info("Can't do anything")
        return Move(MoveType.NOTHING)


def get_move(state):

    for worm in state.own_worms:
        if worm.health > 0:
            if worm.rounds_until_unfrozen > 0:
                logging.info(f"{worm} is frozen for {worm.rounds_until_unfrozen} rounds")
            if worm.bananas > 0:
                logging.info(f"I have {worm.bananas} bananas")
            if worm.snowballs > 0:
                logging.info(f"I have {worm.snowballs} snowballs")

    for worm in state.opponent_worms:
        if worm.health > 0:
            if worm.rounds_until_unfrozen > 0:
                logging.info(f"{worm} is frozen for {worm.rounds_until_unfrozen} rounds")

    is_still_dirt = dirt_remains(state)
    shoot = can_shoot(state)
    logging.info("Shoot: %s", shoot)
    danger = danger_to_current_worm(state)
    logging.info("Danger: %s", danger)

    for w in state.opponent_worms:
        if w.active_before_next_turn:
            logging.info("ABNT: %s", w)

    # Get powerup if next to it
    powerup_move = move_to_powerup(state)
    if powerup_move is not None:
        logging.info("Getting powerup")
        return powerup_move

    moves = valid_moves(state)
    dig_only = filter_type(moves, MoveType.DIG)
    move_only = filter_type(moves, MoveType.MOVE)

    # Heat
    hot = hot_cells(state)
    if state.current_worm.position in hot:

        logging.info("On a hot cell")

        cold_moves = [m for m in move_only if m.target not in hot]
        if cold_moves:
            logging.info("Can move to cold cell")
            return closest_to_centre(state, cold_moves)

        if move_only:
            logging.info("Can move to non-lava cell")
            return closest_to_centre(state, move_only)

        lava_moves = valid_moves(state, include_lava=True)
        lava_moves_only = filter_type(lava_moves, MoveType.MOVE)
        if lava_moves_only:
            logging.info("Moving including lava")
            return closest_to_centre(state, lava_moves_only)
        else:
            # No lava or air to move to
            lava_dig_only = filter_type(lava_moves, MoveType.DIG)
            if lava_dig_only:
                logging.info("Digging towards centre")
                return closest_to_centre(state, lava_dig_only)
            else:
                # Also no dirt - surrounded by worms
                if shoot:
                    logging.info("Cornered - shooting")
                    return shoot_lowest_health(state)
                else:
                    logging.info("Nothing to do")
                    return Move(MoveType.NOTHING)

    # Filter out hot cells
    moves = [m for m in moves if m.target not in hot]
    # dig_only = filter_type(moves, MoveType.DIG)
    move_only = filter_type(moves, MoveType.MOVE)

    # Urgent moves
    if danger:
        if not shoot:
            logging.info("Running away from banana")
            return run_away(state)
        else:
            if not any(w.active_before_next_turn for _, w in shoot):
                # Take pot shot at vulnerable worm
                logging.info("Taking pot shot")
                return shoot_lowest_health(state)
            elif should_engage(state):
                logging.info("Should engage")
                return shoot_lowest_health(state)
            else:
                logging.info("Running away")
                return run_away(state)

    # Shoot if no danger - repeat of above
    if shoot:
        logging.info("Shoot but no danger")
        if not any(w.active_before_next_turn for _, w in shoot):
            # Take pot shot at vulnerable worm
            logging.info("Taking pot shot")
            return shoot_lowest_health(state)
        elif should_engage(state):
            logging.info("Should engage")
            return shoot_lowest_health(state)

    # No urgent move for current worm - check if it makes sense selecting
    select_move = get_select_move(state)
    if select_move is not None:
        logging.info("Selecting! Move: %s", select_move)
        return select_move

    # Throw snowball
    snowball = snowball_move(state)
    if snowball is not None:
        logging.info("Snowballing")
        return snowball

    # Dig with banana
    b_dig = banana_dig(state)
    if b_dig is not None:
        logging.info("Digging with banana")
        return b_dig

    safe_dig = exclude_dangerous_digging(state, dig_only)
    if len(safe_dig) != len(dig_only):
        logging.info("Eliminated dig due to danger")
    if safe_dig:
        return random.choice(safe_dig)

    # Filter out moving into danger
    danger_cells = dangerous_cells(state)
    old_move_only = move_only[:]
    move_only = [m for m in move_only if m.target not in danger_cells]
    if not move_only:
        if state.consecutive_do_nothings == MAX_DO_NOTHINGS:
            logging.info("Must do something!")
            return random.choice(old_move_only)
        else:
            logging.info("Danger all around - staying still")
            return Move(MoveType.NOTHING)

    if is_still_dirt:
        weighted = weight_to_dirt(state, move_only)
        return choose_max(weighted)

    # No dirt is left: endgame vs another digger bot
    logging.info("No dirt!!")
    move_only = filter_type(moves, MoveType.MOVE)
    if state.own_score < state.opp_score:
        if shoot:
            logging.info("Shooting lowest health target")
            return shoot_lowest_health(state)
        else:
            logging.info("Moving towards lowest health opponent")
            return move_to_lowest_health_opponent(state)
    else:
        if shoot:
            if not any(w.active_before_next_turn for _, w in shoot):
                logging.info("Taking pot shot")
                return shoot_lowest_health(state)
            elif should_engage(state):
                logging.info("Should engage")
                return shoot_lowest_health(state)
            else:
                logging.info("Running away")
                return run_away(state)
        else:
            logging.info("Moving away from opponents")
            return furthest_from_opponents(state, move_only)
