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
                'path': [],
                'return_path': [],
                'carrying_food': False,
                'direction': 0  # 0 a 7, representa la dirección actual de la hormiga

            }

        state = self.ant_states[ant_id]

        # If colony is visible detect it
        """for pos, terrain in perception.visible_cells.items():
            if terrain == TerrainType.COLONY and self.colony_position is None:
                self.colony_position = pos"""

        # Priority 1: Pick up food if standing on it
        if (
    not perception.has_food
    and (0, 0) in perception.visible_cells
    and perception.visible_cells[(0, 0)] == TerrainType.FOOD
    ):
            if not state['path']:
        # Aún no ha explorado nada, giramos para buscar
                return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])
            state['carrying_food'] = True
            state['return_path'] = list(reversed(state['path']))
            state['path'] = []
            self.ants_last_action[ant_id] = AntAction.PICK_UP_FOOD
            return AntAction.PICK_UP_FOOD

        # Priority 2: Drop food if at colony and carrying food
        if (
            perception.has_food
            and TerrainType.COLONY in perception.visible_cells.values()
        ):
            for pos, terrain in perception.visible_cells.items():
                if terrain == TerrainType.COLONY:
                    if pos == (0, 0):  # Directly on colony
                        state['carrying_food'] = False
                        self.ants_last_action[ant_id] = AntAction.DROP_FOOD
                        return AntAction.DROP_FOOD
                    
    #============================================================================================    

        
            
        # Going back to colony with food, inverse path.
        if state['carrying_food']:
            # Saved path, follow it
            if len(state['return_path'])>0:
                action = state['return_path'].pop()
                self.ants_last_action[ant_id] = action
                return action
            
                    
        action = self._decide_movement(perception)
        # Only save path if doesn't have food.
        if not state['carrying_food'] and action in [
            AntAction.MOVE_FORWARD, AntAction.TURN_LEFT, AntAction.TURN_RIGHT
        ]:
            state['path'].append(action)

        self.ants_last_action[ant_id] = action
        return action


    #============================================================================================


    def _decide_movement(self, perception: AntPerception) -> AntAction:

        # If has food, try to move toward colony if visible
        if perception.has_food and perception.can_see_colony():
            direction = perception.get_colony_direction()
        elif not perception.has_food and perception.can_see_food():
            direction = perception.get_food_direction()
        else:
            direction = None

        if direction is not None:
            # Movimiento directo
            if direction == 0:
                return AntAction.MOVE_FORWARD
            # Diagonales derecha (noreste = 1, este = 2)
            elif direction in [1, 2]:
                return AntAction.TURN_RIGHT
            # Diagonales izquierda (noroeste = 7, oeste = 6)
            elif direction in [6, 7]:
                return AntAction.TURN_LEFT
            # Atrás o muy diagonal → giro aleatorio
            elif direction in [3, 4, 5]:
                return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])



        # Random movement if there is not choice.
        movement_choice = random.random()

        if movement_choice < 0.6:
            return AntAction.MOVE_FORWARD
        elif movement_choice < 0.8:
            return AntAction.TURN_LEFT
        else:
            return AntAction.TURN_RIGHT


