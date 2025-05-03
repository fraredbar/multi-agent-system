from common import AntPerception, AntAction, Direction, TerrainType
from ant import AntStrategy
import random
import time
import copy

class AntStrategy_collaborative(AntStrategy):
    def __init__(self):
        self.ants_last_action = {}
        self.ants_followed_path = {}
        # Amount of actions since the last time the ant followed a path of
        # food pheromones.
        self.following_food_hormone_path_counter = {}

    def decide_action(self, perception: AntPerception) -> AntAction:
        # Get ant's ID to track its actions
        ant_id = perception.ant_id
        last_action = self.ants_last_action.get(ant_id, None)
        local_map, local_position = get_local_map(perception)

        if len(self.ants_followed_path.get(ant_id, [])) == 0:
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
                self.ants_last_action[ant_id] = AntAction.DROP_FOOD
                return AntAction.DROP_FOOD
            if perception.has_food and perception.can_see_colony():
                self.ants_followed_path[ant_id] =\
                    path_to_terrain(local_map, local_position,
                                    TerrainType.COLONY, perception)
            elif not perception.has_food and perception.can_see_food():
                self.ants_followed_path[ant_id] =\
                    path_to_terrain(local_map, local_position,
                                    TerrainType.FOOD, perception)
            # Follow the pheromones back home.
            elif (perception.has_food and len(perception.home_pheromone) > 0
                  and max(perception.home_pheromone.values()) > 0):
                self.ants_followed_path[ant_id] =\
                    home_pheromone_path(local_map, local_position, perception)
            # Find a pheromone path to food.
            elif (not perception.has_food 
                  and len(perception.food_pheromone) > 0
                  and max(perception.food_pheromone.values()) > 70):
                self.following_food_hormone_path_counter[ant_id] = 8
                self.ants_followed_path[ant_id] =\
                    food_pheromone_path(local_map, local_position, perception)
        
        # Alternate between movement and dropping pheromones
        # If last action was not a pheromone drop, drop pheromone
        if last_action not in [
            AntAction.DEPOSIT_HOME_PHEROMONE,
            AntAction.DEPOSIT_FOOD_PHEROMONE,
        ]:
            if perception.has_food:
                self.ants_last_action[ant_id] = AntAction.DEPOSIT_FOOD_PHEROMONE
                return AntAction.DEPOSIT_FOOD_PHEROMONE
            else:
                self.ants_last_action[ant_id] = AntAction.DEPOSIT_HOME_PHEROMONE
                return AntAction.DEPOSIT_HOME_PHEROMONE
        # If following path, follows path.
        if len(self.ants_followed_path.get(ant_id, [])) > 0:
            action = self.ants_followed_path[ant_id][0]
            del self.ants_followed_path[ant_id][0]
            self.ants_last_action[ant_id] = action
            return action
        
        if self.following_food_hormone_path_counter.get(ant_id, 0) > 0:
            self.following_food_hormone_path_counter[ant_id] -= 1
            self.ants_last_action[ant_id] = AntAction.TURN_LEFT
            return AntAction.TURN_RIGHT

        action = self._decide_movement(perception)
        self.ants_last_action[ant_id] = action
        return action

    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        # Random movement if no specific goal
        movement_choice = random.random()

        if movement_choice < 0.6:  # 60% chance to move forward
            return AntAction.MOVE_FORWARD
        elif movement_choice < 0.8:  # 20% chance to turn left
            return AntAction.TURN_LEFT
        else:  # 20% chance to turn right
            return AntAction.TURN_RIGHT
        
        # # If the ant bumps into a wall, turn randomly.
        # if ((Direction.get_delta(perception.direction)
        #      not in perception.visible_cells)
        #     or Direction.get_delta(perception.direction) == TerrainType.WALL):
        #     return random.choice((AntAction.TURN_LEFT, AntAction.TURN_RIGHT))
        # return AntAction.MOVE_FORWARD
    
