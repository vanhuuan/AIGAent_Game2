# Code Organization

This project has been reorganized to improve code readability and maintainability. The original implementation is preserved in `implememt-game-client.py` while the reorganized code follows a more modular approach.

## Directory Structure

```
.
├── main.py                     # Entry point for running the game
├── agents/                     # AI agent implementations
│   ├── __init__.py             
│   └── win_condition_agent.py  # Agent for calculating win conditions
├── game/                       # Game implementation code
│   ├── __init__.py
│   ├── game_client.py          # Game client implementation
│   ├── game_state.py           # Game state and observation models
│   └── game_workflow.py        # Game workflow logic using pydantic_graph
└── utils/                      # Utility functions
    ├── __init__.py
    └── pathfinding.py          # Path finding algorithms
```

## How to Run

You can run the game using the following command:

```bash
python main.py
```

This will start the game with a random Vietnamese player name.

You can also specify a custom player name:

```bash
python main.py --name "YourName"
```

## Implementation Details

1. **Game Client**: The `GameClient` class extends the base `Client` class and provides methods for game actions like collecting resources, moving, and exploring.

2. **Win Condition Agent**: The `CalculateWinConditionAgent` class uses LLM to parse win conditions from text messages.

3. **Game Workflow**: Uses pydantic_graph to implement a state machine for the game flow.

4. **Pathfinding**: Contains utilities for finding the shortest path to resources or unexplored areas.

The code organization separates concerns between game logic, agent intelligence, and utility functions, making it easier to maintain and extend. 