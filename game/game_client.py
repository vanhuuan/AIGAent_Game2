import time
import sys
import os

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client import Client
from pathfinding import shortest_path, find_adjacent_resources
from logs import log

class GameClient(Client):
    def __init__(self, name):
        log(f"Initializing GameClient with name: {name}", "[GameClient]")
        super().__init__()
        time.sleep(2)  # Wait for the client to connect and receive player info
        self.set_player_name(name)
        self.messages: list = []
        self.entity_positions: dict = {
            'w': [],
            'c': [],
            'r': [],  # Rock instead of food
            's': [],
            'a': [], 
            '0': [],
            '1': [], 
            '2': [], 
            '3': [], 
            '4': [], 
            '5': [], 
            '6': []
        }
        # Add exploration tracking
        self.visited_positions = set()
        self.last_direction = None
        self.exploration_row = 0
        self.exploration_col = 0
        log(f"GameClient initialized successfully for player: {name}", "[GameClient]")

    def _get_next_exploration_direction(self, player) -> int:
        """Determine the next direction for exploration based on current state."""
        current_pos = (player.row, player.col)
        self.visited_positions.add(current_pos)
        
        # Define possible directions: left(0), right(1), up(2), down(3)
        directions = [(0, -1, 0), (0, 1, 1), (-1, 0, 2), (1, 0, 3)]  # (row_diff, col_diff, direction)
        
        # First try to continue in the same direction if possible
        if self.last_direction is not None:
            row_diff, col_diff, dir = directions[self.last_direction]
            next_pos = (player.row + row_diff, player.col + col_diff)
            if (0 <= next_pos[0] < len(player.grid) and 
                0 <= next_pos[1] < len(player.grid[0]) and 
                next_pos not in self.visited_positions and
                (player.grid[next_pos[0]][next_pos[1]] == 'g' or 
                 player.grid[next_pos[0]][next_pos[1]] == '-1')):
                return self.last_direction
        
        # If can't continue in same direction, try other directions
        # Prioritize horizontal movement (left/right) over vertical (up/down)
        preferred_directions = [0, 1, 2, 3]  # left, right, up, down
        for dir in preferred_directions:
            row_diff, col_diff, _ = directions[dir]
            next_pos = (player.row + row_diff, player.col + col_diff)
            if (0 <= next_pos[0] < len(player.grid) and 
                0 <= next_pos[1] < len(player.grid[0]) and 
                next_pos not in self.visited_positions and
                (player.grid[next_pos[0]][next_pos[1]] == 'g' or 
                 player.grid[next_pos[0]][next_pos[1]] == '-1')):
                return dir
        
        # If all directions are blocked, try to find any unvisited position
        for dir in range(4):
            row_diff, col_diff, _ = directions[dir]
            next_pos = (player.row + row_diff, player.col + col_diff)
            if (0 <= next_pos[0] < len(player.grid) and 
                0 <= next_pos[1] < len(player.grid[0]) and
                (player.grid[next_pos[0]][next_pos[1]] == 'g' or 
                 player.grid[next_pos[0]][next_pos[1]] == '-1')):
                return dir
        
        return None

    def goto(self, position:tuple):
        log(f"Attempting to navigate to position: {position}", "[GameClient]")
        player = self.get_player()
        path = shortest_path(player.grid, (player.row, player.col), position)

        # If we're already at the target position, return
        if (player.row, player.col) == position:
            log(f"Already at target position {position}", "[GameClient]")
            return
            
        # Move one step along the path if possible
        if path:
            direction = path[0]
            direction_names = ["left", "right", "up", "down"]
            log(f"Moving {direction_names[direction]} towards {position}", "[GameClient]")
            self.move(direction)
        else:
            log(f"No path found to position {position}", "[GameClient]")

    def go_home(self):
        log("Returning to home base", "[GameClient]")
        player = self.get_player()
        home_position = (player.home_row, player.home_col)
        log(f"Home position is at {home_position}", "[GameClient]")
        self.goto(home_position)

    def collect_wood(self):
        log("Attempting to collect wood", "[GameClient]")
        player = self.get_player()
        if player.items_on_hand.count('w') > 0:
            log("Already carrying wood, returning home", "[GameClient]")
            self.go_home()
        else:
            if len(self.entity_positions['w']) > 0:
                wood_position = self.entity_positions['w'][0]
                log(f"Found wood at {wood_position}, moving to collect", "[GameClient]")
                self.goto(wood_position)
            else:
                log("No wood positions known, need to explore more", "[GameClient]")
    
    def collect_cotton(self):
        log("Attempting to collect cotton", "[GameClient]")
        player = self.get_player()
        if player.items_on_hand.count('c') > 0:
            log("Already carrying cotton, returning home", "[GameClient]")
            self.go_home()
        else:
            if len(self.entity_positions['c']) > 0:
                cotton_position = self.entity_positions['c'][0]
                log(f"Found cotton at {cotton_position}, moving to collect", "[GameClient]")
                self.goto(cotton_position)
            else:
                log("No cotton positions known, need to explore more", "[GameClient]")
    
    def collect_sword(self):
        log("Attempting to collect sword", "[GameClient]")
        if len(self.entity_positions['s']) > 0:
            sword_position = self.entity_positions['s'][0]
            log(f"Found sword at {sword_position}, moving to collect", "[GameClient]")
            self.goto(sword_position)
            player = self.get_player()
            if player.row == sword_position[0] and player.col == sword_position[1]:
                log(f"Reached sword position, removing from known positions", "[GameClient]")
                self.entity_positions['s'] = []
        else:
            log("No sword positions known", "[GameClient]")

    def collect_armor(self):
        log("Attempting to collect armor", "[GameClient]")
        if len(self.entity_positions['a']) > 0:
            armor_position = self.entity_positions['a'][0]
            log(f"Found armor at {armor_position}, moving to collect", "[GameClient]")
            self.goto(armor_position)
            player = self.get_player()
            if player.row == armor_position[0] and player.col == armor_position[1]:
                log(f"Reached armor position, removing from known positions", "[GameClient]")
                self.entity_positions['a'] = []
        else:
            log("No armor positions known", "[GameClient]")

    def collect_reward(self, reward_position: tuple[int, int]):
        """Go to a specific position to collect a reward."""
        if not reward_position:
            log("No reward position provided", "[GameClient]")
            return
            
        log(f"Attempting to collect reward at {reward_position}", "[GameClient]")
        self.goto(reward_position)
        
        # If we've reached the reward position, consider the reward collected
        player = self.get_player()
        if (player.row, player.col) == reward_position:
            log(f"Reached reward position at {reward_position}", "[GameClient]")
            return True
        else:
            log(f"Still moving towards reward at {reward_position}", "[GameClient]")
        
        return False

    def explore(self):
        log("Starting exploration", "[GameClient]")
        player = self.get_player()
        current_position = (player.row, player.col)
        log(f"Current position: {current_position}", "[GameClient]")
        
        # Update entity positions from surrounding resources
        log("Scanning surroundings for resources", "[GameClient]")
        resources_around = find_adjacent_resources(player.grid, player.row, player.col)
        
        # Track newly discovered resources
        new_resources_found = False
        
        for key in resources_around.keys():
            # Skip rocks as they're not collectible
            if key == 'r':
                continue
                
            for value in resources_around[key]:
                if value not in self.entity_positions[key]:
                    self.entity_positions[key].append(value)
                    new_resources_found = True
                    log(f"Added new {key} resource at {value} to known positions", "[GameClient]")
        
        if new_resources_found:
            log("New resources discovered during exploration", "[GameClient]")
        else:
            log("No new resources found in current area", "[GameClient]")

        # Get next exploration direction
        next_direction = self._get_next_exploration_direction(player)
        
        if next_direction is not None:
            direction_names = ["left", "right", "up", "down"]
            log(f"Moving {direction_names[next_direction]} for exploration", "[GameClient]")
            self.move(next_direction)
            self.last_direction = next_direction
        else:
            log("No valid exploration direction found, resetting visited positions", "[GameClient]")
            # If we're stuck, reset visited positions to allow revisiting
            self.visited_positions.clear()
            # Try to find any unexplored tile
            from pathfinding import shortest_path_to_value
            path, target = shortest_path_to_value(player.grid, current_position, '-1')
            if path is not None and len(path) > 0:
                direction = path[0]
                direction_names = ["left", "right", "up", "down"]
                log(f"Moving {direction_names[direction]} towards unexplored area", "[GameClient]")
                self.move(direction)
                self.last_direction = direction
            else:
                log("No unexplored areas found nearby", "[GameClient]") 