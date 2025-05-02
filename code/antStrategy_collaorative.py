from common import AntPerception, AntAction, Direction, TerrainType
from ant import AntStrategy
import random
import time
import copy

class AntStrategy_concurrent(AntStrategy):
    def __init__(self):
        self.ants_last_action = {}
        self.ants_followed_path = {}

    def decide_action(self, perception: AntPerception) -> AntAction:
        # Get ant's ID to track its actions
        ant_id = perception.ant_id
        last_action = self.ants_last_action.get(ant_id, None)
        followed_path = self.ants_followed_path.get(ant_id, [])
        local_map = get_local_map(perception)

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
        # Otherwise, perform movement
        action = self._decide_movement(perception)
        self.ants_last_action[ant_id] = action
        return action

    def _decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        # If has food, try to move toward colony if visible
        if perception.has_food:
            for pos, terrain in perception.visible_cells.items():
                if terrain == TerrainType.COLONY:
                    if pos[1] > 0:  # Colony is ahead in some direction
                        return AntAction.MOVE_FORWARD
            print(print(perception.home_pheromone))
            for pos, pheromones_level in perception.home_pheromone.items():
                if pheromones_level > 0.1:
                    return AntAction.MOVE_FORWARD
        # If doesn't have food, try to move toward food if visible
        else:
            for pos, terrain in perception.visible_cells.items():
                if terrain == TerrainType.FOOD:
                    if pos[1] > 0:  # Food is ahead in some direction
                        return AntAction.MOVE_FORWARD
            for pos, pheromones_level in perception.food_pheromone.items():
                if pheromones_level > 0.1:
                    return AntAction.MOVE_FORWARD

        if perception.has_food: print('a')
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
    
def get_local_map(perception: AntPerception) -> list:
    """Creates a map of nearby tiles according to perception.

    Args:
        perception: Perception of the ant whose local map we want to make.
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
    return current_map

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