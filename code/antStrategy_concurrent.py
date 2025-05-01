from common import AntPerception, AntAction, Direction, TerrainType
from ant import AntStrategy
import random
import time

class AntStrategy_concurrent(AntStrategy):
    def __init__(self):
        self.position = (0, 0)  # Posición relativa actual (comienza en (0,0))
        self.ants_last_action = {}  # ant_id -> last_action
        self.ant_states = {}  # Estado individual por hormiga

    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""

        # Get ant's ID to track its actions
        ant_id = perception.ant_id

        # State
        if ant_id not in self.ant_states:
            self.ant_states[ant_id] = {
                'map': [[TerrainType.COLONY]],
                'ant_map_position': [0, 0],
                'followed_path': []
            }
        
        self.update_map(ant_id, perception)
        
        # Reset path if the ant bumps into a wall.
        if (len(self.ant_states[ant_id]['followed_path']) > 0
            and (self.ant_states[ant_id]['followed_path'][0]
                 == AntAction.MOVE_FORWARD)):
            next_position =\
                self.compute_step(self.ant_states[ant_id]['ant_map_position'],
                                  perception.direction)
            if (self.ant_states[ant_id]['map'][next_position[0]][next_position[1]]
                == TerrainType.WALL):
                self.ant_states[ant_id]['followed_path'] = []

        if len(self.ant_states[ant_id]['followed_path']) == 0:
            # Pick up food if standing on it.
            if (
                not perception.has_food
                and (0, 0) in perception.visible_cells
                and perception.visible_cells[(0, 0)] == TerrainType.FOOD
                ):
                self.ants_last_action[ant_id] = AntAction.PICK_UP_FOOD
                return AntAction.PICK_UP_FOOD

            # Drop food if at colony and carrying food.
            if (
                perception.has_food
                and (0, 0) in perception.visible_cells
                and perception.visible_cells[(0, 0)] == TerrainType.COLONY
            ):
                return AntAction.DROP_FOOD
            
            # Find a path to colony if carrying food.
            if perception.has_food:
                self.ant_states[ant_id]['followed_path'] =\
                    self.shortest_path_to_terrain(ant_id, TerrainType.COLONY,
                                                  perception)
            # Find a path to food some is on the map.
            else:
                path_to_food =\
                    self.shortest_path_to_terrain(ant_id, TerrainType.FOOD,
                                                  perception)
                path_to_unknown =\
                    self.shortest_path_to_terrain(ant_id, -1, perception)
                path_to_corner =\
                    self.shortest_path_to_corner(ant_id, perception)
                if len(path_to_food) > 0:
                    self.ant_states[ant_id]['followed_path'] = path_to_food
                elif len(path_to_unknown) > 0:
                    self.ant_states[ant_id]['followed_path'] = path_to_unknown
                # If the map is fully explored, we find a path to a random
                # empty spot.
                # Could be optimized by forcing the ant to go to the edges of
                # the map.
                elif len(path_to_corner) > 0:
                    self.ant_states[ant_id]['followed_path'] = path_to_corner
                else:
                    return AntAction.TURN_LEFT
        # Follow current path.
        action = self.ant_states[ant_id]['followed_path'][0]
        del self.ant_states[ant_id]['followed_path'][0]
        self.update_ant_map_position(ant_id, perception.direction, action)
        return action

    def update_map(self, ant_id: int, perception: AntPerception):
        """Updates the map of ant ant_id"""
        for pos, terrain in perception.visible_cells.items():
            current_map = self.ant_states[ant_id]['map']
            ant_pos = self.ant_states[ant_id]['ant_map_position']
            point_to_add = [pos[1]+ant_pos[0], pos[0]+ant_pos[1]]
            # Extending the map if needed.
            while point_to_add[0] < 0:
                self.add_map_row(ant_id, True)
                point_to_add[0] += 1
                self.ant_states[ant_id]['ant_map_position'][0] += 1
            while point_to_add[0] >= len(current_map):
                self.add_map_row(ant_id, False)
            while point_to_add[1] < 0:
                self.add_map_column(ant_id, True)
                point_to_add[1] += 1
                self.ant_states[ant_id]['ant_map_position'][1] += 1
            while point_to_add[1] >= len(current_map[0]):
                self.add_map_column(ant_id, False)
            # Updating information on the map
            self.ant_states[ant_id]['map'][point_to_add[0]][point_to_add[1]] =\
                terrain
    
    def add_map_row(self, ant_id: int, top: bool):
        """Adds a row to the map of ant ant_id

        Args:
            ant_id: the id of the ant whose map we want to change
            top: true when the row to add is at the top of the map, false
                otherwise.
        """
        current_map = self.ant_states[ant_id]['map']
        to_add = list(-1 for i in range(len(current_map[0])))
        if top:
            to_add = [to_add]
            for row in current_map:
                to_add.append(row)
            self.ant_states[ant_id]['map'] = to_add
        else:
            self.ant_states[ant_id]['map'].append(to_add)
            
    def add_map_column(self, ant_id: int, left: bool):
        """Adds a column to the map of ant ant_id

        Args:
            ant_id: the id of the ant whose map we want to change
            left: true when the column to add is at the left of the map, false
                otherwise.
        """
        current_map = self.ant_states[ant_id]['map']
        if left:
            width = len(current_map[0])
            for i in range(len(current_map)):
                to_add = [-1]
                for j in range(width):
                    to_add.append(current_map[i][j])
                current_map[i] = to_add
        else:
            for i in range(len(current_map)):
                current_map[i].append(-1)
    
    def search_map(self, ant_id: int, terrain: TerrainType) -> list:
        """Searches for terrain in map.

        Args:
            ant_id: Id of an ant.
            terrain: The terrain we're looking for.
        Returns:
            Positions of all terrains like terrain.
        """
        terrains_position = []
        current_map = self.ant_states[ant_id]['map']
        for i in range(len(current_map)):
            for j in range(len(current_map[0])):
                if current_map[i][j] == terrain:
                    terrains_position.append([i, j])
        return terrains_position

    def search_map_edge(self, ant_id: int, terrain: TerrainType) -> list:
        """Searches for terrain in the edge of the map.

        Args:
            ant_id: Id of an ant.
            terrain: The terrain we're looking for.
        Returns:
            Positions of all terrains like terrain.
        """
        terrains_position = []
        current_map = self.ant_states[ant_id]['map']
        i = 0
        for j in range(len(current_map[0])):
            if current_map[i][j] == terrain:
                terrains_position.append([i, j])
        i = len(current_map) - 1
        for j in range(len(current_map[0])):
            if current_map[i][j] == terrain:
                terrains_position.append([i, j])
        j = 0
        for i in range(len(current_map)):
            if current_map[i][j] == terrain:
                terrains_position.append([i, j])
        j = len(current_map[0]) - 1
        for i in range(len(current_map)):
            if current_map[i][j] == terrain:
                terrains_position.append([i, j])
        return terrains_position     
    
    def compute_step(self, initial_position: list, direction: Direction) -> list:
        """Computes the new position after a step.

        Args:
            initial_position: The initial position.
            direction (Direction): The direction in which the ant moves.
        Returns:
            The new coordinates of the ant
        """
        initial_position = [initial_position[0], 
                            initial_position[1]]
        if direction == Direction.NORTH:
            initial_position[0] -= 1
        if direction == Direction.NORTHEAST:
            initial_position[0] -= 1
            initial_position[1] += 1
        if direction == Direction.EAST:
            initial_position[1] += 1
        if direction == Direction.SOUTHEAST:
            initial_position[0] += 1
            initial_position[1] += 1
        if direction == Direction.SOUTH:
            initial_position[0] += 1
        if direction == Direction.SOUTHWEST:
            initial_position[0] += 1
            initial_position[1] -= 1
        if direction == Direction.WEST:
            initial_position[1] -= 1
        if direction == Direction.NORTHWEST:
            initial_position[0] -= 1
            initial_position[1] -= 1
        return initial_position
    def move_to(self, ant_id: int, position: list,
                perception: AntPerception) -> AntAction:
        """Returns an action of ant ant_id to move to position.

        Args:
            ant_id: The id of an ant.
            position: The position the ants moves to. Must be next to the
                current position of ant ant_id.
            perception: Perception of ant ant_id.

        Returns:
            An action of the ant to move to or orients itself towards position.
        """
        current_position = self.ant_states[ant_id]['ant_map_position']
        if (tuple(self.compute_step(current_position, perception.direction))
            == tuple(position)):
            return AntAction.MOVE_FORWARD
        # We could optimize this part by choosing the shortest turn.
        else:
            return AntAction.TURN_LEFT
    
    def is_position_out_of_bounds(self, ant_id: int, position: list) -> bool:
        current_map = self.ant_states[ant_id]['map']
        return (position[0] < 0 or position[0] >= len(current_map)
                or position[1] < 0 or position[1] >= len(current_map[0]))

    def update_ant_map_position(self, ant_id: int, direction: Direction, action: AntAction):
        if action == AntAction.MOVE_FORWARD:
            new_position =\
                self.compute_step(self.ant_states[ant_id]['ant_map_position'],
                                  direction)
            if (not self.is_position_out_of_bounds(ant_id, new_position)):
                self.ant_states[ant_id]['ant_map_position'] = new_position
    
    def shortest_path(self, ant_id: int, start_position: list,
                      end_position: list, start_direction: Direction) -> list:
        """Returns the shortest know path between two positions for ant ant_id.

        Args:
            ant_id: The id of the ant.
            start_position: The starting position of the path.
            end_position: The end position of the path.
            start_direction: The starting direction of the ant.

        Returns:
            A sequence of actions to reach end_position from start_position.
        """
        class AntState:
            def __init__(self, position: tuple, direction: Direction,
                strategy: AntStrategy_concurrent,
                parent, parent_action: AntAction):
                self.position = position
                self.direction = direction
                self.strategy = strategy
                self.parent = parent
                self.parent_action = parent_action
            def __str__(self):
                return str(self.position, self.direction)
            def get_neighbours(self, ant_id: int):
                """Get neighouring states.
                Args:
                    ant_id: The id of an ant.
                """
                current_map = self.strategy.ant_states[ant_id]['map']
                neighbours = []
                neighbours.append(
                    AntState(
                        self.position, Direction.get_left(self.direction),
                        self.strategy, self, AntAction.TURN_LEFT
                        )
                )
                neighbours.append(
                    AntState(
                        self.position, Direction.get_right(self.direction),
                        self.strategy, self, AntAction.TURN_RIGHT
                        )
                )
                forward_position =\
                    tuple(self.strategy.compute_step(self.position,
                                                     self.direction))
                if (not self.strategy.is_position_out_of_bounds(
                        ant_id,
                        forward_position)
                    and (current_map[forward_position[0]][forward_position[1]])
                        != TerrainType.WALL):
                    neighbours.append(
                        AntState(
                        forward_position, self.direction, self.strategy, self,
                        AntAction.MOVE_FORWARD
                        )
                    )
                return neighbours
            def path_to_origin(self):
                path = []
                current = self
                while current.parent_action != None:
                    path.append(current.parent_action)
                    current = current.parent
                return path
        
        class PriorityQueue:
            def __init__(self):
                self.queue = {}
                self.length = 0
            def __str__(self):
                return str(self.queue)
            def push(self, index: int, item):
                """Pushes an item into the queue."""
                if not index in self.queue.keys():
                    self.queue[index] = set()
                self.queue[index].add(item)
                self.length += 1
            def pop(self):
                """Pops the item with the smallest index."""
                smallest_index = min(self.queue.keys())
                popped = self.queue[smallest_index].pop()
                self.length -= 1
                if len(self.queue[smallest_index]) == 0:
                    del self.queue[smallest_index]
                return smallest_index, popped

        starting_state =\
            AntState(tuple(start_position), start_direction, self, None, None)
        frontier = PriorityQueue()
        frontier.push(distance_to(start_position, end_position),
                      starting_state)
        explored_positions = set()
        while frontier.length > 0:
            current_state_distance, current_state = frontier.pop()
            current_state_distance -=\
                distance_to(current_state.position, end_position)
            if current_state.position == tuple(end_position):
                return list(reversed(current_state.path_to_origin()))
            for neighbour in current_state.get_neighbours(ant_id):
                if ((neighbour.position, neighbour.direction)
                    not in explored_positions):
                    explored_positions.add((neighbour.position,
                                            neighbour.direction))
                    new_distance =\
                        current_state_distance + 1\
                        + distance_to(neighbour.position, end_position)
                    frontier.push(new_distance, neighbour)
        raise Exception('Frontier exhausted')
    def shortest_path_to_terrain(
        self, ant_id: int, terrain_type: int,
        perception: AntPerception) -> list:
        """Computes the shortest path to a specific terrain type.

        Args:
            ant_id: The id of an ant.
            terrain_type: The terrain for which the shortest path has to be
                computed.
                Can be a TerrainType or -1.
            perception: The perception of ant ant_id.
        
        Returns:
            A list of actions representing the shortest path to a random tile
            of type terrain_type if there is one, an empty list otherwise.
        """
        terrain_positions = []
        if terrain_type == -1:
            terrain_positions = self.search_map_edge(ant_id, terrain_type)
        if len(terrain_positions) == 0:
            terrain_positions = self.search_map(ant_id, terrain_type)
        if len(terrain_positions) == 0: return []
        terrain_position = \
            random.choice(terrain_positions)
        current_position = self.ant_states[ant_id]['ant_map_position']
        path_to_terrain =\
            self.shortest_path(ant_id, current_position, terrain_position,
                               perception.direction)
        return path_to_terrain
    
    def shortest_path_to_corner(self, ant_id: int,
                                perception: AntPerception) -> list:
        """Computes shortest path to a random corner of the map.

        Args:
            ant_id: The id of an ant.
            perception: The perception of ant ant_id.

        Returns:
            A list of actions representing the shortest path to a random
            corner of the map.
        """
        current_map = self.ant_states[ant_id]['map']
        corners = [[0, 0], [0, len(current_map[0])-1], [len(current_map)-1, 0],
                   [len(current_map)-1, len(current_map[0])-1]]
        corner = random.choice(corners)
        path = self.shortest_path(ant_id, 
                                  self.ant_states[ant_id]['ant_map_position'],
                                  corner, perception.direction)
        return path

def distance_to(start_position, end_position):
    diagonal_distance =\
        min(abs(start_position[0]-end_position[0]),
            abs(start_position[1]-end_position[1]))
    line_distance =\
        max(abs(start_position[0]-end_position[0])-diagonal_distance,
            abs(start_position[1]-end_position[1])-diagonal_distance)
    return diagonal_distance + line_distance
