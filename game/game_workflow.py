from dataclasses import dataclass
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from game.game_state import GameState, ObservationResult
from game.game_client import GameClient
from agents.win_condition_agent import CalculateWinConditionAgent
from agents.event_handler_agent import EventHandlerAgent, EventTask
from enums import PlayerStatus
from logs import log
import time
import json
import os
import sys
import openai
from enum import Enum

# Add the root directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from promptings import SYSTEM_PROMPTING
from config import Config

@dataclass
class CreateGame(BaseNode[GameState]):  
    async def run(self, ctx: GraphRunContext[GameState]) -> 'TakeMission':
        log("Starting game creation process", "[Workflow]")
        # Create a new game client
        ctx.state.client = GameClient(ctx.state.name)
        log(f"Game client created for player: {ctx.state.name}", "[Workflow]")
        
        # Initialize the event handler agent
        ctx.state.event_handler_agent = EventHandlerAgent()
        log("Event handler agent initialized", "[Workflow]")
        
        ctx.state.states.append("CreateGame")
        log("Game creation complete, moving to mission phase", "[Workflow]")
        return TakeMission()

@dataclass
class TakeMission(BaseNode[GameState]):
    async def run(self, ctx: GraphRunContext[GameState]) -> 'WaitingStartGame':
        log("Starting mission acquisition phase", "[Workflow]")
        ctx.state.states.append("TakeMission")

        # Store mission to context
        client = ctx.state.client 

        log("Waiting for WinConditionEvent from server", "[Workflow]")
        player = client.get_player()
        while not player.message or "To complete this game" not in player.message:
            time.sleep(1)
            player = client.get_player()
            log("Waiting for win condition message...", "[Workflow]")

        log(f"Received win condition message: {player.message}", "[Workflow]")

        log("Analyzing mission to determine win conditions", "[Workflow]")
        result = ctx.state.calculate_win_condition_agent.calculate(player.message)

        log(f"Win conditions determined: {result}", "[Workflow]")

        ctx.state.wood_need = result.wood_need
        ctx.state.cotton_need = result.cotton_need
        ctx.state.fabric_to_cotton_ratio = result.fabric_to_cotton_ratio

        # Set win condition on the client
        client.set_win_condition(
            wood=result.wood_need,
            fabric=result.cotton_need // result.fabric_to_cotton_ratio,  # Convert cotton need to fabric need
            cotton_per_fabric=result.fabric_to_cotton_ratio
        )

        log(f"Mission requirements: {result.wood_need} wood, {result.cotton_need} cotton, fabric ratio: {result.fabric_to_cotton_ratio}", "[Workflow]")
        log("Mission acquisition complete, waiting for game to start", "[Workflow]")

        return WaitingStartGame()

@dataclass
class WaitingStartGame(BaseNode[GameState]):
    async def run(self, ctx: GraphRunContext[GameState]) -> 'Action':
        log("Waiting for game to start", "[Workflow]")
        ctx.state.states.append("WaitingStartGame")

        msg = 'Waiting start game'
        print(msg, end='')
        client = ctx.state.client 
        while True:
            player = client.get_player()
            print('.', end='')
            if player.status.value == 'playing':
                break
            time.sleep(1)

        log('Game started. Beginning gameplay', "[Workflow]")

        log("Setting up resource collection permissions", "[Workflow]")
        client.allow_collect_items(items=['w', 'c'])

        log("Starting initial exploration", "[Workflow]")
        return Action(observation_result=ObservationResult.EXPLORE)

