# Test Agent Explanation

The `test-agent.ipynb` file implements an AI-powered autonomous agent for playing the Rules of Survival game. The notebook is structured into several key components that work together to create a game-playing agent.

## Structure Overview

The test-agent.ipynb contains:

1. **Task Definitions** - Different types of tasks the agent can perform
2. **Agent Classes** - Different specialized agents with specific responsibilities
3. **Game Client Implementation** - Extension of the base Client class
4. **Workflow Graph** - A decision tree for agent behaviors

## Key Components

### 1. Task Definitions

The agent uses a task-based architecture, where different tasks are represented as Pydantic models:

```python
class Task(BaseModel):
    task_description: str
    
class CalCulateWinConditionTask(Task):
    explain: str
    wood_need: int
    cotton_need: int

class CollectResourceTask(Task):
    position: Position
    
class CollectFoodTask(CollectResourceTask):
    pass

class CollectWoodTask(CollectResourceTask):
    pass

class CollectCottonTask(CollectResourceTask):
    pass

class GoHomeTask(Task):
    pass

class DiscoverMapTask(Task):
    pass

class UnknownTask(Task):
    pass
```

These task classes define the different types of actions the agent can decide to take.

### 2. Agent Classes

The notebook implements two main agent classes:

#### OrchestratorAgent

This is a high-level decision-making agent that determines what task the player should perform next based on the current state of the game and resource needs:

```python
@dataclass
class OrchestratorAgent:
    # Define constants for actions
    KILL_OTHERS_TASK = "kill other players"
    COLLECT_FOOD_TASK = "collect food"
    COLLECT_WOOD_TASK = "collect wood"
    COLLECT_COTTON_TASK = "collect cotton"
    GOTO_CELL_TASK = "Go to cell to collect resource"
    DISCOVER_MAP_TASK = "discover map"
    CALCULATE_WIN_CONDITION = "calculate condition to win the game"
    GO_HOME_TASK = "go home"
    UNKNOWN_TASK = "unknown"
    
    # Agent initialization with OpenAI model
    agent = Agent(
        f'openai:{config.LLM_MODEL}',
        output_type= CalCulateWinConditionTask | CollectFoodTask | CollectWoodTask | CollectCottonTask | GoHomeTask | Task | DiscoverMapTask | UnknownTask,
        system_prompt=("You are a helpful ai assistant\nSuggest the task to win the game"),
        result_retries=2,
    )
```

The OrchestratorAgent uses a large language model to analyze the game state and decide on the next best action to take.

#### PlayGameAgent

This agent handles resource identification and pathfinding:

```python
@dataclass
class PlayGameAgent:
    config = Config()
    agent = Agent(
        f'openai:{config.LLM_MODEL}',
        output_type= FoodPositions | WoodPositions | CottonPositions | MapExplorer | Path,
        system_prompt= prompting_for_finding_resource,
        deps_type=FindContext
    )
    
    # Methods for finding resources and paths
    @agent.tool
    def map_expolorer(ctx: RunContext[FindContext]) -> list:
        """Find -1 cells"""
        ...
        
    @agent.tool
    def find_food(ctx: RunContext[FindContext]) -> list:
        """Find food cells"""
        ...
    
    @agent.tool
    def find_wood(ctx: RunContext[FindContext]) -> list:
        """Find wood cells"""
        ...
    
    @agent.tool
    def find_cotton(ctx: RunContext[FindContext]) -> list:
        """Find cotton cells"""
        ...
        
    @agent.tool
    def find_shortest_path(ctx: RunContext[FindContext], resource_positions: list[Position]) -> list:
        """Find shortest path"""
        ...
```

This agent is responsible for scanning the map and locating resources.

### 3. GameClient Implementation

The notebook extends the base Client class to create a GameClient with additional capabilities:

```python
class GameClient(Client):
    def __init__(self):
        super().__init__()
        self.task: str = ''
        self.messages: list[str] = []
        self.usage = Usage()
        self.orchestrator_agent = OrchestratorAgent()
        self.play_game_agent = PlayGameAgent()
        
    # Methods for gameplay
    def find_shortest_path_to(self, row, col):
        ...
    
    def go_step_by_step(self, path: list[int]):
        ...
    
    def go_home(self):
        ...
```

This implementation integrates the agents and provides additional game-specific functionality.

### 4. Workflow Graph

The notebook uses a graph-based workflow to orchestrate the agent's behavior:

```python
@dataclass
class GameState:  
    client: GameClient
    name: str
    food_need: int 
    fabric_need: int

@dataclass
class CreateGame(BaseNode[GameState]):  
    async def run(self, ctx: GraphRunContext[GameState]) -> TakeMission:
        return TakeMission()

@dataclass
class TakeMission(BaseNode[GameState]):
    async def run(self, ctx: GraphRunContext[GameState]) -> WaitingStartGame:
        # Implementation...
        
@dataclass
class WaitingStartGame(BaseNode[GameState]):
    async def run(self, ctx: GraphRunContext[GameState]) -> IdentifyTask | End:
        # Implementation...
```

This workflow manages the sequence of high-level operations performed by the agent.

## How It Works

1. The workflow starts when the game begins
2. The agent parses the initial message to understand the game goal
3. When the game starts, the agent continuously cycles through:
   - Assessing the current state (OrchestratorAgent)
   - Deciding on a task (OrchestratorAgent)
   - Finding resources/paths (PlayGameAgent)
   - Executing movements and actions (GameClient)
   
The agent uses AI language models to make decisions based on the game state, resource locations, and objectives.

## Extension Possibilities

The modular design of the test agent allows for:

1. Implementing different strategies by modifying the OrchestratorAgent
2. Improving pathfinding by enhancing the PlayGameAgent
3. Adding more sophisticated behavior by creating new task types
4. Enhancing the workflow graph with additional states and transitions 