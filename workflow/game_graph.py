from dataclasses import dataclass
import time
import random
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from game_client import GameClient
from models.tasks import WinCondition, Position
from models.context import FindContext

@dataclass
class GameState:  
    """State maintained throughout the game workflow"""
    client: GameClient
    name: str
    wood_need: int = 0
    cotton_need: int = 0
    # Track unexplored frontier cells for map discovery
    frontier: list = None
    visited: set = None

    def __post_init__(self):
        self.frontier = []
        self.visited = set()

@dataclass
class CreateGame(BaseNode[GameState]):  
    """Initial node in the workflow"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'TakeMission':
        return TakeMission()

@dataclass
class TakeMission(BaseNode[GameState]):
    """Parse the mission and identify resource requirements"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'WaitingStartGame':
        # Store mission to context
        client = ctx.state.client 
        
        player = client.get_player()
        while not player.message:
            time.sleep(1)
            player = client.get_player()

        client.messages.append(player.message)

        result = client.orchestrator_agent.agent.run_sync(
            "Parse this message to get the resource need: " + player.message,
            deps = WinCondition(
                wood_need=0,
                cotton_need=0,
                player=player
            )
        )

        print(result.output)

        ctx.state.wood_need = result.output.wood_need
        ctx.state.cotton_need = result.output.cotton_need

        print(f'{ctx.state=}')

        return WaitingStartGame()

@dataclass
class WaitingStartGame(BaseNode[GameState]):
    """Wait for the game to start"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'IdentifyTask | End':
        msg = 'Waiting start game'
        client = ctx.state.client 
        
        # Example implementation - wait for game to start
        # In a real implementation, this would check player status
        time.sleep(5)
        
        return IdentifyTask()

@dataclass
class IdentifyTask(BaseNode[GameState]):
    """Determine the next task to perform"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'ExecuteTask | End':
        client = ctx.state.client
        player = client.get_player()
        
        # Check if the game is over
        if player.status == "game_over":
            return End()
            
        # Decide the next task
        result = client.orchestrator_agent.agent.run_sync(
            "What should I do next?",
            deps=WinCondition(
                wood_need=ctx.state.wood_need,
                cotton_need=ctx.state.cotton_need,
                player=player
            )
        )
        
        client.task = result.output
        
        return ExecuteTask()