@dataclass
class Action(BaseNode[GameState]):
    observation_result: ObservationResult = ObservationResult.EXPLORE
    async def run(self, ctx: GraphRunContext[GameState]) -> 'Observation | End':
        log(f"Executing action: {self.observation_result}", "[Workflow]")
        time.sleep(1)

        ctx.state.states.append(self.observation_result)
        client = ctx.state.client

        # Handle different actions based on observation result
        if self.observation_result == ObservationResult.GET_MORE_WOOD:
            log("Action: Collecting wood", "[Workflow]")
            client.collect_wood()
            return Observation(action_result="exploration")
            
        elif self.observation_result == ObservationResult.GET_MORE_COTTON:
            log("Action: Collecting cotton", "[Workflow]")
            client.collect_cotton()
            return Observation(action_result="exploration")
            
        elif self.observation_result == ObservationResult.COLLECT_SWORD:
            log("Action: Collecting sword", "[Workflow]")
            client.collect_sword()
            return Observation(action_result="exploration")
            
        elif self.observation_result == ObservationResult.COLLECT_ARMOR:
            log("Action: Collecting armor", "[Workflow]")
            client.collect_armor()
            return Observation(action_result="exploration")
            
        elif self.observation_result == ObservationResult.GO_HOME:
            log("Action: Returning home due to event", "[Workflow]")
            client.go_home()
            # Check if we've reached home
            player = client.get_player()
            if player.row == player.home_row and player.col == player.home_col:
                log('Reached home safely, event response complete', "[Workflow]")
                ctx.state.current_event_task = None  # Clear the event once home
            return Observation(action_result="event_response")
            
        elif self.observation_result == ObservationResult.COLLECT_REWARD:
            log("Action: Collecting reward from event", "[Workflow]")
            # Get the reward position from the current event task
            if ctx.state.current_event_task and ctx.state.current_event_task.reward_position:
                log(f"Attempting to collect reward at {ctx.state.current_event_task.reward_position}", "[Workflow]")
                reward_collected = client.collect_reward(ctx.state.current_event_task.reward_position)
                if reward_collected:
                    log(f'Successfully collected reward at {ctx.state.current_event_task.reward_position}', "[Workflow]")
                    ctx.state.current_event_task = None  # Clear the event once collected
                return Observation(action_result="event_response")
            else:
                log('No valid reward position specified in event', "[Workflow]")
                return Observation(action_result="exploration")
            
        elif self.observation_result == ObservationResult.EXPLORE:
            log("Action: Exploring the environment", "[Workflow]")
            client.explore()
            return Observation(action_result="exploration")
            
        elif self.observation_result == "WIN":
            log('Player has won the game!', "[Workflow]")
            return End(f"Player win the game")
            
        # Default fallback
        log("No specific action matched, defaulting to exploration", "[Workflow]")
        return Observation(action_result="exploration")

