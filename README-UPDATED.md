# Rules of Survival Game

## Overview
This is a 2D grid-based autonomous agent gameplay system where AI agents compete to collect resources, craft items, and ultimately escape from an island by building a boat.

## Game Mechanics

### Map and Environment
- The game takes place on a 2D grid map where agents can move in four directions (left, right, up, down)
- The map contains various resources and items that agents can collect
- Agents have a limited vision radius around their current position
- Previously explored areas remain visible but appear dimmed

### Cell Types
- `'g'`: Ground - walkable tile for players
- `'f'`: Food - a collectible resource
- `'w'`: Wood - a collectible resource needed for boat building
- `'c'`: Cotton - a collectible resource that can be converted to fabric
- `'s'`: Sword - a collectible weapon for combat
- `'a'`: Armor/Shield - a collectible defensive item
- `-1`: Unexplored cell
- `number`: The ID of another player

### Gameplay Goals
The main objective is to build a boat to escape the island, which requires:
- Collecting specific amounts of wood
- Collecting cotton and converting it to fabric (e.g., 3 cotton → 1 fabric)
- Managing inventory (maximum 50 items per agent)

### Combat System
When two agents meet:
- No Sword/Shield: Continue moving
- Shield vs Shield: Agent loses Shield and continues moving
- Sword vs Sword: Agent loses Sword and is returned to Home base
- Sword vs Shield: Agent loses item and continues moving
- Sword vs No Sword/Shield: Agent steals the item and the other agent is returned to Home

### Dynamic Events
The game includes unexpected events that appear during matches:
- 🎁 Reward Box: Agents can go to announced locations to receive rewards
- ⛈️ Rain/Storm: Agents must return home or risk losing carried items

### Scoring System
- Building a boat to escape: 250 points + bonus points based on completion order
- Collecting items: Food (1p), Wood (3p), Cotton (3p), Fabric (20p)
- Final ranking is based on total points earned

## Technical Components

### Server
- Run with `python server.py`
- Provides a GUI interface for monitoring
- Updates player information once per second (game tick)
- Accepts client connections until game start

### Client
- Extends the base `Client` class to implement autonomous agent behavior
- Connects to server automatically
- Provides methods for:
  - Movement (move_left, move_right, move_up, move_down)
  - Resource collection (allow_collect_items)
  - Player information retrieval (get_player)
  - Map exploration

### Message Dispatcher
- Handles broadcasting events to all game clients
- Found in `client_communicator.ipynb`

## Development and Testing
- `test-agent.ipynb` contains a sample implementation of a game client
- The repository includes utility functions for pathfinding, resource discovery, and other common tasks
- Agent implementation can leverage AI models to make strategic decisions

## Setup and Requirements
- Install dependencies with `uv sync` (uses the requirements.txt file)
- Configure environment variables using the .env-template file
- Run the server and client(s) to start a game session

## Getting Started
1. Clone the repository
2. Install dependencies
3. Start the server with `python server.py`
4. Implement your autonomous agent by extending the Client class
5. Connect your agent to the server and start playing 