def get_local_map(perception: AntPerception) -> tuple:
    """Creates a map of nearby tiles according to perception.

    Args:
        perception: Perception of the ant whose local map we want to make.
    
    Returns:
        A map of the ant's surroundings and its position in it.
    """
    current_map = [[perception.visible_cells[(0, 0)]]]
    ant_position = [0, 0]
    for position, terrain in perception.visible_cells.items():
        point_to_add =\
            [position[1]+ant_position[0], position[0]+ant_position[1]]
        # Extending the map if needed.
        while point_to_add[0] < 0:
            current_map = add_array_row(current_map, True, -1)
            point_to_add[0] += 1
            ant_position[0] += 1
        while point_to_add[0] >= len(current_map):
            current_map = add_array_row(current_map, False, -1)
        while point_to_add[1] < 0:
            current_map = add_array_column(current_map, True, -1)
            point_to_add[1] += 1
            ant_position[1] += 1
        while point_to_add[1] >= len(current_map[0]):
            current_map = add_array_column(current_map, False, -1)
        current_map[point_to_add[0]][point_to_add[1]] = terrain
    return current_map, ant_position

def is_index_out_of_bounds(index: list, array: list) -> bool:
    """Checks index is in array.

    Args:
        index: A size 2 list.
        array: A 2 dimensional list.

    Returns:
        bool: True if index is out of bounds for array, false otherwise.
    """
    return (index[0] < 0 or index[0] >= len(array)
            or index[1] < 0 or index[1] >= len(array[0]))

def add_array_row(array: list, top: bool, filler) -> list:
    """Adds a row to the array.

    Args:
        array: A 2 dimensional list.
        top: true when the row is to be added at the top of the array, false
            otherwise.
        filler: What to put in the newly created row.
    
    Returns:
        A 2 dimensional list with a new row.
    """
    array = copy.deepcopy(array)
    to_add = list(filler for i in range(len(array[0])))
    if top:
        returned = [to_add] # Make to_add a 2 dimensional array.
        for row in array:
            returned.append(row)
        return returned
    array.append(to_add)
    return array

def add_array_column(array: list, left: bool, filler) -> list:
    """Adds a column to the array.

    Args:
        array: A 2 dimensional list.
        left: true when the column is to be added at the left of the array,
            false otherwise.
        filler: What to put in the newly created column.

    Returns:
        A 2 dimensional list with a new column.
    """
    array = copy.deepcopy(array)
    if left:
        width = len(array[0])
        for i in range(len(array)):
            to_add = [filler]
            for j in range(width):
                to_add.append(array[i][j])
            array[i] = to_add
        return array
    for i in range(len(array)):
        array[i].append(filler)
    return array

def compute_step(initial_position: list, direction: Direction) -> list:
    """Computes the new position after a step.

    Args:
        initial_position: The initial position.
        direction (Direction): The direction in which the ant moves.
    Returns:
        The new coordinates of the ant
    """
    initial_position = list(copy.copy(initial_position))
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

def distance_to(start_position, end_position):
    diagonal_distance =\
        min(abs(start_position[0]-end_position[0]),
            abs(start_position[1]-end_position[1]))
    line_distance =\
        max(abs(start_position[0]-end_position[0])-diagonal_distance,
            abs(start_position[1]-end_position[1])-diagonal_distance)
    return diagonal_distance + line_distance

