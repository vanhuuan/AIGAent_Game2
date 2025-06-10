from dataclasses import dataclass
import time
import random
import logging
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
        self.logger = logging.getLogger("agent_logger")

@dataclass
class CreateGame(BaseNode[GameState]):  
    """Initial node in the workflow"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'TakeMission':
        ctx.state.logger.info("Workflow: CreateGame -> TakeMission")
        return TakeMission()

@dataclass
class TakeMission(BaseNode[GameState]):
    """Parse the mission and identify resource requirements"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'WaitingStartGame':
        ctx.state.logger.info("Workflow: TakeMission - Parsing mission requirements")
        # Store mission to context
        client = ctx.state.client 
        
        player = client.get_player()
        while not player.message:
            time.sleep(1)
            player = client.get_player()

        client.messages.append(player.message)
        ctx.state.logger.info(f"Mission message: {player.message}")

        result = client.orchestrator_agent.agent.run_sync(
            "Parse this message to get the resource need: " + player.message,
            deps = WinCondition(
                wood_need=0,
                cotton_need=0,
                player=player
            )
        )

        print(result.output)
        ctx.state.logger.info(f"Parsed resource needs: Wood={result.output.wood_need}, Cotton={result.output.cotton_need}")

        ctx.state.wood_need = result.output.wood_need
        ctx.state.cotton_need = result.output.cotton_need

        print(f'{ctx.state=}')
        ctx.state.logger.info("Workflow: TakeMission -> WaitingStartGame")
        return WaitingStartGame()

@dataclass
class WaitingStartGame(BaseNode[GameState]):
    """Wait for the game to start"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'IdentifyTask | End':
        client = ctx.state.client
        ctx.state.logger.info("Workflow: WaitingStartGame - Waiting for game to start")
        print("Waiting for game to start...")
        
        # Poll the player status until it changes from WAITING_FOR_PLAYERS to PLAYING
        while True:
            player = client.get_player()
            
            # Check if the game has started
            if player.status == "playing":
                print("Game has started!")
                ctx.state.logger.info("Game has started! Workflow: WaitingStartGame -> IdentifyTask")
                return IdentifyTask()
            
            # Check if the game was canceled or ended unexpectedly
            if player.status in ["win", "loss", "dead", "game_over"]:
                print(f"Game ended with status: {player.status}")
                ctx.state.logger.info(f"Game ended with status: {player.status}. Workflow: WaitingStartGame -> End")
                return End()
                
            # Wait a short time before checking again
            time.sleep(1)

@dataclass
class IdentifyTask(BaseNode[GameState]):
    """Determine the next task to perform"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'ExecuteTask | End':
        ctx.state.logger.info("Workflow: IdentifyTask - Determining next task")
        client = ctx.state.client
        player = client.get_player()
        
        # Check if the game is over
        if player.status == "game_over":
            ctx.state.logger.info("Game is over. Workflow: IdentifyTask -> End")
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
        ctx.state.logger.info(f"Identified task: {client.task.task_description if hasattr(client.task, 'task_description') else client.task}")
        ctx.state.logger.info("Workflow: IdentifyTask -> ExecuteTask")
        
        return ExecuteTask()

