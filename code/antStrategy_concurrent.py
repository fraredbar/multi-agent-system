from common import AntPerception, AntAction, Direction, TerrainType
from ant import AntStrategy
import random

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
                'ant_map_position': [0, 0]
            }

        state = self.ant_states[ant_id]
        
        self.update_map(ant_id, perception)

        # Priority 1: Pick up food if standing on it
        if (
            not perception.has_food
            and (0, 0) in perception.visible_cells
            and perception.visible_cells[(0, 0)] == TerrainType.FOOD
            ):
            self.ants_last_action[ant_id] = AntAction.PICK_UP_FOOD
            return AntAction.PICK_UP_FOOD

        # Priority 2: Drop food if at colony and carrying food
        if (
            perception.has_food
            and (0, 0) in perception.visible_cells
            and perception.visible_cells[(0, 0)] == TerrainType.COLONY
        ):
            return AntAction.DROP_FOOD      
                    
        action = self._decide_movement(perception)

        self.ants_last_action[ant_id] = action
        self.update_ant_map_position(ant_id, perception.direction, action)
        return action

    def _decide_movement(self, perception: AntPerception) -> AntAction:

        # Random movement if there is not choice.
        movement_choice = random.random()

        if movement_choice < 0.6:
            return AntAction.MOVE_FORWARD
        elif movement_choice < 0.8:
            return AntAction.TURN_LEFT
        else:
            return AntAction.TURN_RIGHT

    def update_map(self, ant_id: int, perception: AntPerception):
        """Updates the map of ant ant_id"""
        for pos, terrain in perception.visible_cells.items():
            current_map = self.ant_states[ant_id]['map']
            ant_pos = self.ant_states[ant_id]['ant_map_position']
            print(pos, ant_pos)
            point_to_add = [pos[1]+ant_pos[0], pos[0]+ant_pos[1]]
            # Extending the map if needed.
            while point_to_add[0] < 0:
                print("a")
                self.add_map_row(ant_id, True)
                point_to_add[0] += 1
                self.ant_states[ant_id]['ant_map_position'][0] += 1
            while point_to_add[0] >= len(current_map):
                print("b")
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
            print(terrain)
            print("map:")
            for row in self.ant_states[ant_id]['map']:
                print(row)
    
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

    def update_ant_map_position(self, ant_id: int, direction: Direction, action: AntAction):
        if action == AntAction.MOVE_FORWARD:
            initial_position = [self.ant_states[ant_id]['ant_map_position'][0], 
                                self.ant_states[ant_id]['ant_map_position'][1]]
            if direction == Direction.NORTH:
                self.ant_states[ant_id]['ant_map_position'][0] -= 1
            if direction == Direction.NORTHEAST:
                self.ant_states[ant_id]['ant_map_position'][0] -= 1
                self.ant_states[ant_id]['ant_map_position'][1] += 1
            if direction == Direction.EAST:
                self.ant_states[ant_id]['ant_map_position'][1] += 1
            if direction == Direction.SOUTHEAST:
                self.ant_states[ant_id]['ant_map_position'][0] += 1
                self.ant_states[ant_id]['ant_map_position'][1] += 1
            if direction == Direction.SOUTH:
                self.ant_states[ant_id]['ant_map_position'][0] += 1
            if direction == Direction.SOUTHWEST:
                self.ant_states[ant_id]['ant_map_position'][0] += 1
                self.ant_states[ant_id]['ant_map_position'][1] -= 1
            if direction == Direction.WEST:
                self.ant_states[ant_id]['ant_map_position'][1] -= 1
            if direction == Direction.NORTHWEST:
                self.ant_states[ant_id]['ant_map_position'][0] -= 1
                self.ant_states[ant_id]['ant_map_position'][1] -= 1
            new_position = [self.ant_states[ant_id]['ant_map_position'][0], 
                            self.ant_states[ant_id]['ant_map_position'][1]]
            # Checks if the new position is out of bounds and resets the
            # position if needed.
            current_map = self.ant_states[ant_id]['map']
            if (new_position[0] < 0 or new_position[0] >= len(current_map)
                or new_position[1] < 0 or new_position[1] >= len(current_map[0])):
                self.ant_states[ant_id]['ant_map_position'] = initial_position
                
            