@dataclass
class ExecuteTask(BaseNode[GameState]):
    """Execute the identified task"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'IdentifyTask | End':
        client = ctx.state.client
        task = client.task
        
        # Go home if requested
        if hasattr(task, "task_description") and "go home" in task.task_description.lower():
            client.go_home()
            
        # Map discovery logic - frontier-based exploration
        elif hasattr(task, "task_description") and "discover" in task.task_description.lower():
            await self.discover_map(ctx)
            
        # Resource collection logic
        elif any(resource_type in task.task_description.lower() for resource_type in ["wood", "cotton", "food"]):
            await self.collect_resource(ctx, task)
            
        # After task execution, return to task identification
        return IdentifyTask()
    
    async def collect_resource(self, ctx: GraphRunContext[GameState], task) -> None:
        """
        Resource collection algorithm
        
        This function:
        1. Determines which resource to collect based on the task
        2. Finds the nearest resource of that type
        3. Navigates to and collects the resource
        """
        client = ctx.state.client
        player = client.get_player()
        
        # Determine resource type from task
        resource_type = None
        if "wood" in task.task_description.lower():
            resource_type = 'w'
            result = client.play_game_agent.agent.run_sync(
                "find wood",
                deps=FindContext(player=player)
            )
        elif "cotton" in task.task_description.lower():
            resource_type = 'c'
            result = client.play_game_agent.agent.run_sync(
                "find cotton",
                deps=FindContext(player=player)
            )
        elif "food" in task.task_description.lower():
            resource_type = 'f'
            result = client.play_game_agent.agent.run_sync(
                "find food",
                deps=FindContext(player=player)
            )
        else:
            # Unknown resource type, default to discovery
            await self.discover_map(ctx)
            return
        
        # Allow collection of the resource type
        if resource_type and resource_type not in player.allow_collect_items:
            client.allow_collect_items(items=[resource_type])
        
        # If we found resource positions
        if hasattr(result.output, "positions") and result.output.positions:
            positions = result.output.positions
            
            # Get the nearest resource position
            current_row, current_col = player.row, player.col
            nearest_position = min(
                positions, 
                key=lambda pos: abs(pos.row - current_row) + abs(pos.col - current_col)
            )
            
            # Find path to the resource
            path = client.find_shortest_path_to(nearest_position.row, nearest_position.col)
            
            if path:
                # If we're adjacent to the resource, collect it
                if len(path) == 1:
                    # Move to the resource and collect it
                    client.move(path[0])
                    # Collection happens automatically when stepping on the resource
                    # if we've allowed collection of this resource type
                elif len(path) > 1:
                    # Move one step toward the resource
                    client.move(path[0])
            else:
                # No path found, explore instead
                await self.discover_map(ctx)
        else:
            # No resources found, explore
            await self.discover_map(ctx)
    
    async def discover_map(self, ctx: GraphRunContext[GameState]) -> None:
        """
        Frontier-based exploration algorithm for map discovery
        
        This algorithm:
        1. Identifies unexplored (-1) cells at the frontier of explored territory
        2. Chooses the closest unexplored cell to move to
        3. Updates the frontier as new areas are explored
        
        This is an efficient exploration algorithm that prioritizes expanding
        the known map area.
        """
        client = ctx.state.client
        player = client.get_player()
        
        # Get player's current position
        current_row, current_col = player.row, player.col
        
        # Update visited cells
        ctx.state.visited.add((current_row, current_col))
        
        # Moves: (dr, dc, move_code)
        moves = [
            (0, -1, 0),  # left
            (0, 1, 1),   # right
            (-1, 0, 2),  # up
            (1, 0, 3),   # down
        ]
        
        # Function to get unexplored adjacent cells
        def get_unexplored_neighbors(row, col, grid):
            unexplored = []
            for dr, dc, move_code in moves:
                new_row, new_col = row + dr, col + dc
                
                # Check if in bounds
                if 0 <= new_row < grid.shape[0] and 0 <= new_col < grid.shape[1]:
                    # Check if it's unexplored (-1) or ground ('g')
                    cell_value = grid[new_row, new_col]
                    if cell_value == '-1' and (new_row, new_col) not in ctx.state.visited:
                        unexplored.append((new_row, new_col, move_code))
            return unexplored
        
        # Update frontier with new unexplored cells
        new_frontier_cells = get_unexplored_neighbors(current_row, current_col, player.grid)
        for cell in new_frontier_cells:
            if cell[:2] not in [f[:2] for f in ctx.state.frontier]:
                ctx.state.frontier.append(cell)
        
        # Remove current position from frontier if it was there
        ctx.state.frontier = [cell for cell in ctx.state.frontier if cell[:2] != (current_row, current_col)]
        
        # If frontier is empty, find any unexplored cells on the map
        if not ctx.state.frontier:
            print("Finding new frontier cells from entire map...")
            # Use PlayGameAgent to find unexplored cells
            result = client.play_game_agent.agent.run_sync(
                "Find unexplored cells",
                deps=FindContext(player=player)
            )
            
            # If we found map exploration positions
            if hasattr(result.output, "positions") and result.output.positions:
                # Choose a random unexplored cell to move towards
                target_pos = random.choice(result.output.positions)
                path = client.find_shortest_path_to(target_pos.row, target_pos.col)
                if path:
                    # Move one step towards target
                    client.move(path[0])
                    return
            
            # If we didn't find a path, move randomly
            client.move(random.randint(0, 3))
            return
            
        # Choose closest frontier cell (using Manhattan distance)
        closest_cell = min(
            ctx.state.frontier,
            key=lambda cell: abs(cell[0] - current_row) + abs(cell[1] - current_col)
        )
        
        # Find path to closest frontier cell
        target_row, target_col, _ = closest_cell
        path = client.find_shortest_path_to(target_row, target_col)
        
        # Move one step towards target
        if path:
            client.move(path[0])
        else:
            # If no path found, remove this cell from frontier and try again next time
            ctx.state.frontier.remove(closest_cell)
            # Make a random move as fallback
            client.move(random.randint(0, 3)) 