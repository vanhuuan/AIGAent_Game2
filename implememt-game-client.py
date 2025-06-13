from __future__ import annotations
# # Import Libs

# In[1]:


from dotenv import load_dotenv
from config import Config
from pydantic import BaseModel
import numpy as np
from enums import PlayerStatus
from enum import Enum

import nest_asyncio
nest_asyncio.apply()

test_client = False
test_agent = False
test_graph = True


# In[2]:


load_dotenv('./.env',override=True)


# # Util functions

# ## shortest path from position to position

# In[3]:


def shortest_path(
    grid: np.ndarray,
    start: Tuple[int, int],
    target: Tuple[int, int],
) -> Optional[List[int]]:
    """
    Return a list of moves (0=left, 1=right, 2=up, 3=down) from start to target,
    or None if no path exists. Only cells with value 'g' or '-1' are traversable.
    """
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
            return path

        for dr, dc, mv in MOVES:
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, temp) and not visited[nr][nc]:
                visited[nr][nc] = True
                queue.append((nr, nc, path + [mv]))

    return None


# ## shortest path to value

# In[4]:


import numpy as np
from collections import deque
from typing import List, Tuple, Optional

def shortest_path_to_value(
    grid: np.ndarray,
    start: Tuple[int, int],
    x: str
) -> Tuple[Optional[List[int]], Optional[Tuple[int, int]]]:
    """
    Tìm đường đi ngắn nhất từ `start` tới ô có giá trị == x trên ma trận 2D `grid`.
    Trả về:
      - path: danh sách các bước (0=left, 1=right, 2=up, 3=down) nếu tìm thấy, ngược lại None
      - target_coord: (row, col) của ô chứa x, nếu không tìm thấy thì None

    Các ô có giá trị 'f','w','c' được coi là chướng ngại (không thể đi qua).
    Các ô '-1' hoặc 'g' đều được xem là ô trống (có thể đi qua).
    """
    # Kích thước bản đồ
    n_rows, n_cols = grid.shape


    # Tập các giá trị chướng ngại
    obstacles = {'f', 'w', 'c', '0', '1', '2', '3', '4', '5', '6'}

    # Chuyển hướng thành vector dịch chuyển (dr, dc)
    # 0 = move trái  -> dc = -1
    # 1 = move phải  -> dc = +1
    # 2 = move lên   -> dr = -1
    # 3 = move xuống -> dr = +1
    directions = [
        (0, -1),   # 0: left
        (0, +1),   # 1: right
        (-1, 0),   # 2: up
        (+1, 0)    # 3: down
    ]

    # BFS queue chứa ((row, col), path_so_far)
    queue = deque()
    queue.append((start, []))

    # Tập visited tránh lặp vô hạn
    visited = set([start])

    while queue:
        (r, c), path = queue.popleft()

        # Nếu đã đến ô chứa giá trị x thì trả về kết quả
        if grid[r, c] == x:
            return path, (r, c)

        # Duyệt 4 hướng lân cận
        for move_idx, (dr, dc) in enumerate(directions):
            nr, nc = r + dr, c + dc
            # Kiểm tra trong phạm vi bản đồ
            if 0 <= nr < n_rows and 0 <= nc < n_cols:
                if (nr, nc) not in visited:
                    cell_value = grid[nr, nc]
                    # Nếu không phải chướng ngại ('f','w','c'), tiếp tục BFS
                    if cell_value not in obstacles:
                        visited.add((nr, nc))
                        queue.append(((nr, nc), path + [move_idx]))

    # Nếu BFS kết thúc mà không tìm thấy ô có giá trị x
    return None, None


# ### Find adjacent resources

# In[5]:


import numpy as np