@dataclass
class Observation(BaseNode[GameState]):
    action_result: str = ""
    async def run(self, ctx: GraphRunContext[GameState]) -> Action:
        log(f"Observing game state after {self.action_result}", "[Workflow]")
        
        # Check if new message from server
        client = ctx.state.client
        player = client.get_player()
        
        # Process new server messages
        if player.message and player.message != ctx.state.last_processed_message:
            log(f'New message from server: "{player.message}"', "[Workflow]")
            
            # Use the event handler agent to analyze the message
            log("Analyzing message with event handler agent", "[Workflow]")
            event_task = ctx.state.event_handler_agent.analyze_message(player.message)
            log(f'Event analysis results: {event_task}', "[Workflow]")
            
            # Store the current event task in state
            ctx.state.current_event_task = event_task
            log(f"Event priority: {event_task.priority}", "[Workflow]")
            
            # Determine the next action based on the event analysis
            if event_task.should_go_home:
                log('Event requires going home immediately!', "[Workflow]")
                return Action(observation_result=ObservationResult.GO_HOME)
                
            elif event_task.has_reward and event_task.reward_position:
                log(f'Event offers reward at {event_task.reward_position}', "[Workflow]")
                return Action(observation_result=ObservationResult.COLLECT_REWARD)
        
        # Handle active events
        if ctx.state.current_event_task:
            log("Processing active event", "[Workflow]")
            if ctx.state.current_event_task.should_go_home:
                log("Active event requires going home", "[Workflow]")
                return Action(observation_result=ObservationResult.GO_HOME)
                
            elif ctx.state.current_event_task.has_reward:
                log("Active event offers a reward to collect", "[Workflow]")
                return Action(observation_result=ObservationResult.COLLECT_REWARD)

        # If we're in exploration mode or event response mode
        if self.action_result in ["exploration", "event_response"]:
            log("Making decision based on current game state", "[Workflow]")
            
            # Check for win condition
            if player.status == PlayerStatus.WIN:
                log('Win condition detected!', "[Workflow]")
                return Action(observation_result="WIN")
            
            # Calculate resource needs
            current_wood_need = ctx.state.wood_need - player.store.count('w')
            current_cotton_need = ctx.state.cotton_need - player.store.count('c') * ctx.state.fabric_to_cotton_ratio
            
            # Get resource positions
            position_of_woods = client.entity_positions['w']
            position_of_cottons = client.entity_positions['c']
            position_of_sword = client.entity_positions['s']
            position_of_armor = client.entity_positions['a']

            log(f'Current needs: {current_wood_need} wood, {current_cotton_need} cotton', "[Workflow]")
            log(f'Known resources: {len(position_of_woods)} wood, {len(position_of_cottons)} cotton, {len(position_of_sword)} swords, {len(position_of_armor)} armor', "[Workflow]")

            # Decision making with priority order
            # Prioritize collecting sword
            if len(position_of_sword) > 0:
                log("Decision: Collect sword (highest priority)", "[Workflow]")
                return Action(observation_result=ObservationResult.COLLECT_SWORD)
            
            # Prioritize collecting armor
            if len(position_of_armor) > 0:
                log("Decision: Collect armor (high priority)", "[Workflow]")
                return Action(observation_result=ObservationResult.COLLECT_ARMOR) 
            
            # Prioritize collecting wood
            if current_wood_need > 0 and len(position_of_woods) > 0:
                log("Decision: Collect wood (needed for win condition)", "[Workflow]")
                return Action(observation_result=ObservationResult.GET_MORE_WOOD)
            
            # Prioritize collecting cotton
            if current_cotton_need > 0 and len(position_of_cottons) > 0:
                log("Decision: Collect cotton (needed for win condition)", "[Workflow]")
                return Action(observation_result=ObservationResult.GET_MORE_COTTON)
            
        # Default action is to explore
        log("Decision: Continue exploring (default action)", "[Workflow]")
        return Action(observation_result=ObservationResult.EXPLORE)

# Define the game workflow graph
game_graph = Graph(
    nodes=[
        CreateGame, 
        TakeMission, 
        WaitingStartGame, 
        Observation, 
        Action
    ]
)

async def create_client_game(name: str):
    from game.game_state import Resource
    
    log(f"Creating new game for player: {name}", "[Main]")
    state = GameState(
        name = name,
        client = None, 
        calculate_win_condition_agent = CalculateWinConditionAgent(),
        event_handler_agent = None,  # Will be initialized in CreateGame node
        resource = Resource()
    )
    log("Game state initialized, starting game workflow", "[Main]")
    await game_graph.run(CreateGame(), state=state) 

class GameAction(Enum):
    EXPLORE = "EXPLORE"
    COLLECT_WOOD = "COLLECT_WOOD"
    COLLECT_COTTON = "COLLECT_COTTON"
    COLLECT_SWORD = "COLLECT_SWORD"
    COLLECT_ARMOR = "COLLECT_ARMOR"
    GO_HOME = "GO_HOME"
    COLLECT_REWARD = "COLLECT_REWARD"

