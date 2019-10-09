# Worms Bot
# Entelect Challenge 2019
# Mallin Moolman


from enum import Enum


class MoveType(Enum):
    NOTHING = "nothing"
    MOVE = "move"
    DIG = "dig"
    SHOOT = "shoot"
    BANANA = "banana"
    SNOWBALL = "snowball"


class CellType(Enum):
    DIRT = "DIRT"
    AIR = "AIR"
    SPACE = "DEEP_SPACE"
    LAVA = "LAVA"


class Player(Enum):
    SELF = "Self"
    OPPONENT = "Opponent"


class Profession(Enum):
    AGENT = "Agent"
    COMMANDO = "Commando"
    TECHNOLOGIST = "Technologist"


class Direction(Enum):
    NW = "NW"
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"


class Move:

    def __init__(self, move_type, target=None, select=None):
        self.move_type = move_type
        self.target = target
        self.select = select

    def __str__(self):
        if self.target is None:
            return f"{self.move_type.value}"
        else:
            if self.select is None:
                return f"{self.move_type.value}/{self.target}"
            else:
                return f"Select {self.select.id}/{self.move_type.value}/{self.target}"

    def __repr__(self):
        return self.__str__()


class Cell:

    def __init__(self, x, y, type_str):
        self.x = x
        self.y = y
        self.position = (x, y)
        self.type = CellType(type_str)
        self.worm = None
        self.powerup = None


class Worm:

    def __init__(self, x, y, health, id_, profession, ruf, player):
        self.x = x
        self.y = y
        self.position = (x, y)
        self.health = health
        self.alive = health > 0
        self.active = False
        self.bananas = 0
        self.snowballs = 0
        self.turns_till_active = None
        self.profession = Profession(profession)
        self.rounds_until_unfrozen = ruf

        self.id = id_
        self.player = player

        self.active_before_next_turn = False

    def __str__(self):
        return f"{self.player.value}/{self.id} [{self.x}, {self.y}]"

    def __repr__(self):
        return self.__str__()


class State:

    def __init__(self, js):
        self.round = js["currentRound"]
        self.consecutive_do_nothings = js["consecutiveDoNothingCount"]

        js_player = js["myPlayer"]
        js_opponent = js["opponents"][0]

        self.own_score = js_player["score"]
        self.opp_score = js_opponent["score"]

        self.current_worm_id = js_player["currentWormId"] - 1
        self.opp_current_worm_id = js_opponent["currentWormId"] - 1

        self.selects_remaining = js_player["remainingWormSelections"]
        self.opp_selects_remaining = js_opponent["remainingWormSelections"]

        self.opp_previous_command = js_opponent["previousCommand"]

        self.map = dict()
        for row in js["map"]:
            for cell in row:
                if cell["type"] != "DEEP_SPACE":
                    c = Cell(cell["x"], cell["y"], cell["type"])
                    if "powerup" in cell:
                        c.powerup = True
                    self.map[(cell["x"], cell["y"])] = c

        # Own worms
        self.own_worms = []
        for js_worm in js_player["worms"]:
            w = Worm(js_worm["position"]["x"], js_worm["position"]["y"],
                     js_worm["health"], js_worm["id"] - 1,
                     js_worm["profession"], js_worm["roundsUntilUnfrozen"],
                     Player.SELF)

            self.own_worms.append(w)
            if js_worm["id"] - 1 == self.current_worm_id:
                w.active = True
                self.current_worm = w
            if "bananaBombs" in js_worm:
                w.bananas = js_worm["bananaBombs"]["count"]
            if "snowballs" in js_worm:
                w.snowballs = js_worm["snowballs"]["count"]
            if w.health > 0:
                self.map[(js_worm["position"]["x"], js_worm["position"]["y"])].worm = w

        # Opponent worms
        self.opponent_worms = []
        for js_worm in js_opponent["worms"]:
            w = Worm(js_worm["position"]["x"], js_worm["position"]["y"],
                     js_worm["health"], js_worm["id"] - 1,
                     js_worm["profession"], js_worm["roundsUntilUnfrozen"],
                     Player.OPPONENT)

            self.opponent_worms.append(w)
            if js_worm["id"] - 1 == self.opp_current_worm_id:
                w.active = True
                self.opp_current_worm = w
            if w.profession == Profession.AGENT:
                w.bananas = 3  # This gets updated later if some are used
            if w.profession == Profession.TECHNOLOGIST:
                w.snowballs = 3  # updated later
            if w.health > 0:
                self.map[(js_worm["position"]["x"], js_worm["position"]["y"])].worm = w

        own_living_worms = sum(1 for worm in self.own_worms if worm.alive)
        opp_active = self.opp_current_worm_id
        own_active = self.current_worm_id

        for r in range(own_living_worms):

            if self.opponent_worms[opp_active].rounds_until_unfrozen <= r:
                self.opponent_worms[opp_active].active_before_next_turn = True

            self.own_worms[own_active].turns_till_active = r

            # Select next opponent active worm
            for i in range(3):
                opp_active = (opp_active + 1) % 3
                if self.opponent_worms[opp_active].alive:
                    break

            # Select own next active worm
            for j in range(3):
                own_active = (own_active + 1) % 3
                if self.own_worms[own_active].alive:
                    break
