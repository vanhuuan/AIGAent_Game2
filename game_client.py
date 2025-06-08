import time
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
        
    def print_usage(self):
        """Print token usage information"""
        print("Prompt tokens:", self.usage.request_tokens)
        print("Response tokens:", self.usage.response_tokens)
        print("Total tokens:", self.usage.total_tokens)

    def find_shortest_path_to(self, row, col):
        """Find the shortest path to a specific location"""
        player = self.get_player()
        path = shortest_path(
            (self.player.row, self.player.col),
            (row, col),
            self.player.grid
        )
        return path
    
    def go_step_by_step(self, path: list[int]):
        """Move along a path one step at a time"""
        for direction in path:
            self.move(direction)
            time.sleep(1)
        
    def go_home(self):
        """Navigate back to the home base"""
        player = self.get_player()
        home_path = self.find_shortest_path_to(
            self.player.home_row, 
            self.player.home_col
        )
        self.go_step_by_step(home_path) 