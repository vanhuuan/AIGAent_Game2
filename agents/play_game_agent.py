from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from config import Config
from models.context import FindContext
from models.tasks import (
    FoodPositions, WoodPositions, CottonPositions, MapExplorer, Path, Position
)
import numpy as np
from utils import find_resource
import heapq

@dataclass
class PlayGameAgent:
    """
    Agent that handles resource identification and pathfinding
    """
    
    prompting_for_finding_resource = """
    You are tasked with locating resources on the map defined in World Representation.
    Return a list of all cells that contain a resource food, wood, or cotton where each is denoted by:

    'f' for food

    'w' for wood

    'c' for cotton

    '-1' for discover map

    if No wood resources found you should return MapExlorer
    """
    
    config = Config()
    agent = Agent(
        f'openai:{config.LLM_MODEL}',
        output_type=FoodPositions | WoodPositions | CottonPositions | MapExplorer | Path,
        system_prompt=prompting_for_finding_resource,
        deps_type=FindContext
    ) 

    @agent.tool
    def map_expolorer(ctx: RunContext[FindContext]) -> list:
        """Find -1 cells"""
        row = ctx.deps.player.row
        col = ctx.deps.player.col
        
        return find_resource(ctx.deps.player.grid[row-1: row+1, col-1:col+1], -1)
        
    @agent.tool
    def find_food(ctx: RunContext[FindContext]) -> list:
        """Find food cells"""
        return find_resource(ctx.deps.player.grid, 'f')
        
    @agent.tool
    def find_wood(ctx: RunContext[FindContext]) -> list:
        """Find wood cells"""
        return find_resource(ctx.deps.player.grid, 'w')
    
    @agent.tool
    def find_cotton(ctx: RunContext[FindContext]) -> list:
        """Find cotton cells"""
        return find_resource(ctx.deps.player.grid, 'c')
        
    @agent.tool
    def find_shortest_path(ctx: RunContext[FindContext], resource_positions: list[Position]) -> list:
        """
        Find shortest path using A* algorithm
        
        Args:
            ctx: The context containing player and map information
            resource_positions: List of positions to find paths to
            
        Returns:
            List of movement directions to the closest resource
        """
        # If no resources found, return None
        if len(resource_positions) == 0:
            return None
            
        # Define moves: (dr, dc, move_code)
        moves = [
            (0, -1, 0),  # left
            (0, 1, 1),   # right
            (-1, 0, 2),  # up
            (1, 0, 3),   # down
        ]
        
        # Player's current position
        start_row, start_col = ctx.deps.player.row, ctx.deps.player.col
        grid = ctx.deps.player.grid
        h, w = grid.shape
        
        # Function to check if a position is valid for movement
        def is_valid(r, c):
            return 0 <= r < h and 0 <= c < w and grid[r, c] in ('g', '-1', 'f', 'w', 'c')
        
        # Find paths to all resource positions and return the shortest one
        best_path = None
        shortest_distance = float('inf')
        
        for pos in resource_positions:
            end_row, end_col = pos.row, pos.col
            
            # A* algorithm
            # f(n) = g(n) + h(n) where:
            # - g(n) is the cost from start to current node
            # - h(n) is the heuristic (Manhattan distance in this case)
            
            # Priority queue for A* (f_score, g_score, row, col, path)
            open_set = []
            # Start node with f_score = h(start)
            h_score = abs(start_row - end_row) + abs(start_col - end_col)
            heapq.heappush(open_set, (h_score, 0, start_row, start_col, []))
            
            # Track visited nodes to avoid cycles
            visited = set([(start_row, start_col)])
            
            while open_set:
                # Get node with lowest f_score
                _, g_score, row, col, path = heapq.heappop(open_set)
                
                # If reached destination
                if row == end_row and col == end_col:
                    if len(path) < shortest_distance:
                        shortest_distance = len(path)
                        best_path = path
                    break
                
                # Try all four directions
                for dr, dc, move_code in moves:
                    new_row, new_col = row + dr, col + dc
                    
                    if is_valid(new_row, new_col) and (new_row, new_col) not in visited:
                        visited.add((new_row, new_col))
                        new_path = path + [move_code]
                        
                        # Calculate scores
                        new_g = g_score + 1  # Cost is 1 per step
                        new_h = abs(new_row - end_row) + abs(new_col - end_col)
                        new_f = new_g + new_h
                        
                        heapq.heappush(open_set, (new_f, new_g, new_row, new_col, new_path))
        
        return best_path 