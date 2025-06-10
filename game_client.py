import time
import logging
from client import Client
from pydantic_ai.usage import Usage
from config import Config
from agents.orchestrator_agent import OrchestratorAgent
from agents.play_game_agent import PlayGameAgent
from utils import shortest_path

class GameClient(Client):
    """
    Extended Client implementation with AI agent capabilities
    """
    
    def __init__(self):
        super().__init__()

        self.task: str = ''
        self.messages: list[str] = []
        self.usage = Usage()
        self.orchestrator_agent = OrchestratorAgent()
        self.play_game_agent = PlayGameAgent()
        self.logger = logging.getLogger("agent_logger")
        
    def print_usage(self):
        """Print token usage information"""
        print("Prompt tokens:", self.usage.request_tokens)
        print("Response tokens:", self.usage.response_tokens)
        print("Total tokens:", self.usage.total_tokens)
        
        # Log token usage
        self.logger.info(f"Token Usage - Prompt: {self.usage.request_tokens}, Response: {self.usage.response_tokens}, Total: {self.usage.total_tokens}")

    def find_shortest_path_to(self, row, col):
        """Find the shortest path to a specific location"""
        player = self.get_player()
        path = shortest_path(
            (self.player.row, self.player.col),
            (row, col),
            self.player.grid
        )
        self.logger.info(f"Path finding - From: ({self.player.row}, {self.player.col}) To: ({row}, {col}) - Path length: {len(path)}")
        return path
    
    def go_step_by_step(self, path: list[int]):
        """Move along a path one step at a time"""
        self.logger.info(f"Following path of {len(path)} steps")
        for direction in path:
            self.move(direction)
            time.sleep(1)
        
    def go_home(self):
        """Navigate back to the home base"""
        player = self.get_player()
        self.logger.info(f"Going home - Current position: ({self.player.row}, {self.player.col}), Home: ({self.player.home_row}, {self.player.home_col})")
        home_path = self.find_shortest_path_to(
            self.player.home_row, 
            self.player.home_col
        )
        self.go_step_by_step(home_path)
        
    def move(self, direction):
        """Override move method to add logging"""
        directions = {0: "left", 1: "right", 2: "up", 3: "down"}
        direction_name = directions.get(direction, str(direction))
        
        # Get player state before move
        player_before = self.get_player()
        pos_before = (player_before.row, player_before.col)
        inventory_before = {
            'wood': player_before.store.count('w'),
            'food': player_before.store.count('f'),
            'cotton': player_before.store.count('c')
        }
        
        # Perform the move
        result = super().move(direction)
        
        # Get player state after move
        player_after = self.get_player()
        pos_after = (player_after.row, player_after.col)
        inventory_after = {
            'wood': player_after.store.count('w'),
            'food': player_after.store.count('f'),
            'cotton': player_after.store.count('c')
        }
        
        # Log the move
        self.logger.info(f"Move: {direction_name} - Position: {pos_before} -> {pos_after}")
        
        # Check if resources were collected
        for resource, count_before in inventory_before.items():
            count_after = inventory_after[resource]
            if count_after > count_before:
                self.logger.info(f"Collected {resource}: +{count_after - count_before} (Total: {count_after})")
        
        return result
        
    def allow_collect_items(self, items=None):
        """Override allow_collect_items to add logging"""
        self.logger.info(f"Setting collectible items: {items}")
        return super().allow_collect_items(items) 