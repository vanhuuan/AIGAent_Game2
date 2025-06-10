# Test Agent Explanation

This document explains the autonomous agent implementation for playing the Rules of Survival game. The agent is built with a modular architecture that uses AI-powered decision making and a workflow-based approach to gameplay.

## Structure Overview

The agent implementation consists of:

1. **Agent Classes** - Specialized agents with specific responsibilities
2. **Task Definitions** - Different types of tasks the agent can perform
3. **Game Client Implementation** - Extension of the base Client class
4. **Workflow Graph** - A decision tree for agent behaviors

## Key Components

### 1. Agent Classes

The implementation uses two main agent classes:

#### OrchestratorAgent (`agents/orchestrator_agent.py`)

This high-level decision-making agent determines what task the player should perform next based on the current state of the game and resource needs:

```python
@dataclass
class OrchestratorAgent:
    """
    High-level decision-making agent that determines what task the player 
    should perform next based on the current state of the game and resource needs.
    """
    
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
```

The OrchestratorAgent uses a large language model to analyze the game state and decide on the next best action to take. It prioritizes collecting resources needed to win the game (wood and cotton) while managing other needs like food collection and map exploration.

#### PlayGameAgent (`agents/play_game_agent.py`)

This agent handles resource identification and pathfinding:

```python
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
```

The PlayGameAgent provides tools for:
- Finding food, wood, and cotton resources on the map
- Identifying unexplored areas
- Calculating the shortest path to resources using A* pathfinding

### 2. Task Definitions (`models/tasks.py`)

Tasks are represented as Pydantic models that define different actions the agent can take:

```python
class Task(BaseModel):
    task_description: str
    
class CalCulateWinConditionTask(Task):
    """
    Step by step to calculate resource need, you can apply some calculate as +, -, * , / operator
    """
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

Additional models are defined for resource positions and pathfinding:

```python
class ResourcePositions(BaseModel):
    positions: List[Position]
    explain: str

class FoodPositions(ResourcePositions):
    pass

class WoodPositions(ResourcePositions):
    pass

class CottonPositions(ResourcePositions):
    pass

class MapExplorer(BaseModel):
    positions: List[Position]
    explain: str
     
class Path(BaseModel):
    directions: List[int]
    explain: str
```

### 3. GameClient Implementation (`game_client.py`)

The GameClient extends the base Client class with additional capabilities:

```python
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
```

The GameClient provides methods for:
- Finding the shortest path to specific locations
- Moving along paths step by step
- Navigating back to the home base
- Tracking token usage for AI models

### 4. Workflow Graph (`workflow/game_graph.py`)

The agent uses a graph-based workflow to orchestrate behavior:

```python
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
```

The workflow consists of several node types:
- `CreateGame`: Initial node that starts the workflow
- `TakeMission`: Parses the game mission to identify resource requirements
- `WaitingStartGame`: Waits for the game to start
- `IdentifyTask`: Determines the next task to perform
- `ExecuteTask`: Executes the identified task

The `ExecuteTask` node implements sophisticated algorithms for:
1. **Resource Collection**: Finding and navigating to the nearest resource of a specific type
2. **Map Discovery**: Using a frontier-based exploration algorithm that efficiently explores unknown areas

## How It Works

1. The entry point (`main.py`) initializes the GameClient and workflow
2. The workflow starts with the `CreateGame` node
3. The agent parses the initial mission to understand resource requirements
4. When the game starts, the agent continuously cycles through:
   - Assessing the current state (`IdentifyTask`)
   - Deciding on a task (via `OrchestratorAgent`)
   - Finding resources/paths (via `PlayGameAgent`)
   - Executing movements and actions (`ExecuteTask`)

The agent makes intelligent decisions based on:
- Current resource needs (wood and cotton required to win)
- Map knowledge (explored vs unexplored areas)
- Resource availability (locations of food, wood, and cotton)
- Efficient pathfinding (using A* algorithm)

## Advanced Features

1. **Frontier-based Exploration**: The agent maintains a frontier of unexplored cells at the edge of known territory, allowing for efficient map discovery
2. **Prioritized Resource Collection**: Resources needed to win (wood, cotton) are prioritized over food
3. **A* Pathfinding**: Efficient pathfinding to navigate to resources and unexplored areas
4. **Dynamic Task Selection**: The agent continuously reassesses its tasks based on the changing game state

## Extension Possibilities

The modular design allows for:

1. Implementing different strategies by modifying the `OrchestratorAgent`
2. Improving pathfinding by enhancing the `PlayGameAgent`
3. Adding more sophisticated behavior by creating new task types
4. Enhancing the workflow graph with additional states and transitions
5. Implementing combat strategies for player-vs-player interactions 