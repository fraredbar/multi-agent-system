import heapq, math, random
from typing import Dict, List, Tuple, Optional, Set

from common import TerrainType, Direction, AntAction, AntPerception
from ant import AntStrategy

Vec2 = Tuple[int, int]
Grid = List[List[int]]

C_STRAIGHT = 1.0
C_DIAG = 1.4
DELTA2DIR = {Direction.get_delta(d): d for d in Direction}


def heu(a: Vec2, b: Vec2) -> float:  # octile
    dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
    return max(dx, dy) + (math.sqrt(2)-1)*min(dx, dy)


class AntMem:
    def __init__(self):
        self.map: Grid = [[TerrainType.COLONY.value]]
        self.pos: Vec2 = (0, 0)
        self.dir: Direction = Direction.NORTH
        self.path: List[Vec2] = []

    @staticmethod
    def turn(cur: Direction, want: Optional[Direction]) -> AntAction:
        if want is None or cur == want:
            return AntAction.MOVE_FORWARD
        l, r = (cur.value - want.value) % 8, (want.value - cur.value) % 8
        return AntAction.TURN_LEFT if l <= r else AntAction.TURN_RIGHT

    def _grow(self, x: int, y: int):
        gl = max(0, -x); gr = max(0, x - (len(self.map[0])-1))
        gu = max(0, -y); gd = max(0, y - (len(self.map)-1))
        if gl or gr:
            for row in self.map:
                row[:0] = [-1]*gl; row.extend([-1]*gr)
            self.pos = (self.pos[0]+gl, self.pos[1])
        if gu:
            self.map[:0] = [[-1]*len(self.map[0]) for _ in range(gu)]
            self.pos = (self.pos[0], self.pos[1]+gu)
        if gd:
            self.map.extend([[-1]*len(self.map[0]) for _ in range(gd)])

    def _set(self, x: int, y: int, v: int):
        self._grow(x, y)
        if self.map[y][x] == -1 or v in (TerrainType.FOOD.value, TerrainType.COLONY.value):
            self.map[y][x] = v

    def integrate(self, p: AntPerception):
        for (dx, dy), terr in p.visible_cells.items():
            gx, gy = self.pos[0]+dx, self.pos[1]+dy
            self._set(gx, gy, terr.value)
        self._set(self.pos[0], self.pos[1], p.visible_cells.get((0,0), TerrainType.EMPTY).value)
        self.dir = p.direction

    # ----- A* (only seeking) -----
    def _neigh(self, n: Vec2):
        for d in Direction:
            dx, dy = Direction.get_delta(d)
            nx, ny = n[0]+dx, n[1]+dy
            if 0<=ny<len(self.map) and 0<=nx<len(self.map[0]) and self.map[ny][nx]!=TerrainType.WALL.value:
                yield (nx, ny), (C_DIAG if dx and dy else C_STRAIGHT)

    def plan(self, goal_pred):
        self.path.clear()
        src = self.pos
        pq: List[Tuple[float, Vec2]] = [(0.0, src)]
        came: Dict[Vec2, Vec2] = {}
        g: Dict[Vec2, float] = {src: 0.0}
        seen: Set[Vec2] = set()
        tgt: Optional[Vec2] = None
        while pq:
            _, cur = heapq.heappop(pq)
            if cur in seen: continue; seen.add(cur)
            if goal_pred(cur):
                tgt = cur; break
            for nxt, c in self._neigh(cur):
                ng = g[cur] + c
                if ng < g.get(nxt, math.inf):
                    g[nxt] = ng; came[nxt] = cur; heapq.heappush(pq, (ng + heu(nxt, src), nxt))
        if tgt is None: return
        rev: List[Vec2] = []
        while tgt != src:
            rev.append(tgt); tgt = came[tgt]
        self.path = list(reversed(rev))