@dataclass
class ExecuteTask(BaseNode[GameState]):
    """Execute the identified task"""
    async def run(self, ctx: GraphRunContext[GameState]) -> 'IdentifyTask | End':
        ctx.state.logger.info("Workflow: ExecuteTask - Executing task")
        client = ctx.state.client
        task = client.task
        
        # Go home if requested
        if hasattr(task, "task_description") and "go home" in task.task_description.lower():
            ctx.state.logger.info("Executing task: Go home")
            client.go_home()
            
        # Map discovery logic - frontier-based exploration
        elif hasattr(task, "task_description") and "discover" in task.task_description.lower():
            ctx.state.logger.info("Executing task: Discover map")
            await self.discover_map(ctx)
            
        # Resource collection logic
        elif any(resource_type in task.task_description.lower() for resource_type in ["wood", "cotton", "food"]):
            resource_type = "unknown"
            if "wood" in task.task_description.lower():
                resource_type = "wood"
            elif "cotton" in task.task_description.lower():
                resource_type = "cotton"
            elif "food" in task.task_description.lower():
                resource_type = "food"
                
            ctx.state.logger.info(f"Executing task: Collect {resource_type}")
            await self.collect_resource(ctx, task)
            
        # After task execution, return to task identification
        ctx.state.logger.info("Task execution complete. Workflow: ExecuteTask -> IdentifyTask")
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
            ctx.state.logger.info("Searching for wood resources")
            result = client.play_game_agent.agent.run_sync(
                "find wood",
                deps=FindContext(player=player)
            )
        elif "cotton" in task.task_description.lower():
            resource_type = 'c'
            ctx.state.logger.info("Searching for cotton resources")
            result = client.play_game_agent.agent.run_sync(
                "find cotton",
                deps=FindContext(player=player)
            )
        elif "food" in task.task_description.lower():
            resource_type = 'f'
            ctx.state.logger.info("Searching for food resources")
            result = client.play_game_agent.agent.run_sync(
                "find food",
                deps=FindContext(player=player)
            )
        else:
            # Unknown resource type, default to discovery
            ctx.state.logger.info("Unknown resource type, defaulting to map discovery")
            await self.discover_map(ctx)
            return
        
        # Allow collection of the resource type
        if resource_type and resource_type not in player.allow_collect_items:
            ctx.state.logger.info(f"Enabling collection of resource type: {resource_type}")
            client.allow_collect_items(items=[resource_type])
        
        # If we found resource positions
        if hasattr(result.output, "positions") and result.output.positions:
            positions = result.output.positions
            ctx.state.logger.info(f"Found {len(positions)} resource positions")
            
            # Get the nearest resource position
            current_row, current_col = player.row, player.col
            nearest_position = min(
                positions, 
                key=lambda pos: abs(pos.row - current_row) + abs(pos.col - current_col)
            )
            
            ctx.state.logger.info(f"Nearest resource at position: ({nearest_position.row}, {nearest_position.col})")
            
            # Find path to the resource
            path = client.find_shortest_path_to(nearest_position.row, nearest_position.col)
            
            if path:
                # If we're adjacent to the resource, collect it
                if len(path) == 1:
                    # Move to the resource and collect it
                    ctx.state.logger.info("Moving to collect resource")
                    client.move(path[0])
                    # Collection happens automatically when stepping on the resource
                    # if we've allowed collection of this resource type
                elif len(path) > 1:
                    # Move one step toward the resource
                    ctx.state.logger.info("Moving one step toward resource")
                    client.move(path[0])
            else:
                # No path found, explore instead
                ctx.state.logger.info("No path to resource found, exploring instead")
                await self.discover_map(ctx)
        else:
            # No resources found, explore
            ctx.state.logger.info("No resources found, exploring instead")
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
        ctx.state.logger.info("Executing map discovery algorithm")
        
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
            ctx.state.frontier.append(cell)
        
        ctx.state.logger.info(f"Added {len(new_frontier_cells)} new cells to frontier")
        
        # Remove current position from frontier if it was there
        ctx.state.frontier = [cell for cell in ctx.state.frontier if cell[:2] != (current_row, current_col)]
        
        # If frontier is empty, find any unexplored cells on the map
        if not ctx.state.frontier:
            ctx.state.logger.info("Frontier is empty, finding new unexplored cells")
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
                ctx.state.logger.info(f"Found unexplored cells, targeting: ({target_pos.row}, {target_pos.col})")
                path = client.find_shortest_path_to(target_pos.row, target_pos.col)
                if path:
                    # Move one step towards target
                    ctx.state.logger.info("Moving one step toward unexplored area")
                    client.move(path[0])
                    return
            
            # If we didn't find a path, move randomly
            ctx.state.logger.info("No path to unexplored cells found, moving randomly")
            random_direction = random.randint(0, 3)
            client.move(random_direction)
            return
            
        # Choose closest frontier cell (using Manhattan distance)
        closest_cell = min(
            ctx.state.frontier,
            key=lambda cell: abs(cell[0] - current_row) + abs(cell[1] - current_col)
        )
        
        # Find path to closest frontier cell
        target_row, target_col, _ = closest_cell
        ctx.state.logger.info(f"Targeting closest frontier cell at: ({target_row}, {target_col})")
        path = client.find_shortest_path_to(target_row, target_col)
        
        # Move one step towards target
        if path:
            ctx.state.logger.info("Moving one step toward frontier cell")
            client.move(path[0])
        else:
            # If no path found, remove this cell from frontier and try again next time
            ctx.state.logger.info("No path to frontier cell found, removing from frontier")
            ctx.state.frontier.remove(closest_cell)
            # Make a random move as fallback
            ctx.state.logger.info("Making random move as fallback")
            client.move(random.randint(0, 3)) 