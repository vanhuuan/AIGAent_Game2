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

from promptings import SYSTEM_PROMPTING, DECISION_MAKING_PROMPT
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
        
    def decide_next_action(self) -> GameAction:
        """Determine the next action based on current game state using LLM."""
        log("Deciding next action using LLM...", "[GameWorkflow]")
        
        # First, check if there are any event tasks to handle (high priority)
        if self.game_state.event_tasks:
            event_task = self.game_state.event_tasks[0]
            log(f"Found event task: {event_task}", "[GameWorkflow]")
            
            if event_task.get("type") == "go_home":
                log("Priority action: GO_HOME due to event", "[GameWorkflow]")
                return GameAction.GO_HOME
                
            elif event_task.get("type") == "collect_reward":
                log(f"Priority action: COLLECT_REWARD at {event_task.get('position')}", "[GameWorkflow]")
                return GameAction.COLLECT_REWARD
        
        # Get player information
        player = self.game_state.client.get_player()
        entity_positions = self.game_state.client.entity_positions
        
        # Calculate resource needs
        wood_needed = max(0, self.game_state.win_condition.get('wood', 0) - 
                         player.store.count('w') - 
                         player.items_on_hand.count('w'))
                         
        cotton_needed = max(0, self.game_state.win_condition.get('cotton', 0) - 
                           player.store.count('c') - 
                           player.items_on_hand.count('c'))
        
        # Prepare the input for the LLM
        prompt = DECISION_MAKING_PROMPT.format(
            row=player.row,
            col=player.col,
            inventory=player.store,
            items_on_hand=player.items_on_hand,
            wood_needed=wood_needed,
            cotton_needed=cotton_needed,
            wood_positions=entity_positions.get('w', []),
            cotton_positions=entity_positions.get('c', []),
            sword_positions=entity_positions.get('s', []),
            armor_positions=entity_positions.get('a', []),
            event_tasks=self.game_state.event_tasks,
            status=player.status.value
        )
        
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
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                action_name = result.get("action", "EXPLORE")
                explanation = result.get("explanation", "No explanation provided")
                
                log(f"Decision: {action_name} - {explanation}", "[GameWorkflow]")
                
                # Convert the action name string to GameAction enum
                try:
                    return GameAction[action_name]
                except KeyError:
                    log(f"Invalid action name: {action_name}, defaulting to EXPLORE", "[GameWorkflow]", level="WARNING")
                    return GameAction.EXPLORE
                    
            except json.JSONDecodeError as e:
                log(f"Error parsing JSON response: {e}", "[GameWorkflow]", level="ERROR")
                log(f"Raw response: {content}", "[GameWorkflow]")
                
                # Fall back to rule-based decision making
                return self._rule_based_decision()
                
        except Exception as e:
            log(f"Error calling OpenAI API: {e}", "[GameWorkflow]", level="ERROR")
            
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