def find_adjacent_resources(grid: np.array, row: int, col: int):
    """Find all resources adjacent to the specified position in the grid.

    Args:
        grid (np.array): The grid to search within.
        row (int): Row index of the grid.
        col (int): Column index of the grid.

    Returns:
        A list of values/resources found at positions adjacent to (row, col).
    """
    # List to collect adjacent resources
    adjacent_resources = {
        'w': [],
        'c': [],
        'f': [],
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

    # Define movement directions: up, down, left, right
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
            cell_value =  str(grid[new_row, new_col])
            if cell_value in adjacent_resources.keys():
                if cell_value in ['s','a','1','2','3','4','5','6']:
                    adjacent_resources[cell_value] = [(new_row, new_col)]
                else:
                    for p in [(new_row-1, new_col), (new_row+1, new_col), (new_row, new_col-1), (new_row, new_col +1)]:
                        if 0 <= p[0] < grid.shape[0] and 0 <= p[1] < grid.shape[1]:
                            if grid[*p] == 'g' or grid[*p] == '-1':
                                adjacent_resources[cell_value] += [p]

    return adjacent_resources


# # Game Client

# In[6]:


from map import Map
import time 
from client import Client


class GameClient(Client):
    def __init__(self, name):
        super().__init__()
        time.sleep(2)  # Wait for the client to connect and receive player info
        self.set_player_name(name)
        self.messages: list = []
        self.entity_positions: dict = {
            'w': [],
            'c': [],
            'f': [],
            's': [],
            'a': [], 
            '0': [],
            '1': [], 
            '2': [], 
            '3': [], 
            '4': [], 
            '5': [], 
            '6': []
        }

    def goto(self, position:tuple[(int,int)]=None):
        player = self.get_player()
        path = shortest_path(player.grid, (player.row, player.col), position)

        # remove loop: just move step by step and recalculate next action
        # while path:
        if (player.row, player.col) == position:
            return
        self.move(path[0])

    def go_home(self):
        player = self.get_player()
        row, col = player.home_row, player.home_col
        self.goto((row, col))

    def collect_wood(self):
        player = self.get_player()
        if player.items_on_hand.count('w') > 0:
            self.go_home()
        else:
            if len(self.entity_positions['w']) > 0:
                wood_position = self.entity_positions['w'][0]
                self.goto(wood_position)
    
    def collect_cotton(self):
        player = self.get_player()
        if player.items_on_hand.count('c') > 0:
            self.go_home()
        else:
            if len(self.entity_positions['c']) > 0:
                cotton_position = self.entity_positions['c'][0]
                self.goto(cotton_position)
    
    def collect_sword(self):
        if len(self.entity_positions['s']) > 0:
            sword_position = self.entity_positions['s'][0]
            self.goto(sword_position)
            player = self.get_player()
            if player.row == sword_position[0] and player.col == sword_position[1]:
                self.entity_positions['s'] = []

    def collect_armor(self):  
        if len(self.entity_positions['a']) > 0:
            armor_position = self.entity_positions['a'][0]
            self.goto(armor_position)
            player = self.get_player()
            if player.row == armor_position[0] and player.col == armor_position[1]:
                self.entity_positions['a'] = []



    def explore(self):
        player = self.get_player()
        row, col = player.row, player.col
        start_pos = (row, col)
        target_value = '-1'

        resources_around = find_adjacent_resources(player.grid, row, col)
        for key in resources_around.keys():
            for value in resources_around[key]:
                if value not in self.entity_positions[key]:
                    self.entity_positions[key] += resources_around[key]

        path, target_coord = shortest_path_to_value(player.grid, start_pos, target_value)
        if path is not None and len(path)>0:
            self.move(path[0])



# In[7]:


if test_client:
    c2 = GameClient('Binh')
    c2.explore()


# # Agents

# ## Import Libs

# In[8]:


from dataclasses import dataclass, field
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from mermaid import Mermaid
# import logfire
from pydantic_ai import Agent, RunContext, ModelRetry
from config import Config
from player import Player
from client_prompting import ClientPrompting
from logs import log

# logfire.configure()  
# logfire.instrument_pydantic_ai()  

import nest_asyncio
nest_asyncio.apply()


# ## Calculate Win Condition Agent

# In[9]:


class EventMessage(BaseModel):
    message: str= ""

class Task(BaseModel):
    task_description: str

class WinCondition(BaseModel):
    wood_need: int
    cotton_need: int
    fabric_to_cotton_ratio: int

    explained: str = ""


class CalculateWinConditionAgent:
    def __init__(self):

        config = Config()

        agent = Agent(
                f'openai:{config.LLM_MODEL}',
                output_type= WinCondition,  
                system_prompt=(ClientPrompting.calculate_win_condition),
                result_retries=5,
            )

        self.agent = agent

        @agent.output_validator
        def validate_output(ctx: RunContext[None], result: WinCondition) -> WinCondition:
            if not result:
                raise ModelRetry(
                    "The result is empty. Please try again.")
            if result.wood_need <= 0:
                raise ModelRetry(
                    "The wood_need must be a positive integer. Please try again.")
            if result.cotton_need <= 0:
                raise ModelRetry(
                    "The cotton_need must be a positive integer. Please try again.")
            if not result.explained:
                raise ModelRetry(
                    "The explained field must not be empty. Please try again.")

            return result

    def calculate(self, message: str) -> WinCondition:
        return self.agent.run_sync(message).output



# ## Test CalculateWinConditionAgent

# In[10]:


if test_agent:
    g = CalculateWinConditionAgent()
    mission_text =  """To complete this game, you need to collect 2 units of wood and 2 units of fabric. Every 3 units of cotton can be converted into 1 unit of fabric."""
    # mission_text
    r = g.calculate(mission_text)
    print(r)


# # Build Graph

# ## Define Graph State

# In[11]:


@dataclass
class Resource:
    num_current_food: int = 0
    num_current_cotton: int = 0
    num_current_fabric: int = 0
    food_need: int = 0
    cotton_need: int = 0
    fabric_to_cotton_ratio: int = 0


# In[12]:


@dataclass
class GameState:
    name: str  
    client: GameClient
    calculate_win_condition_agent: CalculateWinConditionAgent
    resource: Resource 
    states: list[str] = field(default_factory=lambda: [])



# ## Define nodes

# ### Create Game Node

# In[13]:


@dataclass
class CreateGame(BaseNode[GameState]):  
    async def run(self, ctx: GraphRunContext[GameState]) -> TakeMission:
        # Create a new game client
        ctx.state.client = GameClient(ctx.state.name)
        
        ctx.state.states.append("CreateGame")
        return TakeMission()


# ### Take on the mission Node

# In[14]:


@dataclass
class TakeMission(BaseNode[GameState]):
    async def run(self, ctx: GraphRunContext[GameState]) -> WaitingStartGame:
        ctx.state.states.append("TakeMission")

        # Store mission to context

        client = ctx.state.client 

        player = client.get_player()
        while not player.message:
            time.sleep(1)
            player = client.get_player()

        client.messages.append(player.message)

        result = ctx.state.calculate_win_condition_agent.calculate(player.message)

        print(result)

        ctx.state.wood_need = result.wood_need
        ctx.state.cotton_need = result.cotton_need
        ctx.state.fabric_to_cotton_ratio = result.fabric_to_cotton_ratio

        print(f'{ctx.state=}')

        return WaitingStartGame()



# ### Waiting Start Game Node

# In[15]:


@dataclass
class WaitingStartGame(BaseNode[GameState]):
    async def run(self, ctx: GraphRunContext[GameState]) -> Action:

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

        # change state to 

        log('Game started. New identity task to do', '[WaitingStartGame]')

        client.allow_collect_items(items=['w', 'c'])

        return Action(observation_result=ObservationResult.EXPLORE)


# ### Action Node

# In[16]:


class ObservationResult(Enum):
    GET_MORE_WOOD = 'Get more wood'
    GET_MORE_COTTON = 'Get more cotton'
    COLLECT_SWORD = 'Collect sword'
    COLLECT_ARMOR = 'Collect armor'
    EXPLORE = 'Explore'
    

@dataclass
class Action(BaseNode[GameState]):
    observation_result: ObservationResult = ObservationResult.EXPLORE
    async def run(self, ctx: GraphRunContext[GameState]) -> Observeration | End:

        time.sleep(1)

        ctx.state.states.append(self.observation_result)
        client = ctx.state.client

        if self.observation_result == ObservationResult.GET_MORE_WOOD:
            client.collect_wood()
            return Observeration(action_result="exploreration")
        if self.observation_result == ObservationResult.GET_MORE_COTTON:
            client.collect_cotton()
            return Observeration(action_result="exploreration")
        if self.observation_result == ObservationResult.COLLECT_SWORD:
            client.collect_sword()
            return Observeration(action_result="exploreration")
        if self.observation_result == ObservationResult.COLLECT_ARMOR:
            client.collect_armor()
            return Observeration(action_result="exploreration")
        if self.observation_result == ObservationResult.EXPLORE:
            client.explore()
            return Observeration(action_result="exploreration")
        if self.observation_result == "WIN":
            log('Player win the game', '[Action]')
            return End(f"Player win the game")

# ### Observeration Node

# In[17]:


@dataclass
class Observeration(BaseNode[GameState]):
    action_result: str = ""
    async def run(self, ctx: GraphRunContext[GameState]) -> Action:

        # Check if new message from server
        client = ctx.state.client
        player = client.get_player()
        if player.message not in client.messages:
            client.messages.append(player.message)
            log(f'TODO:  Process new message: {player.message}', '[Observeration]')
            return Action(player.message)

        elif self.action_result == "exploreration":
            # If the action result is exploreration, we continue to explore
            
            # determine the next action based on the current state
            if player.status == PlayerStatus.WIN:
                log('Player win the game', '[Observeration]')
                return Action(observation_result="WIN")
            
            current_wood_need = ctx.state.wood_need - player.store.count('w')
            current_cotton_need = ctx.state.cotton_need - player.store.count('c') * ctx.state.fabric_to_cotton_ratio
            position_of_woods = client.entity_positions['w']
            position_of_cottons = client.entity_positions['c']
            position_of_sword = client.entity_positions['s']
            position_of_armor = client.entity_positions['a']

            log(f'{current_wood_need=}', '[Observeration]' )
            log(f'{current_cotton_need=}', '[Observeration]' )

            # Uu tien thu thập sword
            if len(position_of_sword) > 0:
                return Action(observation_result=ObservationResult.COLLECT_SWORD)
            
            # Uu tien thu thập armor
            if len(position_of_armor) > 0:
                return Action(observation_result=ObservationResult.COLLECT_ARMOR) 
            
            # Uu tien thu thập gỗ
            if current_wood_need > 0 and len(position_of_woods) > 0:
                return Action(observation_result=ObservationResult.GET_MORE_WOOD)
            
            # Uu tien thu thập cotton
            if current_cotton_need > 0 and len(position_of_cottons) > 0:
                return Action(observation_result=ObservationResult.GET_MORE_COTTON)
            
        return Action(observation_result=ObservationResult.EXPLORE)  


# ## Draw Graph

# In[18]:


game_graph = Graph(
    nodes=[
        CreateGame, 
        TakeMission, 
        WaitingStartGame, 
        Observeration, 
        Action
    ]
)
Mermaid(game_graph.mermaid_code(start_node=CreateGame))


# # Test Game

# In[19]:


async def create_client_game(name: str):
    state = GameState(
        name = name,
        client= None, 
        calculate_win_condition_agent= CalculateWinConditionAgent(),
        resource= Resource()
    )  
    await game_graph.run(CreateGame(), state=state) 

import asyncio
import nest_asyncio
nest_asyncio.apply()


# In[ ]:


if test_graph:
    from faker import Faker
    fake = Faker("vi_VN")
    
    asyncio.run(create_client_game(fake.last_name())) 


# In[ ]:




