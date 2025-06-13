# Algorithms in the Game Client

This document explains in detail the key algorithms used in the autonomous agent game client.

## 1. Pathfinding Algorithms

### Breadth-First Search (BFS)
**File**: `utils/pathfinding.py`
**Functions**: `shortest_path`, `shortest_path_to_value`

BFS is a graph traversal algorithm that explores all vertices at the current depth before moving to vertices at the next depth level.

#### Implementation Details:
```python
def shortest_path(grid, start, target):
    # Define directions: left, right, up, down
    MOVES = [
        (0, -1, 0),  # left
        (0, 1, 1),   # right
        (-1, 0, 2),  # up
        (1, 0, 3),   # down
    ]
    
    # Create a queue for BFS
    queue = deque([(start[0], start[1], [])])
    visited = [[False] * w for _ in range(h)]
    visited[start[0]][start[1]] = True
    
    while queue:
        r, c, path = queue.popleft()
        
        # If we reached the target
        if (r, c) == (tr, tc):
            return path
            
        # Check all four directions
        for dr, dc, mv in MOVES:
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, temp) and not visited[nr][nc]:
                visited[nr][nc] = True
                queue.append((nr, nc, path + [mv]))
```

#### Complexity:
- **Time Complexity**: O(V + E) where V is the number of vertices (cells in the grid) and E is the number of edges
- **Space Complexity**: O(V) for the visited array and queue

#### Advantages:
- Guarantees the shortest path in an unweighted graph
- Simple to implement
- Works well for grid-based movement where all moves have equal cost

#### Limitations:
- Not optimal for weighted graphs (if different terrain had different movement costs)
- Explores in all directions equally, which can be inefficient for large maps

#### Improvement Opportunities:
- Implement A* algorithm which uses a heuristic to guide the search toward the target
- Add weights for different terrain types if needed
- Implement bidirectional search for faster path finding

## 2. Resource Discovery Algorithm

**File**: `utils/pathfinding.py`
**Function**: `find_adjacent_resources`

This algorithm scans a 5×5 grid area centered on the player to discover resources in the surrounding area.

#### Implementation Details:
```python
def find_adjacent_resources(grid, row, col):
    # Dictionary to store found resources
    adjacent_resources = {
        'w': [], 'c': [], 'f': [], 's': [], 'a': [],
        '0': [], '1': [], '2': [], '3': [], '4': [], '5': [], '6': [],
    }
    
    # Define a 5x5 search area
    directions = [
        (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),  # row -2
        (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),  # row -1
        (0, -2), (0, -1), (0, 0), (0, 1), (0, 2),       # row 0
        (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),       # row 1
        (2, -2), (2, -1), (2, 0), (2, 1), (2, 2),       # row 2
    ]
    
    # Check each cell in the search area
    for direction in directions:
        new_row, new_col = row + direction[0], col + direction[1]
        
        # Check if within grid bounds
        if 0 <= new_row < grid.shape[0] and 0 <= new_col < grid.shape[1]:
            cell_value = str(grid[new_row, new_col])
            
            # If it's a resource we're tracking
            if cell_value in adjacent_resources.keys():
                # Special handling for items and players
                if cell_value in ['s','a','1','2','3','4','5','6']:
                    adjacent_resources[cell_value] = [(new_row, new_col)]
                else:
                    # For resources, find adjacent walkable cells
                    for p in [(new_row-1, new_col), (new_row+1, new_col), 
                             (new_row, new_col-1), (new_row, new_col+1)]:
                        if 0 <= p[0] < grid.shape[0] and 0 <= p[1] < grid.shape[1]:
                            if grid[*p] == 'g' or grid[*p] == '-1':
                                adjacent_resources[cell_value] += [p]
```

#### Complexity:
- **Time Complexity**: O(1) as it checks a fixed 5×5 area and a fixed number of adjacent cells
- **Space Complexity**: O(1) as it stores a limited number of resource positions

#### Advantages:
- Fast operation with constant time complexity
- Provides nearby resource information for immediate decision making
- Helps build a mental map of the environment

#### Limitations:
- Limited to a fixed search area
- May miss resources just outside the search area
- Current implementation doesn't track resource depletion

#### Improvement Opportunities:
- Implement resource memory with timestamps to track when resources were last seen
- Add probabilistic resource modeling for areas not yet explored
- Implement more sophisticated adjacent cell finding for collecting resources

## 3. Decision Making Algorithm

**File**: `game/game_workflow.py`
**Class**: `Observation`

The client uses a priority-based decision making algorithm to determine the next action.

#### Implementation Details:
```python
def run(self, ctx: GraphRunContext[GameState]) -> Action:
    # Check for new server messages
    if player.message not in client.messages:
        client.messages.append(player.message)
        return Action(player.message)
    
    # If we're in exploration mode
    elif self.action_result == "exploration":
        # Check for win condition
        if player.status == PlayerStatus.WIN:
            return Action(observation_result="WIN")
        
        # Calculate resource needs
        current_wood_need = ctx.state.wood_need - player.store.count('w')
        current_cotton_need = ctx.state.cotton_need - player.store.count('c') * ctx.state.fabric_to_cotton_ratio
        
        # Get resource positions
        position_of_woods = client.entity_positions['w']
        position_of_cottons = client.entity_positions['c']
        position_of_sword = client.entity_positions['s']
        position_of_armor = client.entity_positions['a']
        
        # Decision making with priority order
        if len(position_of_sword) > 0:
            return Action(observation_result=ObservationResult.COLLECT_SWORD)
        
        if len(position_of_armor) > 0:
            return Action(observation_result=ObservationResult.COLLECT_ARMOR)
        
        if current_wood_need > 0 and len(position_of_woods) > 0:
            return Action(observation_result=ObservationResult.GET_MORE_WOOD)
        
        if current_cotton_need > 0 and len(position_of_cottons) > 0:
            return Action(observation_result=ObservationResult.GET_MORE_COTTON)
        
    # Default action is to explore
    return Action(observation_result=ObservationResult.EXPLORE)
```

#### Complexity:
- **Time Complexity**: O(1) as it performs a fixed number of checks
- **Space Complexity**: O(1) as it uses a fixed amount of memory

#### Decision Priority:
1. Process new server messages first
2. Check for win condition
3. Collect sword if available
4. Collect armor if available
5. Collect wood if needed and available
6. Collect cotton if needed and available
7. Default to exploration

#### Advantages:
- Simple and predictable behavior
- Clear priority ordering makes debugging easier
- Fast decision making with constant time complexity

#### Limitations:
- Fixed priorities don't adapt to changing game conditions
- Doesn't consider distance to resources when making decisions
- No consideration of other players or strategic positioning

#### Improvement Opportunities:
- Implement utility-based decision making that considers multiple factors
- Add distance weighting to prioritize closer resources
- Incorporate opponent modeling and avoidance strategies
- Implement dynamic priority adjustment based on game state

## 4. State Machine for Game Flow

**File**: `game/game_workflow.py`
**Implementation**: Using pydantic_graph to model game flow as a directed graph

The game uses a state machine pattern to manage the overall game flow through different phases.

#### States:
1. **CreateGame**: Initializes the game client
2. **TakeMission**: Receives and parses the mission/win conditions
3. **WaitingStartGame**: Waits for the game to start
4. **Action**: Executes a specific action in the game
5. **Observation**: Observes the game state and decides the next action

#### State Transitions:
```
CreateGame → TakeMission → WaitingStartGame → Action ↔ Observation → End
```

#### Advantages:
- Clear separation of concerns between different game phases
- Explicit state transitions make the flow easy to understand
- Modular design allows adding new states or modifying transitions

#### Limitations:
- Linear flow doesn't handle unexpected events well
- No parallel state execution for complex behaviors
- Limited error recovery between states

#### Improvement Opportunities:
- Add error states and recovery paths
- Implement hierarchical state machines for more complex behavior
- Add conditional transitions based on game state
- Implement event-driven transitions for more responsive behavior

## 5. Natural Language Processing for Win Conditions

**File**: `agents/win_condition_agent.py`
**Implementation**: Uses OpenAI LLM to extract structured information from text

This algorithm leverages large language models to parse natural language instructions and extract specific requirements.

#### Process:
1. Receive a text message from the server
2. Send the message to the LLM with specific instructions
3. Parse the structured output (wood_need, cotton_need, fabric_to_cotton_ratio)
4. Validate the output to ensure requirements are met
5. Return the structured win conditions

#### Advantages:
- Can handle various phrasings and formats of instructions
- Extracts structured data from unstructured text
- More flexible than rule-based parsing

#### Limitations:
- Depends on external API availability
- May have higher latency than rule-based approaches
- Could fail for unusual or ambiguous instructions

#### Improvement Opportunities:
- Implement local fallback parser for common patterns
- Add caching to avoid redundant API calls
- Implement a feedback loop to improve parsing accuracy

## Missing Algorithms and Future Implementations

### 1. Dynamic Event Handler
**Purpose**: Process and respond to dynamic game events (storms, rewards, etc.)
**Proposed Implementation**: 
- Create an event parser that categorizes events
- Implement specific handlers for each event type
- Add priority override for urgent events

### 2. Combat Strategy Algorithm
**Purpose**: Make decisions during player encounters
**Proposed Implementation**:
- Implement threat assessment based on opponent inventory
- Add escape path planning when outmatched
- Create offensive strategies when having advantage

### 3. Resource Efficiency Optimizer
**Purpose**: Optimize resource collection based on distance and need
**Proposed Implementation**:
- Calculate utility scores for each resource based on:
  - Distance to resource
  - Current need
  - Risk factors (proximity to other players)
- Select the resource with the highest utility score

### 4. Exploration Optimization
**Purpose**: Improve exploration efficiency
**Proposed Implementation**:
- Track explored/unexplored areas with a probabilistic map
- Prioritize unexplored areas with highest information gain
- Implement frontier-based exploration 