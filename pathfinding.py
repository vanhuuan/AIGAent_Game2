from collections import deque
import numpy as np
from typing import List, Tuple, Optional
from logs import log

def shortest_path(
    grid: np.ndarray,
    start: Tuple[int, int],
    target: Tuple[int, int],
) -> Optional[List[int]]:
    """
    Return a list of moves (0=left, 1=right, 2=up, 3=down) from start to target,
    or None if no path exists. Only cells with value 'g' or '-1' are traversable.
    """
    log(f"Finding shortest path from {start} to {target}", "[Pathfinding]")
    
    MOVES = [
        ( 0, -1,  0),  # left
        ( 0,  1,  1),  # right
        (-1,  0,  2),  # up
        ( 1,  0,  3),  # down
    ]

    h, w = grid.shape

    def is_valid(r: int, c: int, g: np.ndarray) -> bool:
        if not (0 <= r < h and 0 <= c < w):
            return False
        val = g[r, c]
        return val == 'g' or val == '-1'

    # Copy so we don't modify the original grid
    temp = grid.copy()
    tr, tc = target
    # Mark the target as reachable even if it wasn't 'g' or '-1'
    temp[tr, tc] = 'g'

    visited = [[False] * w for _ in range(h)]
    queue = deque([(start[0], start[1], [])])
    visited[start[0]][start[1]] = True

    while queue:
        r, c, path = queue.popleft()

        if (r, c) == (tr, tc):
            log(f"Path found with {len(path)} steps: {path}", "[Pathfinding]")
            return path

        for dr, dc, mv in MOVES:
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, temp) and not visited[nr][nc]:
                visited[nr][nc] = True
                queue.append((nr, nc, path + [mv]))

    log(f"No path found from {start} to {target}", "[Pathfinding]")
    return None

def shortest_path_to_value(
    grid: np.ndarray,
    start: Tuple[int, int],
    x: str
) -> Tuple[Optional[List[int]], Optional[Tuple[int, int]]]:
    """
    Find the shortest path from `start` to a cell with value == x on the 2D matrix `grid`.
    Returns:
      - path: list of steps (0=left, 1=right, 2=up, 3=down) if found, otherwise None
      - target_coord: (row, col) of the cell containing x, if not found then None

    Cells with values 'r','w','c' are considered obstacles (cannot be passed through).
    Cells '-1' or 'g' are considered empty cells (can be passed through).
    """
    log(f"Finding shortest path to value '{x}' from {start}", "[Pathfinding]")
    
    # Map dimensions
    n_rows, n_cols = grid.shape

    # Set of obstacle values - Changed 'f' to 'r' for rock
    obstacles = {'r', 'w', 'c', '0', '1', '2', '3', '4', '5', '6'}

    # Convert directions to movement vectors (dr, dc)
    # 0 = move left  -> dc = -1
    # 1 = move right -> dc = +1
    # 2 = move up    -> dr = -1
    # 3 = move down  -> dr = +1
    directions = [
        (0, -1),   # 0: left
        (0, +1),   # 1: right
        (-1, 0),   # 2: up
        (+1, 0)    # 3: down
    ]

    # BFS queue containing ((row, col), path_so_far)
    queue = deque()
    queue.append((start, []))

    # Visited set to avoid infinite loops
    visited = set([start])

    while queue:
        (r, c), path = queue.popleft()

        # If we've reached a cell containing value x, return the result
        if grid[r, c] == x:
            log(f"Found value '{x}' at {(r, c)} with path length {len(path)}", "[Pathfinding]")
            return path, (r, c)

        # Check all 4 adjacent directions
        for move_idx, (dr, dc) in enumerate(directions):
            nr, nc = r + dr, c + dc
            # Check if within map bounds
            if 0 <= nr < n_rows and 0 <= nc < n_cols:
                if (nr, nc) not in visited:
                    cell_value = grid[nr, nc]
                    # If not an obstacle ('r','w','c'), continue BFS
                    if cell_value not in obstacles:
                        visited.add((nr, nc))
                        queue.append(((nr, nc), path + [move_idx]))

    log(f"No path found to value '{x}' from {start}", "[Pathfinding]")
    # If BFS ends without finding a cell with value x
    return None, None

def find_adjacent_resources(grid: np.array, row: int, col: int):
    """Find all resources adjacent to the specified position in the grid.

    Args:
        grid (np.array): The grid to search within.
        row (int): Row index of the grid.
        col (int): Column index of the grid.

    Returns:
        A dictionary of resource types with their positions.
    """
    log(f"Searching for resources around position ({row}, {col})", "[Pathfinding]")
    
    # Dictionary to collect adjacent resources - Changed 'f' to 'r' for rock
    adjacent_resources = {
        'w': [],
        'c': [],
        'r': [],  # Rock instead of food
        's': [],
        'a': [],
        '0': [],
        '1': [],
        '2': [],
        '3': [],
        '4': [],
        '5': [],
        '6': [],
    }

    # Define search area: 5x5 grid centered on (row, col)
    directions = [
        (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2), # row -2
        (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2), # row -1
        (-0, -2), (-0, -1), (-0, 0), (-0, 1), (-0, 2), # row -0
        (+1, -2), (+1, -1), (+1, 0), (+1, 1), (+1, 2), # row +1
        (+2, -2), (+2, -1), (+2, 0), (+2, 1), (+2, 2), # row +2
    ]

    for direction in directions:
        new_row, new_col = row + direction[0], col + direction[1]

        # Check if the new positions are within the grid bounds
        if 0 <= new_row < grid.shape[0] and 0 <= new_col < grid.shape[1]:
            cell_value = str(grid[new_row, new_col])
            if cell_value in adjacent_resources.keys():
                # Rock ('r') is not collectible, so don't add accessible positions for it
                if cell_value in ['s','a','1','2','3','4','5','6']:
                    adjacent_resources[cell_value] = [(new_row, new_col)]
                    log(f"Found {cell_value} at ({new_row}, {new_col})", "[Pathfinding]")
                elif cell_value != 'r':  # Skip rocks as they're not collectible
                    for p in [(new_row-1, new_col), (new_row+1, new_col), (new_row, new_col-1), (new_row, new_col +1)]:
                        if 0 <= p[0] < grid.shape[0] and 0 <= p[1] < grid.shape[1]:
                            if grid[*p] == 'g' or grid[*p] == '-1':
                                adjacent_resources[cell_value] += [p]
                                log(f"Found {cell_value} accessible from {p}", "[Pathfinding]")
                else:
                    # Just log that we found a rock but don't add it to collectible resources
                    log(f"Found rock at ({new_row}, {new_col}) - not collectible", "[Pathfinding]")

    # Log summary of found resources
    for resource_type, positions in adjacent_resources.items():
        if positions and resource_type != 'r':  # Don't count rocks in summary
            log(f"Found {len(positions)} {resource_type} resources", "[Pathfinding]")
            
    return adjacent_resources 