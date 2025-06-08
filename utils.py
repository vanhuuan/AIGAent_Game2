import pickle
import struct
import pygame
import socket
import numpy as np
from collections import deque

def send(sock, data):
    if sock._closed:
        return
    data = pickle.dumps(data)
    length = struct.pack('!I', len(data))  # (4 byte)
    sock.sendall(length)                   # 
    sock.sendall(data)  # 
                       
def receive(sock):
    try:
        # length_data = sock.recv(4, socket.MSG_DONTWAIT)
        length_data = sock.recv(4)
        if not length_data:
            return None
        length = struct.unpack('!I', length_data)[0]

        data = b''
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                break
            data += packet

        obj = pickle.loads(data)
        return obj
    except:
        return None

def load_image(image_path,  width=None, height=None):
    """Displays an image at the given position and size using Pygame."""
    # Load the image
    image = pygame.image.load(image_path)
    if width and height:
        image = pygame.transform.scale(image, (width, height))
    return image

    
def display_image(screen, image, x, y):
    # Scale the image to the desired size
    # Blit (draw) the image onto the screen at the specified position
    screen.blit(image, (x, y))


def draw_text(screen, x, y, text, color, bg_color, font, padding=10, draw_box=True):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    
    # Add padding to the background box
    box_rect = pygame.Rect(x, y, text_rect.width + 2 * padding, text_rect.height + 2 * padding)
    
    # Draw background box
    if draw_box:
        pygame.draw.rect(screen, bg_color, box_rect)
    
    # Blit text onto the screen centered within the box
    screen.blit(text_surface, (x + padding, y + padding))
    return box_rect

def draw_energy(screen, text, energine: int = 0, energine_max: int = 10,
                x: int = 20, y: int = 20, width: int = 15, height: int = 10, 
                spacing: int = 5, color=(0, 0, 0), bg_color=(50, 50, 50), font_size=22):
    
    box = draw_text(screen, x + spacing, y-2*spacing, 
                    text, color, bg_color, 
                    pygame.font.SysFont('', font_size, bold=False), spacing,
                    False )
    x += box.width + spacing
    for i in range(energine):
        rect_x = x + i * (width + spacing)
        rect = pygame.Rect(rect_x, y, width, height)
        pygame.draw.rect(screen, bg_color, rect, border_radius=4)
        inner_rect = rect.inflate(-4, -4)
        pygame.draw.rect(screen, color, inner_rect, border_radius=4)
    
    for i in range(energine, energine_max):
        rect_x = x + i * (width + spacing)
        rect = pygame.Rect(rect_x, y, width, height)
        pygame.draw.rect(screen, bg_color, rect, border_radius=4)
        inner_rect = rect.inflate(-4, -4)
        pygame.draw.rect(screen, (255,255,255), inner_rect, border_radius=4)

# Move step (dr, dc, move_code)
MOVES = [
    (0, -1, 0),  # left
    (0, 1,  1),  # right
    (-1, 0, 2),  # up
    (1, 0,  3),  # down
]

def find_resource(grid: np.ndarray, resource: str) -> list:
    """
    Find cells containing a specific resource
    
    Args:
        grid: 2D grid representing the game map
        resource: Resource identifier ('f', 'w', 'c', -1, etc.)
        
    Returns:
        List of dictionaries with row and col positions
    """
    pair_of_row_cols = np.where(grid == resource)
    
    result = []
    if pair_of_row_cols:
        for r, c in zip(pair_of_row_cols[0], pair_of_row_cols[1]):
            result.append({'row': int(r), 'col': int(c)})    
    return result

def is_valid(r, c, grid):
    """
    Check if a position is valid for movement
    
    Args:
        r: Row index
        c: Column index
        grid: 2D grid representing the game map
        
    Returns:
        Boolean indicating if the position is valid
    """
    h, w = grid.shape
    return 0 <= r < h and 0 <= c < w and grid[r, c] in ('g', '-1')

def shortest_path(start, end, grid):
    """
    Find the shortest path from start to end
    
    Args:
        start: Tuple of (row, col) for starting position
        end: Tuple of (row, col) for ending position
        grid: 2D grid representing the game map
        
    Returns:
        List of movement directions (0: left, 1: right, 2: up, 3: down)
    """
    start_row, start_col = start
    end_row, end_col = end
    
    # Queue for BFS
    queue = deque([(start_row, start_col, [])])
    visited = set([(start_row, start_col)])
    
    while queue:
        row, col, path = queue.popleft()
        
        # If we reached the destination
        if row == end_row and col == end_col:
            return path
        
        # Try all four directions
        for dr, dc, move_code in MOVES:
            new_row, new_col = row + dr, col + dc
            
            if is_valid(new_row, new_col, grid) and (new_row, new_col) not in visited:
                visited.add((new_row, new_col))
                new_path = path + [move_code]
                queue.append((new_row, new_col, new_path))
    
    # No path found
    return []

    