def shortest_path(current_map: list, start_position: list, end_position: list,
                  start_direction: Direction) -> list:
    """Returns the shortest know path between two positions.

    Args:
        current_map: A 2 dimensional array representing a terrain map.
        start_position: The starting position of the path.
        end_position: The end position of the path.
        start_direction: The starting direction of the ant.

    Returns:
        A sequence of actions to reach end_position from start_position.
    """
    class AntState:
        def __init__(self, position: tuple, direction: Direction, parent,
                     parent_action: AntAction):
            self.position = position
            self.direction = direction
            self.parent = parent
            self.parent_action = parent_action
        def __str__(self):
            return str(self.position, self.direction)
        def get_neighbours(self):
            """Get neighouring states."""
            neighbours = []
            neighbours.append(
                AntState(
                    self.position, Direction.get_left(self.direction), self,
                    AntAction.TURN_LEFT
                    )
            )
            neighbours.append(
                AntState(
                    self.position, Direction.get_right(self.direction), self,
                    AntAction.TURN_RIGHT
                    )
            )
            forward_position =\
                tuple(compute_step(self.position, self.direction))
            if (not is_index_out_of_bounds(forward_position, current_map)
                and (current_map[forward_position[0]][forward_position[1]]
                     != TerrainType.WALL)):
                neighbours.append(
                    AntState(
                    forward_position, self.direction, self,
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
        AntState(tuple(start_position), start_direction, None, None)
    frontier = PriorityQueue()
    frontier.push(distance_to(start_position, end_position),
                  starting_state)
    explored_positions = set()
    while frontier.length > 0:
        current_state_distance, current_state = frontier.pop()
        # Get the distance from start_position.
        current_state_distance -=\
            distance_to(current_state.position, end_position)
        if current_state.position == tuple(end_position):
            return list(reversed(current_state.path_to_origin()))
        for neighbour in current_state.get_neighbours():
            if ((neighbour.position, neighbour.direction)
                not in explored_positions):
                explored_positions.add((neighbour.position,
                                        neighbour.direction))
                new_distance =\
                    current_state_distance + 1\
                    + distance_to(neighbour.position, end_position)
                frontier.push(new_distance, neighbour)
    raise Exception('Frontier exhausted')

def home_pheromone_path(current_map: list, position: list,
                        perception: AntPerception) -> list:
    """Computes a path to the oldest home pheromone in perception.

    Args:
        current_map: A 2 dimensional array representing a terrain map.
        position: The position of the ant in current_map.
        perception: The perfood_pheromone_pathception of an ant.

    Returns:
        The shortest path to the oldest home pheromone detected.
    """
    destination =\
        max(list(perception.home_pheromone.items()),
            key=lambda item: item[1])[0]
    destination = list((destination[1], destination[0]))
    destination[0] += position[0]
    destination[1] += position[1]
    return shortest_path(current_map, position, destination,
                         perception.direction)

def food_pheromone_path(current_map: list, position: list,
                        perception: AntPerception) -> list:
    """Computes a path to the oldest food pheromone in perception.

    Args:
        current_map: A 2 dimensional array representing a terrain map.
        perception: The perception of an ant.

    Returns:
        The shortest path to the oldest food pheromone detected.
    """
    destination =\
        max(list(perception.food_pheromone.items()),
            key=lambda item: item[1])[0]
    neighbours_position =\
        [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    # If following the path in the wrong direction.
    if destination in neighbours_position:
        return [AntAction.TURN_LEFT]
    destination = list((destination[1], destination[0]))
    destination[0] += position[0]
    destination[1] += position[1]
    return shortest_path(current_map, position, destination,
                         perception.direction)

def path_to_terrain(current_map: list, position: list,
                    terrain_type: TerrainType,
                    perception: AntPerception) -> list:
    """Computes a path to a terrain.

    Args:
        current_map: A 2 dimensional array representing a terrain map.
        terrain_type: A terrain type.
        perception: The perception of an ant.

    Returns:
        The shortest path to a terrain of terrain_type.
    """
    terrains = []
    for i in range(len(current_map)):
        for j in range(len(current_map[0])):
            if current_map[i][j] == terrain_type:
                terrains.append((i, j))       
    destination = random.choice(terrains)
    if destination[0] < 0 or destination[1] < 0:
        destination = (destination[1]+position[0], destination[0]+position[1])
    return shortest_path(current_map, position, destination,
                         perception.direction)