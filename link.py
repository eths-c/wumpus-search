# The code that defines the behaviour of Link.

from collections import deque

import config
from utils import Directions


class Link:

    def __init__(self, dungeon):
        # Link can inspect the current world state to choose a move.
        self.gameWorld = dungeon
        self.moves = [Directions.NORTH, Directions.SOUTH,
                      Directions.EAST, Directions.WEST]
        self._deltas = {
            Directions.NORTH: (0, 1),
            Directions.SOUTH: (0, -1),
            Directions.EAST: (1, 0),
            Directions.WEST: (-1, 0),
        }

    def makeMove(self):
        """Take one step along the shortest currently safe route to gold."""
        world = self.gameWorld
        start = (world.lLoc.x, world.lLoc.y)
        gold = {(p.x, p.y) for p in world.getGoldLocation()}

        if not gold:
            return self._safest_step(start, set())

        pits = {(p.x, p.y) for p in world.getPitsLocation()}
        wumpuses = {(p.x, p.y) for p in world.getWumpusLocation()}
        blocked = pits | wumpuses

        # Evaluate each possible first move separately. This lets us reject
        # a step that a nearby, moving Wumpus could occupy on its next turn.
        best_route = None
        for direction, destination in self._neighbours(start):
            if destination in blocked:
                continue
            if self._wumpus_may_enter(destination):
                continue

            remainder = self._shortest_path(destination, gold, blocked)
            if remainder is None:
                continue
            route = [direction] + remainder
            if best_route is None or len(route) < len(best_route):
                best_route = route

        if best_route:
            return best_route[0]

        # If every route is blocked or immediately dangerous, move to a safe
        # adjacent square that gives the greatest distance from the Wumpuses.
        return self._safest_step(start, blocked)

    def _neighbours(self, position):
        x, y = position
        for direction in self.moves:
            dx, dy = self._deltas[direction]
            next_x, next_y = x + dx, y + dy
            if 0 <= next_x <= self.gameWorld.maxX and \
                    0 <= next_y <= self.gameWorld.maxY:
                yield direction, (next_x, next_y)

    def _shortest_path(self, start, goals, blocked):
        """Return directions for a shortest path, or None if none exists."""
        queue = deque([(start, [])])
        visited = {start}

        while queue:
            position, path = queue.popleft()
            if position in goals:
                return path
            for direction, destination in self._neighbours(position):
                if destination in blocked or destination in visited:
                    continue
                visited.add(destination)
                queue.append((destination, path + [direction]))
        return None

    def _wumpus_may_enter(self, destination):
        """Check whether a Wumpus can move onto Link's next square."""
        if not config.dynamic:
            return False

        target_x, target_y = destination
        for wumpus in self.gameWorld.getWumpusLocation():
            x, y = wumpus.x, wumpus.y
            distance = ((x - target_x) ** 2 + (y - target_y) ** 2) ** 0.5

            if distance < config.senseDistance:
                # This mirrors World.moveToLink. When diagonally offset, the
                # Wumpus randomly moves on either the x or y axis.
                possible_moves = []
                if x == target_x:
                    possible_moves.append((x, self._step_towards(y, target_y)))
                elif y == target_y:
                    possible_moves.append((self._step_towards(x, target_x), y))
                else:
                    possible_moves.append((self._step_towards(x, target_x), y))
                    possible_moves.append((x, self._step_towards(y, target_y)))

                if destination in possible_moves:
                    return True

        return False

    @staticmethod
    def _step_towards(value, target):
        if value < target:
            return value + 1
        if value > target:
            return value - 1
        return value

    def _safest_step(self, start, blocked):
        candidates = [
            (direction, destination)
            for direction, destination in self._neighbours(start)
            if destination not in blocked
        ]
        if not candidates:
            # There is no safe neighbouring square; stay put by trying a
            # direction that points beyond the edge of the grid.
            for direction in self.moves:
                dx, dy = self._deltas[direction]
                if not (0 <= start[0] + dx <= self.gameWorld.maxX and
                        0 <= start[1] + dy <= self.gameWorld.maxY):
                    return direction
            return self.moves[0]

        wumpuses = [(p.x, p.y) for p in self.gameWorld.getWumpusLocation()]
        goals = [(p.x, p.y) for p in self.gameWorld.getGoldLocation()]

        def score(candidate):
            _, destination = candidate
            x, y = destination
            nearest_wumpus = min(
                (abs(x - wx) + abs(y - wy) for wx, wy in wumpuses),
                default=self.gameWorld.maxX + self.gameWorld.maxY,
            )
            nearest_gold = min(
                (abs(x - gx) + abs(y - gy) for gx, gy in goals),
                default=0,
            )
            avoids_next_wumpus_move = not self._wumpus_may_enter(destination)
            return avoids_next_wumpus_move, nearest_wumpus, -nearest_gold

        return max(candidates, key=score)[0]