# =====================================================================
class AntStrategy_smart(AntStrategy):
    def __init__(self):
        self.mem: Dict[int, AntMem] = {}
        self.prev: Dict[int, AntAction] = {}
        self.food_seen = False

    def _visible_dir(self, p: AntPerception, target: TerrainType) -> Optional[Direction]:
        for (dx, dy), terr in p.visible_cells.items():
            if terr == target:
                return DELTA2DIR.get((dx, dy))
        return None

    def _grad_dir(self, p: AntPerception, home: bool) -> Optional[Direction]:
        ph = p.home_pheromone if home else p.food_pheromone
        if not ph: return None
        (dx, dy), s = max(ph.items(), key=lambda kv: kv[1])
        if s < 0.0005: return None
        return DELTA2DIR.get((dx, dy))

    def _dir_to(self, src: Vec2, dst: Vec2) -> Direction:
        dx = 0 if dst[0]==src[0] else (1 if dst[0]>src[0] else -1)
        dy = 0 if dst[1]==src[1] else (1 if dst[1]>src[1] else -1)
        return DELTA2DIR.get((dx,dy), Direction.NORTH)

    def decide_action(self, p: AntPerception) -> AntAction: 
        aid = p.ant_id
        st = self.mem.setdefault(aid, AntMem())

        # update absolute pos
        if self.prev.get(aid) == AntAction.MOVE_FORWARD:
            dx, dy = Direction.get_delta(st.dir); st.pos = (st.pos[0]+dx, st.pos[1]+dy)

        st.integrate(p)

        if not self.food_seen and any(t == TerrainType.FOOD for t in p.visible_cells.values()):
            self.food_seen = True

        #PICK/DROP

        here = p.visible_cells.get((0,0))
        if not p.has_food and here == TerrainType.FOOD:
            self.food_seen = True
            st.path.clear()  # discard memory
            return AntAction.PICK_UP_FOOD
        if p.has_food and here == TerrainType.COLONY:
            return AntAction.DROP_FOOD

        if p.has_food:
            if not st.path:
                best_dir = self._visible_dir(p, TerrainType.COLONY) or self._grad_dir(p, home=True)
                if best_dir is None:
                    st.plan(lambda pos: st.map[pos[1]][pos[0]] == TerrainType.COLONY.value)
            if st.path:
                nxt = st.path[0]
                want = self._dir_to(st.pos, nxt)
                act = AntMem.turn(st.dir, want)
                if act == AntAction.MOVE_FORWARD:
                    st.path.pop(0)
            else:
                best_dir = self._visible_dir(p, TerrainType.COLONY) or self._grad_dir(p, home=True)
                act = AntMem.turn(st.dir, best_dir)
            pher = AntAction.DEPOSIT_FOOD_PHEROMONE
        else:
            if not st.path:
                if self.food_seen:
                    st.plan(lambda pos: st.map[pos[1]][pos[0]] == TerrainType.FOOD.value)
                else:
                    tgt: Optional[Vec2] = None; best = -1
                    for y,row in enumerate(st.map):
                        for x,v in enumerate(row):
                            if v == -1:
                                d = abs(x)+abs(y)
                                if d > best:
                                    best = d; tgt = (x,y)
                    if tgt:
                        st.plan(lambda pos, t=tgt: pos == t)
            if st.path:
                nxt = st.path[0]
                want = self._dir_to(st.pos, nxt)
                act = AntMem.turn(st.dir, want)
                if act == AntAction.MOVE_FORWARD:
                    st.path.pop(0)
            else:
                grad = self._grad_dir(p, home=False)
                act = AntMem.turn(st.dir, grad) if grad else (AntAction.MOVE_FORWARD if random.random()<0.6 else AntAction.TURN_LEFT)
            pher = AntAction.DEPOSIT_HOME_PHEROMONE

        # --- pheromone decision (50%) ---
        final = pher if (act == AntAction.MOVE_FORWARD and random.random()<0.5) else act
        self.prev[aid] = final
        return final
