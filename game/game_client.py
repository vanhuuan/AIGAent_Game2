import time
import sys
import os

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client import Client
from pathfinding import shortest_path, find_adjacent_resources
from logs import log
from config import Config

class GameClient(Client):
    def __init__(self, name):
        log(f"Initializing GameClient with name: {name}", "[GameClient]")
        super().__init__()
        self.name = name
        self.set_player_name(name)
        self.storage = {}  # Track our own storage
        self.items_on_hand = []  # Track items being carried (wood, cotton only)
        self.items_worn = {'sword': False, 'armor': False}  # Track equipped sword and armor
        self.entity_positions = {'w': [], 'c': [], 's': [], 'a': []}  # Track resource positions
        self.is_at_home = False
        self.win_condition = {'wood': 0, 'cotton': 0, 'fabric': 0, 'cotton_per_fabric': 2}  # Default win condition
        
        # Allow collecting both wood and cotton by default
        self.allow_collect_items(items=['w', 'c'])
        
        time.sleep(2)  # Wait for the client to connect and receive player info
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
        
        # Add movement history tracking
        self.movement_history = []
        self.last_positions = []
        self.max_history = 5  # Track last 5 positions
        
        # Add systematic exploration tracking
        self.exploration_phase = "center"  # center, up, down, left, right
        self.center_reached = False
        self.exploration_radius = 1
        self.max_exploration_radius = 8  # Maximum radius to explore from center
        
        log(f"GameClient initialized successfully for player: {name}", "[GameClient]")

    def set_win_condition(self, wood: int, cotton: int = 0, fabric: int = 0, cotton_per_fabric: int = 2):
        """Set the win condition requirements."""
        self.win_condition = {
            'wood': wood,
            'cotton': cotton,
            'fabric': fabric,
            'cotton_per_fabric': cotton_per_fabric
        }
        log(f"Win condition set: {self.win_condition}", "[GameClient]")

    def update_allowed_items(self):
        """Update allowed items based on what's still needed in storage."""
        player = super().get_player()
        
        # Calculate what's still needed
        wood_needed = max(0, self.win_condition['wood'] - 
                         self.get_storage_count('w'))
        
        # Calculate cotton needed for both direct cotton requirements and fabric conversion
        fabric_needed = max(0, self.win_condition.get('fabric', 0) - 
                           self.get_storage_count('fa'))
        cotton_for_fabric = fabric_needed * self.win_condition['cotton_per_fabric']
        cotton_needed = max(0, self.win_condition.get('cotton', 0) + cotton_for_fabric - 
                           self.get_storage_count('c'))
        
        # Only allow collection of items that are still needed
        allowed_items = []
        if wood_needed > 0:
            allowed_items.append('w')
        if cotton_needed > 0:
            allowed_items.append('c')
            
        # Update allowed items on server
        self.allow_collect_items(items=allowed_items)
        log(f"Updated allowed items to: {allowed_items} (wood needed: {wood_needed}, cotton needed: {cotton_needed}, fabric needed: {fabric_needed})", "[GameClient]")

    def get_player(self):
        """Get player information from server but ignore storage/on-hand data."""
        player = super().get_player()
        
        # Update our storage tracking based on player position
        if player.row == player.home_row and player.col == player.home_col:
            # We're at home, store any items we're carrying
            if self.items_on_hand:
                log(f"At home, storing items: {self.items_on_hand}", "[GameClient]")
                for item in self.items_on_hand:
                    if item in self.storage:
                        self.storage[item] += 1
                    else:
                        self.storage[item] = 1
                    log(f"Stored {item}, total in storage: {self.storage.get(item, 0)}", "[GameClient]")
                self.items_on_hand = []
                
                # Convert cotton to fabric automatically
                cotton_count = self.get_storage_count('c')
                cotton_per_fabric = self.win_condition['cotton_per_fabric']
                
                if cotton_count >= cotton_per_fabric:
                    fabric_created = cotton_count // cotton_per_fabric
                    cotton_remaining = cotton_count % cotton_per_fabric
                    
                    # Update storage counts
                    self.storage['c'] = cotton_remaining
                    if 'fa' in self.storage:
                        self.storage['fa'] += fabric_created
                    else:
                        self.storage['fa'] = fabric_created
                    
                    log(f"Converted {fabric_created * cotton_per_fabric} cotton to {fabric_created} fabric. Cotton remaining: {cotton_remaining}", "[GameClient]")
                
                # Recalculate needs after storing items and converting fabric
                wood_needed = max(0, self.win_condition['wood'] - self.get_storage_count('w'))
                fabric_needed = max(0, self.win_condition.get('fabric', 0) - self.get_storage_count('fa'))
                cotton_for_fabric = fabric_needed * self.win_condition['cotton_per_fabric']
                cotton_needed = max(0, self.win_condition.get('cotton', 0) + cotton_for_fabric - self.get_storage_count('c'))
                
                log(f"Recalculated needs - Wood: {wood_needed}, Cotton: {cotton_needed}, Fabric: {fabric_needed}", "[GameClient]")
                
                # Check if win condition is met
                if wood_needed == 0 and cotton_needed == 0 and fabric_needed == 0:
                    log("WIN CONDITION MET! All required resources stored at home!", "[GameClient]")
                
                # Update allowed items only when at home, after all calculations
                self.update_allowed_items()
                
            self.is_at_home = True
        else:
            self.is_at_home = False
            
        # Update player's store and items_on_hand with our tracked values
        player.store = []
        for item, count in self.storage.items():
            player.store.extend([item] * count)
        player.items_on_hand = self.items_on_hand.copy()
        
        return player

    def collect_item(self, item_type: str):
        """Collect an item - equipment goes to items_worn, resources to items_on_hand."""
        if item_type == 's':  # Sword
            if not self.items_worn['sword']:
                self.items_worn['sword'] = True
                log(f"Equipped sword", "[GameClient]")
                return True
            else:
                log(f"Already wearing sword", "[GameClient]")
                return False
        elif item_type == 'a':  # Armor
            if not self.items_worn['armor']:
                self.items_worn['armor'] = True
                log(f"Equipped armor", "[GameClient]")
                return True
            else:
                log(f"Already wearing armor", "[GameClient]")
                return False
        else:  # Resources (wood, cotton, etc.)
            if len(self.items_on_hand) < 2:
                self.items_on_hand.append(item_type)
                log(f"Collected {item_type}, now carrying: {self.items_on_hand}", "[GameClient]")
                return True
            else:
                log(f"Backpack full, cannot collect {item_type}", "[GameClient]")
                return False

    def store_items(self):
        """Store all items in hand to storage. Equipment stays worn."""
        if self.is_at_home:
            for item in self.items_on_hand:
                if item in self.storage:
                    self.storage[item] += 1
                else:
                    self.storage[item] = 1
            self.items_on_hand = []
            log(f"Stored all backpack items, current storage: {self.storage}", "[GameClient]")
            log(f"Equipment worn: {self.items_worn}", "[GameClient]")
            return True
        return False

    def get_storage_count(self, item_type: str) -> int:
        """Get the count of a specific item in storage."""
        return self.storage.get(item_type, 0)

    def get_items_on_hand_count(self, item_type: str) -> int:
        """Get the count of a specific item in backpack."""
        return self.items_on_hand.count(item_type)

    def is_wearing(self, item_type: str) -> bool:
        """Check if wearing specific equipment."""
        if item_type == 's':
            return self.items_worn['sword']
        elif item_type == 'a':
            return self.items_worn['armor']
        return False

    def get_total_item_count(self, item_type: str) -> int:
        """Get the total count of a specific item (storage + on hand + worn)."""
        total = self.get_storage_count(item_type) + self.get_items_on_hand_count(item_type)
        if self.is_wearing(item_type):
            total += 1
        return total

    def move(self, direction: int):
        """Move in the specified direction and handle item collection."""
        super().move(direction)
        player = self.get_player()
        
        # Update movement history
        current_pos = (player.row, player.col)
        self.last_positions.append(current_pos)
        if len(self.last_positions) > self.max_history:
            self.last_positions.pop(0)
        
        # Check if we're standing on equipment and collect it
        current_cell = player.grid[player.row][player.col]
        if current_cell in ['s', 'a']:  # Equipment that we stand on to collect
            if self.collect_item(current_cell):
                log(f"Collected {current_cell} at position ({player.row}, {player.col})", "[GameClient]")
                # Remove from grid and entity positions
                player.grid[player.row][player.col] = 'g'
                pos = (player.row, player.col)
                if pos in self.entity_positions[current_cell]:
                    self.entity_positions[current_cell].remove(pos)
        
        # Check adjacent cells for resources (wood, cotton) that we collect by standing next to
        adjacent_positions = [
            (player.row - 1, player.col),  # up
            (player.row + 1, player.col),  # down
            (player.row, player.col - 1),  # left
            (player.row, player.col + 1)   # right
        ]
        
        for adj_row, adj_col in adjacent_positions:
            if (0 <= adj_row < len(player.grid) and 0 <= adj_col < len(player.grid[0])):
                adj_cell = player.grid[adj_row][adj_col]
                if adj_cell in ['w', 'c']:  # Resources we collect by standing adjacent
                    if self.collect_item(adj_cell):
                        log(f"Collected {adj_cell} from adjacent position ({adj_row}, {adj_col})", "[GameClient]")
                        # Remove from grid and entity positions
                        player.grid[adj_row][adj_col] = 'g'
                        pos = (adj_row, adj_col)
                        if pos in self.entity_positions[adj_cell]:
                            self.entity_positions[adj_cell].remove(pos)
                        break  # Only collect one resource per move
        
        # Update visited positions for exploration
        self.visited_positions.add((player.row, player.col))
        self.last_direction = direction
        
        return player

    def _is_walkable(self, cell_value) -> bool:
        """Check if a cell is walkable, avoiding other players and obstacles."""
        cell_str = str(cell_value)
        
        # Walkable tiles: ground, unexplored, sword, armor, wood, cotton
        if cell_str in ['g', '-1', 's', 'a', 'w', 'c']:
            return True
            
        # Avoid other players (numbers 1-9)
        if cell_str.isdigit() and cell_str != '0':
            return False
            
        # Avoid obstacles like rocks
        if cell_str in ['r', '#']:
            return False
            
        return False

    def _is_repeating_movement(self, next_pos: tuple[int, int]) -> bool:
        """Check if the next position would create a repeating pattern or standing still."""
        if len(self.last_positions) < 1:
            return False
        
        # Get current position
        current_pos = self.last_positions[-1] if self.last_positions else None
        
        # Check if we're standing still (not moving)
        if current_pos and next_pos == current_pos:
            log("Detected standing still, avoiding stationary movement", "[GameClient]")
            return True
            
        if len(self.last_positions) < 2:
            return False
            
        # Check if we're moving back to a position we were at recently
        if next_pos in self.last_positions:
            log(f"Detected revisiting recent position {next_pos}", "[GameClient]")
            return True
            
        # Check for back-and-forth movement in the same row
        if len(self.last_positions) >= 2:
            last_pos = self.last_positions[-1]
            second_last_pos = self.last_positions[-2]
            
            # If we're in the same row and moving back and forth
            if (last_pos[0] == second_last_pos[0] and  # Same row
                next_pos[0] == last_pos[0] and  # Still in same row
                abs(next_pos[1] - last_pos[1]) == abs(last_pos[1] - second_last_pos[1])):  # Same distance
                log(f"Detected back-and-forth movement in row {last_pos[0]}", "[GameClient]")
                return True
                
        return False

    def _get_next_exploration_direction(self, player) -> int:
        """Determine the next direction for systematic exploration."""
        # First check if we need to return home to store items
        if len(self.items_on_hand) >= Config.MAX_STORAGE_CAPACITY:
            log("Inventory full, returning home to store items", "[GameClient]")
            path = shortest_path(player.grid, (player.row, player.col), (player.home_row, player.home_col))
            if path:
                return path[0]
        
        # Check for resources in adjacent cells
        resources = find_adjacent_resources(player.grid, player.row, player.col)
        if resources:
            # Prioritize resources based on our needs
            for resource_type in ['s', 'a', 'w', 'c', 'r']:  # Prioritize sword, armor, then others
                if resource_type in resources and resources[resource_type]:
                    # Get the first accessible position for this resource
                    target_pos = resources[resource_type][0]
                    # Calculate direction to move towards the resource
                    row_diff = target_pos[0] - player.row
                    col_diff = target_pos[1] - player.col
                    
                    # Determine the direction based on the largest difference
                    if abs(row_diff) > abs(col_diff):
                        return 2 if row_diff < 0 else 3  # up or down
                    else:
                        return 0 if col_diff < 0 else 1  # left or right
        
        # Systematic exploration based on current phase
        return self._get_systematic_exploration_direction(player)

    def _get_systematic_exploration_direction(self, player) -> int:
        """Get direction for systematic exploration starting from center."""
        # Calculate center of the map
        center_row = Config.N_ROW // 2
        center_col = Config.N_COL // 2
        center_pos = (center_row, center_col)
        
        current_pos = (player.row, player.col)
        
        # Check win condition first
        # Note: This would need to be passed from the workflow
        # For now, we'll assume we need to find at least one wood and one cotton
        if (self.get_storage_count('w') > 0 and self.get_storage_count('c') > 0 and
            len(self.entity_positions['w']) > 0 and len(self.entity_positions['c']) > 0):
            log("Have both wood and cotton in storage and known positions, exploration complete", "[GameClient]")
            return self._get_direction_to_resource(player)
        
        # Phase 1: Go to center first
        if not self.center_reached:
            if current_pos == center_pos:
                self.center_reached = True
                self.exploration_phase = "up"
                log("Reached center, starting systematic exploration", "[GameClient]")
            else:
                # Move towards center
                path = shortest_path(player.grid, current_pos, center_pos)
                if path:
                    return path[0]
                else:
                    # If no path to center, try to get as close as possible
                    row_diff = center_row - player.row
                    col_diff = center_col - player.col
                    if abs(row_diff) > abs(col_diff):
                        return 2 if row_diff < 0 else 3  # up or down
                    else:
                        return 0 if col_diff < 0 else 1  # left or right
        
        # Phase 2: Systematic exploration from center
        if self.center_reached:
            # Check if we have found both wood and cotton
            if len(self.entity_positions['w']) > 0 and len(self.entity_positions['c']) > 0:
                log("Found both wood and cotton, exploration complete", "[GameClient]")
                return self._get_direction_to_resource(player)
            
            # Continue systematic exploration
            return self._explore_in_pattern(player, center_pos)

    def _explore_in_pattern(self, player, center_pos) -> int:
        """Explore in a systematic pattern: up, down, left, right with increasing radius."""
        current_pos = (player.row, player.col)
        
        # Calculate distance from center
        distance_from_center = abs(player.row - center_pos[0]) + abs(player.col - center_pos[1])
        
        # If we're too far from center, return to center
        if distance_from_center > self.max_exploration_radius:
            log("Too far from center, returning to center", "[GameClient]")
            path = shortest_path(player.grid, current_pos, center_pos)
            if path:
                return path[0]
        
        # Define exploration pattern based on current phase
        if self.exploration_phase == "up":
            # Try to move up from center
            target_row = center_pos[0] - self.exploration_radius
            if target_row >= 0:
                target_pos = (target_row, center_pos[1])
                if target_pos not in self.visited_positions:
                    path = shortest_path(player.grid, current_pos, target_pos)
                    if path:
                        return path[0]
            # If can't go up, switch to next phase
            self.exploration_phase = "down"
            
        if self.exploration_phase == "down":
            # Try to move down from center
            target_row = center_pos[0] + self.exploration_radius
            if target_row < Config.N_ROW:
                target_pos = (target_row, center_pos[1])
                if target_pos not in self.visited_positions:
                    path = shortest_path(player.grid, current_pos, target_pos)
                    if path:
                        return path[0]
            # If can't go down, switch to next phase
            self.exploration_phase = "left"
            
        if self.exploration_phase == "left":
            # Try to move left from center
            target_col = center_pos[1] - self.exploration_radius
            if target_col >= 0:
                target_pos = (center_pos[0], target_col)
                if target_pos not in self.visited_positions:
                    path = shortest_path(player.grid, current_pos, target_pos)
                    if path:
                        return path[0]
            # If can't go left, switch to next phase
            self.exploration_phase = "right"
            
        if self.exploration_phase == "right":
            # Try to move right from center
            target_col = center_pos[1] + self.exploration_radius
            if target_col < Config.N_COL:
                target_pos = (center_pos[0], target_col)
                if target_pos not in self.visited_positions:
                    path = shortest_path(player.grid, current_pos, target_pos)
                    if path:
                        return path[0]
            # If can't go right, increase radius and restart pattern
            self.exploration_radius += 1
            self.exploration_phase = "up"
            log(f"Increased exploration radius to {self.exploration_radius}", "[GameClient]")
        
        # If no specific direction found, try to find any unexplored area
        return self._find_unexplored_direction(player)

    def _find_unexplored_direction(self, player) -> int:
        """Find any unexplored direction when systematic exploration fails."""
        directions = [0, 1, 2, 3]  # left, right, up, down
        
        for direction in directions:
            row_diff, col_diff = 0, 0
            if direction == 0:  # left
                col_diff = -1
            elif direction == 1:  # right
                col_diff = 1
            elif direction == 2:  # up
                row_diff = -1
            elif direction == 3:  # down
                row_diff = 1
                
            next_row = player.row + row_diff
            next_col = player.col + col_diff
            next_pos = (next_row, next_col)
            
            # Check if the next position is valid, walkable, and unexplored (avoid resources)
            if (0 <= next_row < Config.N_ROW and 
                0 <= next_col < Config.N_COL and
                self._is_walkable(player.grid[next_row][next_col]) and  # Only walkable tiles
                next_pos not in self.visited_positions):
                return direction
        
        # If no unexplored direction found, try any walkable direction (avoid resources)
        for direction in directions:
            row_diff, col_diff = 0, 0
            if direction == 0:  # left
                col_diff = -1
            elif direction == 1:  # right
                col_diff = 1
            elif direction == 2:  # up
                row_diff = -1
            elif direction == 3:  # down
                row_diff = 1
                
            next_row = player.row + row_diff
            next_col = player.col + col_diff
            
            if (0 <= next_row < Config.N_ROW and 
                0 <= next_col < Config.N_COL and
                self._is_walkable(player.grid[next_row][next_col])):  # Only walkable tiles
                return direction
        
        return 0  # Default to moving left if no other option

    def _get_direction_to_resource(self, player) -> int:
        """Get direction to the nearest needed resource."""
        # Get current storage counts from our tracking system
        stored_wood = self.get_storage_count('w')
        stored_cotton = self.get_storage_count('c')
        stored_fabric = self.get_storage_count('fa')
        
        # Calculate what's still needed based on win condition
        wood_needed = max(0, self.win_condition['wood'] - stored_wood)
        fabric_needed = max(0, self.win_condition.get('fabric', 0) - stored_fabric)
        
        # Calculate cotton needed for fabric conversion
        cotton_for_fabric = fabric_needed * self.win_condition['cotton_per_fabric']
        cotton_needed = max(0, self.win_condition.get('cotton', 0) + cotton_for_fabric - stored_cotton)
        
        # If we have enough of both resources, stay at home
        if wood_needed == 0 and cotton_needed == 0 and fabric_needed == 0:
            log("Have enough resources in storage, staying at home", "[GameClient]")
            return 0  # Stay put
        
        # Prioritize wood and cotton based on what we need
        if wood_needed > 0 and len(self.entity_positions['w']) > 0:
            wood_pos = self.entity_positions['w'][0]
            path = shortest_path(player.grid, (player.row, player.col), wood_pos)
            if path:
                log(f"Moving towards wood at {wood_pos}, still need {wood_needed}", "[GameClient]")
                return path[0]
        
        if cotton_needed > 0 and len(self.entity_positions['c']) > 0:
            cotton_pos = self.entity_positions['c'][0]
            path = shortest_path(player.grid, (player.row, player.col), cotton_pos)
            if path:
                log(f"Moving towards cotton at {cotton_pos}, still need {cotton_needed} (for fabric: {cotton_for_fabric})", "[GameClient]")
                return path[0]
        
        # If no path to resources, continue exploration
        log("No path to needed resources, continuing exploration", "[GameClient]")
        return self._find_unexplored_direction(player)

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
            self.explore()

    def go_home(self):
        log("Returning to home base", "[GameClient]")
        player = self.get_player()
        home_position = (player.home_row, player.home_col)
        log(f"Home position is at {home_position}", "[GameClient]")
        self.goto(home_position)

    def collect_wood(self):
        """Collect wood by standing adjacent to it."""
        log("Attempting to collect wood", "[GameClient]")
        player = self.get_player()
        
        # Check if already carrying wood
        if self.get_items_on_hand_count('w') > 0:
            log("Already carrying wood, returning home to store", "[GameClient]")
            self.go_home()
            return
            
        # Check if inventory is full
        if len(self.items_on_hand) >= 4:
            log("Inventory full, returning home", "[GameClient]")
            self.go_home()
            return
            
        # First check visible area for wood
        visible_range = 5
        for i in range(max(0, player.row - visible_range), min(len(player.grid), player.row + visible_range + 1)):
            for j in range(max(0, player.col - visible_range), min(len(player.grid[0]), player.col + visible_range + 1)):
                if player.grid[i][j] == 'w':
                    pos = (i, j)
                    if pos not in self.entity_positions['w']:
                        self.entity_positions['w'].append(pos)
                        log(f"Added new wood at {pos} to known positions", "[GameClient]")
        
        if len(self.entity_positions['w']) > 0:
            wood_position = self.entity_positions['w'][0]
            # Move towards the wood (automatic collection will happen when adjacent)
            log(f"Moving towards wood at {wood_position}", "[GameClient]")
            self.goto(wood_position)
        else:
            log("No wood positions known, need to explore more", "[GameClient]")
    
    def collect_cotton(self):
        """Collect cotton by standing adjacent to it."""
        log("Attempting to collect cotton", "[GameClient]")
        player = self.get_player()
        
        # Check if already carrying cotton
        if self.get_items_on_hand_count('c') > 0:
            log("Already carrying cotton, returning home to store", "[GameClient]")
            self.go_home()
            return
            
        # Check if inventory is full
        if len(self.items_on_hand) >= 4:
            log("Inventory full, returning home", "[GameClient]")
            self.go_home()
            return
            
        # First check visible area for cotton
        visible_range = 5
        for i in range(max(0, player.row - visible_range), min(len(player.grid), player.row + visible_range + 1)):
            for j in range(max(0, player.col - visible_range), min(len(player.grid[0]), player.col + visible_range + 1)):
                if player.grid[i][j] == 'c':
                    pos = (i, j)
                    if pos not in self.entity_positions['c']:
                        self.entity_positions['c'].append(pos)
                        log(f"Added new cotton at {pos} to known positions", "[GameClient]")
        
        if len(self.entity_positions['c']) > 0:
            cotton_position = self.entity_positions['c'][0]
            # Move towards the cotton (automatic collection will happen when adjacent)
            log(f"Moving towards cotton at {cotton_position}", "[GameClient]")
            self.goto(cotton_position)
        else:
            log("No cotton positions known, need to explore more", "[GameClient]")
    
    def collect_sword(self):
        """Collect sword by standing on it. Only one sword at a time."""
        log("Attempting to collect sword", "[GameClient]")
        player = self.get_player()
        
        # Check if already wearing sword
        if self.is_wearing('s'):
            log("Already equipped with sword", "[GameClient]")
            return
            
        if len(self.entity_positions['s']) > 0:
            sword_position = self.entity_positions['s'][0]
            # Move to the sword position (automatic collection will happen when standing on it)
            log(f"Moving to sword at {sword_position}", "[GameClient]")
            self.goto(sword_position)
        else:
            log("No sword positions known", "[GameClient]")

    def collect_armor(self):
        """Collect armor by standing on it. Only one armor at a time."""
        log("Attempting to collect armor", "[GameClient]")
        player = self.get_player()
        
        # Check if already wearing armor
        if self.is_wearing('a'):
            log("Already equipped with armor", "[GameClient]")
            return
            
        if len(self.entity_positions['a']) > 0:
            armor_position = self.entity_positions['a'][0]
            # Move to the armor position (automatic collection will happen when standing on it)
            log(f"Moving to armor at {armor_position}", "[GameClient]")
            self.goto(armor_position)
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
        """Explore the map, prioritizing unexplored areas and moving towards the center."""
        log("Starting exploration", "[GameClient]")
        player = self.get_player()
        current_position = (player.row, player.col)
        log(f"Current position: {current_position}", "[GameClient]")
        
        # Update entity positions from surrounding resources
        log("Scanning surroundings for resources", "[GameClient]")
        visible_range = 5
        for i in range(max(0, player.row - visible_range), min(len(player.grid), player.row + visible_range + 1)):
            for j in range(max(0, player.col - visible_range), min(len(player.grid[0]), player.col + visible_range + 1)):
                cell = str(player.grid[i][j])
                if cell in ['w', 'c', 's', 'a']:  # Found a resource
                    pos = (i, j)
                    if pos not in self.entity_positions[cell]:
                        self.entity_positions[cell].append(pos)
                        log(f"Added new {cell} resource at {pos} to known positions", "[GameClient]")
        
        # Get next exploration direction
        next_direction = self._get_next_exploration_direction(player)
        
        if next_direction is not None:
            # Check if the direction is blocked
            row_diff, col_diff = 0, 0
            if next_direction == 0:  # left
                col_diff = -1
            elif next_direction == 1:  # right
                col_diff = 1
            elif next_direction == 2:  # up
                row_diff = -1
            elif next_direction == 3:  # down
                row_diff = 1
                
            next_row = player.row + row_diff
            next_col = player.col + col_diff
            
            # Check if the next position is valid and walkable (avoid resources)
            if (0 <= next_row < len(player.grid) and 
                0 <= next_col < len(player.grid[0]) and
                self._is_walkable(player.grid[next_row][next_col])):  # Only walkable tiles
                direction_names = ["left", "right", "up", "down"]
                log(f"Moving {direction_names[next_direction]} for exploration", "[GameClient]")
                self.move(next_direction)
                self.last_direction = next_direction
            else:
                # Direction is blocked by resource or obstacle, find alternative
                log(f"Direction {next_direction} is blocked by resource/obstacle, finding alternative", "[GameClient]")
                self._find_alternative_direction(player)
        else:
            log("No valid exploration direction found, finding alternative", "[GameClient]")
            self._find_alternative_direction(player)

    def _find_alternative_direction(self, player):
        """Find an alternative direction when the primary direction is blocked."""
        # Calculate center of the map
        center_row = Config.N_ROW // 2
        center_col = Config.N_COL // 2
        
        # Get current position
        current_row, current_col = player.row, player.col
        
        # Calculate direction towards center
        row_diff = center_row - current_row
        col_diff = center_col - current_col
        
        # Prioritize directions that lead to unexplored areas and towards center
        directions = []
        if abs(row_diff) > abs(col_diff):
            # Prioritize vertical movement
            directions = [2 if row_diff < 0 else 3, 0, 1]  # up/down, then left/right
        else:
            # Prioritize horizontal movement
            directions = [0 if col_diff < 0 else 1, 2, 3]  # left/right, then up/down
        
        # Try each direction in order of priority
        for direction in directions:
            row_diff, col_diff = 0, 0
            if direction == 0:  # left
                col_diff = -1
            elif direction == 1:  # right
                col_diff = 1
            elif direction == 2:  # up
                row_diff = -1
            elif direction == 3:  # down
                row_diff = 1
                
            next_row = player.row + row_diff
            next_col = player.col + col_diff
            next_pos = (next_row, next_col)
            
            # Skip if this would create a repeating pattern
            if self._is_repeating_movement(next_pos):
                continue
            
            # Check if the next position is valid and walkable (avoid resources)
            if (0 <= next_row < Config.N_ROW and 
                0 <= next_col < Config.N_COL and
                self._is_walkable(player.grid[next_row][next_col])):  # Only walkable tiles
                direction_names = ["left", "right", "up", "down"]
                log(f"Moving {direction_names[direction]} as alternative direction", "[GameClient]")
                self.move(direction)
                self.last_direction = direction
                return
        
        # If no clear direction found, try to find any unexplored area
        log("No clear directions found, searching for unexplored areas", "[GameClient]")
        from pathfinding import shortest_path_to_value
        path, target = shortest_path_to_value(player.grid, (player.row, player.col), '-1')
        if path is not None and len(path) > 0:
            direction = path[0]
            next_row = player.row + [-1, 0, 1, 0][direction]
            next_col = player.col + [0, 1, 0, -1][direction]
            next_pos = (next_row, next_col)
            
            # Only move if it won't create a repeating pattern and is walkable
            if (not self._is_repeating_movement(next_pos) and
                0 <= next_row < Config.N_ROW and 
                0 <= next_col < Config.N_COL and
                self._is_walkable(player.grid[next_row][next_col])):
                direction_names = ["left", "right", "up", "down"]
                log(f"Moving {direction_names[direction]} towards unexplored area", "[GameClient]")
                self.move(direction)
                self.last_direction = direction
            else:
                log("Avoiding repeating movement pattern or blocked path", "[GameClient]")
                # Reset visited positions to allow revisiting
                self.visited_positions.clear()
        else:
            log("No unexplored areas found nearby", "[GameClient]")
            # Reset visited positions to allow revisiting
            self.visited_positions.clear()

    def check_win_condition(self, wood_needed: int, cotton_needed: int) -> bool:
        """Check if we have met the win condition based on stored resources."""
        stored_wood = self.get_storage_count('w')
        stored_cotton = self.get_storage_count('c')
        
        log(f"Win condition check: need {wood_needed} wood, {cotton_needed} cotton", "[GameClient]")
        log(f"Current storage: {stored_wood} wood, {stored_cotton} cotton", "[GameClient]")
        
        if stored_wood >= wood_needed and stored_cotton >= cotton_needed:
            log("Win condition met!", "[GameClient]")
            return True
        else:
            log("Win condition not yet met", "[GameClient]")
            return False 