class GameWorkflow:
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        log("GameWorkflow initialized", "[GameWorkflow]")
        
        # Initialize OpenAI API
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            log("Warning: OPENAI_API_KEY not found in environment variables", "[GameWorkflow]", level="WARNING")
        else:
            openai.api_key = self.api_key
            log("OpenAI API initialized", "[GameWorkflow]")
        
        # Initialize exploration tracking
        self.last_direction = None
        self.last_position = None
        self.last_action = None
        self.visited_positions = set()
        
    def _format_full_map(self, client) -> str:
        """Format the entire map state for the prompt."""
        player = client.get_player()
        if player is None or player.grid is None:
            return "Map not yet explored"
            
        map_str = "Full map state:\n"
        # Add column numbers
        map_str += "    " + " ".join(f"{i:2d}" for i in range(len(player.grid[0]))) + "\n"
        
        for i in range(len(player.grid)):
            # Add row numbers
            map_str += f"{i:2d} |"
            for j in range(len(player.grid[0])):
                if i == player.row and j == player.col:
                    map_str += " P "  # Player position
                else:
                    cell = str(player.grid[i][j])
                    # Format each cell with consistent width
                    if cell == '-1':
                        map_str += " ? "  # Unexplored
                    elif cell == 'g':
                        map_str += " . "  # Ground
                    elif cell == 'r':
                        map_str += " # "  # Rock
                    elif cell == 'w':
                        map_str += " W "  # Wood
                    elif cell == 'c':
                        map_str += " C "  # Cotton
                    elif cell == 's':
                        map_str += " S "  # Sword
                    elif cell == 'a':
                        map_str += " A "  # Armor
                    elif cell.isdigit():
                        map_str += f" {cell} "  # Other player
                    else:
                        map_str += f" {cell} "
            map_str += "\n"
            
        # Add legend
        map_str += "\nLegend:\n"
        map_str += "P = Player position\n"
        map_str += "? = Unexplored area\n"
        map_str += ". = Ground (walkable)\n"
        map_str += "# = Rock (obstacle)\n"
        map_str += "W = Wood resource\n"
        map_str += "C = Cotton resource\n"
        map_str += "S = Sword item\n"
        map_str += "A = Armor item\n"
        map_str += "1-9 = Other players\n"
            
        return map_str
        
    def _format_visible_map(self, client) -> str:
        """Format the current visible area around the player."""
        player = client.get_player()
        if player is None or player.grid is None:
            return "Map not yet explored"
            
        # Get the visible area around the player
        visible_range = 5  # Show 5 cells in each direction
        
        map_str = "Current visible area (5x5 around player):\n"
        # Add column numbers
        start_col = max(0, player.col - visible_range)
        end_col = min(len(player.grid[0]), player.col + visible_range + 1)
        map_str += "    " + " ".join(f"{i:2d}" for i in range(start_col, end_col)) + "\n"
        
        for i in range(max(0, player.row - visible_range), min(len(player.grid), player.row + visible_range + 1)):
            # Add row numbers
            map_str += f"{i:2d} |"
            for j in range(start_col, end_col):
                if i == player.row and j == player.col:
                    map_str += " P "  # Player position
                else:
                    cell = str(player.grid[i][j])
                    # Format each cell with consistent width
                    if cell == '-1':
                        map_str += " ? "  # Unexplored
                    elif cell == 'g':
                        map_str += " . "  # Ground
                    elif cell == 'r':
                        map_str += " # "  # Rock
                    elif cell == 'w':
                        map_str += " W "  # Wood
                    elif cell == 'c':
                        map_str += " C "  # Cotton
                    elif cell == 's':
                        map_str += " S "  # Sword
                    elif cell == 'a':
                        map_str += " A "  # Armor
                    elif cell.isdigit():
                        map_str += f" {cell} "  # Other player
                    else:
                        map_str += f" {cell} "
            map_str += "\n"
            
        # Add legend
        map_str += "\nLegend:\n"
        map_str += "P = Player position\n"
        map_str += "? = Unexplored area\n"
        map_str += ". = Ground (walkable)\n"
        map_str += "# = Rock (obstacle)\n"
        map_str += "W = Wood resource\n"
        map_str += "C = Cotton resource\n"
        map_str += "S = Sword item\n"
        map_str += "A = Armor item\n"
        map_str += "1-9 = Other players\n"
            
        return map_str
        
    def _check_for_other_players(self, client) -> tuple[bool, list[tuple[int, int]]]:
        """Check if there are other players in the visible area."""
        player = client.get_player()
        if player is None or player.grid is None:
            return False, []
            
        visible_range = 5
        other_players = []
        
        for i in range(max(0, player.row - visible_range), min(len(player.grid), player.row + visible_range + 1)):
            for j in range(max(0, player.col - visible_range), min(len(player.grid[0]), player.col + visible_range + 1)):
                cell = str(player.grid[i][j])
                if cell.isdigit() and cell != '0':  # Other player found
                    other_players.append((i, j))
                    
        return len(other_players) > 0, other_players
        
    def decide_next_action(self) -> GameAction:
        """Determine the next action based on current game state using LLM."""
        log("Deciding next action...", "[GameWorkflow]")
        
        # Get player information
        player = self.game_state.client.get_player()
        client = self.game_state.client
        
        # Check if we're currently in a "go home" task and not yet at home
        if (self.last_action == "GO_HOME" and 
            (player.row != player.home_row or player.col != player.home_col)):
            log("Still going home from previous task, continuing GO_HOME", "[GameWorkflow]")
            return GameAction.GO_HOME
        
        # First, check if there are any event tasks to handle (high priority)
        if self.game_state.event_tasks:
            event_task = self.game_state.event_tasks[0]
            log(f"Found event task: {event_task}", "[GameWorkflow]")
            
            if event_task.get("type") == "go_home":
                log("Priority action: GO_HOME due to event", "[GameWorkflow]")
                return GameAction.GO_HOME

            if event_task.get("type") == "win_condition":
                # Set win condition on the client
                client = self.game_state.client
                client.set_win_condition(
                    wood=event_task.get("wood", 0),
                    fabric=event_task.get("fabric", 0),
                    cotton_per_fabric=event_task.get("cotton_per_fabric", 2)
                )
                log(f"Updated client win condition: wood={event_task.get('wood', 0)}, fabric={event_task.get('fabric', 0)}, cotton_per_fabric={event_task.get('cotton_per_fabric', 2)}", "[GameWorkflow]")
                # Remove the win condition task as it's been processed
                self.game_state.event_tasks.pop(0)
                
            elif event_task.get("type") == "collect_reward":
                log(f"Priority action: COLLECT_REWARD at {event_task.get('position')}", "[GameWorkflow]")
                return GameAction.COLLECT_REWARD
        
        entity_positions = client.entity_positions
        
        # Check for other players in visible area
        has_other_players, other_player_positions = self._check_for_other_players(client)
        if has_other_players:
            log(f"Other players detected at positions: {other_player_positions}", "[GameWorkflow]")
        
        # Update visited positions
        current_pos = (player.row, player.col)
        self.visited_positions.add(current_pos)
        
        # Calculate resource needs using our local storage
        wood_needed = max(0, self.game_state.win_condition.get('wood', 0) - 
                         client.get_storage_count('w') - 
                         client.get_items_on_hand_count('w'))
                         
        cotton_needed = max(0, self.game_state.win_condition.get('cotton', 0) - 
                           client.get_storage_count('c') - 
                           client.get_items_on_hand_count('c'))
        
        # Get fabric to cotton ratio from win condition
        fabric_to_cotton_ratio = self.game_state.win_condition.get('cotton_per_fabric', 2)

        # Check if we're in exploration mode and if anything new was found
        if self.last_action == 'EXPLORE':
            # Check if any new resources were found in the visible area
            visible_range = 5
            new_resources_found = False
            for i in range(max(0, player.row - visible_range), min(len(player.grid), player.row + visible_range + 1)):
                for j in range(max(0, player.col - visible_range), min(len(player.grid[0]), player.col + visible_range + 1)):
                    cell = str(player.grid[i][j])
                    if cell in ['w', 'c', 's', 'a']:
                        pos = (i, j)
                        if cell == 'w' and pos not in entity_positions.get('w', []):
                            new_resources_found = True
                            break
                        elif cell == 'c' and pos not in entity_positions.get('c', []):
                            new_resources_found = True
                            break
                        elif cell == 's' and pos not in entity_positions.get('s', []):
                            new_resources_found = True
                            break
                        elif cell == 'a' and pos not in entity_positions.get('a', []):
                            new_resources_found = True
                            break
                if new_resources_found:
                    break

            # If no new resources found and we're in exploration mode, continue exploring
            if not new_resources_found and not has_other_players:
                log("No new resources found, continuing exploration", "[GameWorkflow]")
                return GameAction.EXPLORE

        # If we reach here, either we found new resources or we're not in exploration mode
        # Prepare the input for the LLM
        last_event_task = self.game_state.event_tasks[0] if self.game_state.event_tasks else 'None'
        
        # Format storage information
        storage_info = {
            'w': client.get_storage_count('w'),
            'c': client.get_storage_count('c'),
            'fa': client.get_storage_count('fa'),
            's': client.get_storage_count('s'),
            'a': client.get_storage_count('a')
        }
        
        # Calculate equipment status (worn/equipped)
        sword_equipped = client.get_items_on_hand_count('s') > 0
        armor_equipped = client.get_items_on_hand_count('a') > 0
        
        prompt = SYSTEM_PROMPTING.format(
            row=player.row,
            col=player.col,
            home_row=player.home_row,
            home_col=player.home_col,
            storage=storage_info,
            items_on_hand=client.items_on_hand,
            wood_needed=wood_needed,
            cotton_needed=cotton_needed,
            wood_positions=entity_positions.get('w', []),
            cotton_positions=entity_positions.get('c', []),
            sword_positions=entity_positions.get('s', []),
            armor_positions=entity_positions.get('a', []),
            event_tasks=self.game_state.event_tasks,
            status=player.status.value,
            wood_count=client.get_storage_count('w'),
            cotton_count=client.get_storage_count('c'),
            fabric_count=client.get_storage_count('fa'),
            sword_count=client.get_storage_count('s'),
            armor_count=client.get_storage_count('a'),
            sword_equipped=sword_equipped,
            armor_equipped=armor_equipped,
            last_event_task=last_event_task,
            full_map=self._format_full_map(client),
            current_visible_map=self._format_visible_map(client),
            previous_position=self.last_position if self.last_position else 'None',
            last_action=self.last_action if self.last_action else 'None',
            last_direction=self.last_direction if self.last_direction else 'None',
            visited_positions=sorted(list(self.visited_positions)),
            fabric_to_cotton_ratio=fabric_to_cotton_ratio,
            max_storage=Config.MAX_STORAGE_CAPACITY
        )
        
        # Write the prompt to a file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        prompt_filename = f"prompts/prompt_{timestamp}.txt"
        os.makedirs("prompts", exist_ok=True)
        with open(prompt_filename, "w", encoding="utf-8") as f:
            f.write("\n\n=== User Prompt ===\n")
            f.write(prompt)
        log(f"Prompt saved to {prompt_filename}", "[GameWorkflow]")
        
        try:
            log("Calling OpenAI API for decision making", "[GameWorkflow]")
            response = openai.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPTING},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            log(f"LLM response: {content}", "[GameWorkflow]")
            
            # Write the response to the same file
            with open(prompt_filename, "a", encoding="utf-8") as f:
                f.write("\n\n=== LLM Response ===\n")
                f.write(content)
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                action_name = result.get("action", "EXPLORE")
                explanation = result.get("explanation", "No explanation provided")
                
                log(f"Decision: {action_name} - {explanation}", "[GameWorkflow]")
                
                # Update movement history
                self.last_position = current_pos
                self.last_action = action_name
                if action_name == "EXPLORE":
                    # Calculate direction based on movement
                    if self.last_position:
                        row_diff = player.row - self.last_position[0]
                        col_diff = player.col - self.last_position[1]
                        self.last_direction = (row_diff, col_diff)
                
                # Convert the action name string to GameAction enum
                try:
                    return GameAction[action_name]
                except KeyError:
                    log(f"Invalid action name: {action_name}, defaulting to EXPLORE", "[GameWorkflow]")
                    return GameAction.EXPLORE
                    
            except json.JSONDecodeError as e:
                log(f"Error parsing JSON response: {e}", "[GameWorkflow]")
                log(f"Raw response: {content}", "[GameWorkflow]")
                
                # Fall back to rule-based decision making
                return self._rule_based_decision()
                
        except Exception as e:
            log(f"Error calling OpenAI API: {e}", "[GameWorkflow]")
            
            # Fall back to rule-based decision making
            return self._rule_based_decision()
    
    def _rule_based_decision(self) -> GameAction:
        """Fallback rule-based decision making when LLM fails."""
        log("Using rule-based decision making as fallback", "[GameWorkflow]")
        
        # Get player information
        player = self.game_state.client.get_player()
        entity_positions = self.game_state.client.entity_positions
        
        # Check if player is carrying items and should return home
        if player.items_on_hand:
            log(f"Player carrying items: {player.items_on_hand}, going home", "[GameWorkflow]")
            return GameAction.GO_HOME
        
        # Priority 1: Collect sword if available
        if entity_positions.get('s'):
            log("Found sword - prioritizing sword collection", "[GameWorkflow]")
            return GameAction.COLLECT_SWORD
            
        # Priority 2: Collect armor if available
        if entity_positions.get('a'):
            log("Found armor - prioritizing armor collection", "[GameWorkflow]")
            return GameAction.COLLECT_ARMOR
            
        # Calculate resource needs
        wood_needed = max(0, self.game_state.win_condition.get('wood', 0) - 
                         player.store.count('w') - 
                         player.items_on_hand.count('w'))
                         
        cotton_needed = max(0, self.game_state.win_condition.get('cotton', 0) - 
                           player.store.count('c') - 
                           player.items_on_hand.count('c'))
        
        # Priority 3: Collect wood if needed and available
        if wood_needed > 0 and entity_positions.get('w'):
            log("Prioritizing wood collection", "[GameWorkflow]")
            return GameAction.COLLECT_WOOD
            
        # Priority 4: Collect cotton if needed and available
        if cotton_needed > 0 and entity_positions.get('c'):
            log("Prioritizing cotton collection", "[GameWorkflow]")
            return GameAction.COLLECT_COTTON
            
        # Default: Explore to find more resources
        log("No specific resource needs, continuing exploration", "[GameWorkflow]")
        return GameAction.EXPLORE
        
    def execute_action(self, action: GameAction):
        """Execute the specified game action."""
        log(f"Executing action: {action}", "[GameWorkflow]")
        
        client = self.game_state.client
        
        if action == GameAction.EXPLORE:
            client.explore()
            
        elif action == GameAction.COLLECT_WOOD:
            client.collect_wood()
            
        elif action == GameAction.COLLECT_COTTON:
            client.collect_cotton()
            
        elif action == GameAction.COLLECT_SWORD:
            client.collect_sword()
            
        elif action == GameAction.COLLECT_ARMOR:
            client.collect_armor()
            
        elif action == GameAction.GO_HOME:
            client.go_home()
            # Check if we've completed the "go_home" event task
            if self.game_state.event_tasks and self.game_state.event_tasks[0].get("type") == "go_home":
                player = client.get_player()
                if player.row == player.home_row and player.col == player.home_col:
                    log("Completed GO_HOME event task", "[GameWorkflow]")
                    self.game_state.event_tasks.pop(0)
            
        elif action == GameAction.COLLECT_REWARD:
            # Get the reward position from the event task
            if self.game_state.event_tasks and self.game_state.event_tasks[0].get("type") == "collect_reward":
                reward_position = self.game_state.event_tasks[0].get("position")
                if reward_position:
                    # If we successfully collected the reward, remove the task
                    if client.collect_reward(reward_position):
                        log("Completed COLLECT_REWARD event task", "[GameWorkflow]")
                        self.game_state.event_tasks.pop(0)
                else:
                    log("Error: No position specified in collect_reward task", "[GameWorkflow]")
            else:
                log("Error: No collect_reward task found", "[GameWorkflow]")
                
    def run_game_loop(self):
        """Main game loop that decides and executes actions continuously."""
        log("Starting game loop", "[GameWorkflow]")
        
        while True:
            try:
                # Update player information
                self.game_state.client.get_player()
                
                # Process any new messages
                self.game_state.process_messages()
                
                # Decide and execute next action
                action = self.decide_next_action()
                self.execute_action(action)
                
                # Small delay to prevent overwhelming the server
                time.sleep(1)
                
            except Exception as e:
                log(f"Error in game loop: {e}", "[GameWorkflow]")
                time.sleep(5)  # Longer delay on error 