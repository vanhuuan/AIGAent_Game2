from dataclasses import dataclass

@dataclass
class Config:
    # GAME DPEED
    FPS:float=2.0
    GAME_DURATION:int=60*60 # in minutes

    
    # PLAYER
    
    
    # DEAD_TIME
    PAUSED_TIME:int=30 # in seconds
    
    # STORE
    MAX_STORAGE_CAPACITY = 50
    
    # Wind condition
    WIND_N_WOOD = 5
    WIND_N_FABRIC = 3
    
    # MAP
    N_ROW:int = 18
    N_COL:int = 32
    CELL_SIZE: int = 42
    OPEN_CELL: int = 4
    
    MAP_NUMBER_FOOT:int = 2
    MAP_NUMBER_WOOD:int = 2
    MAP_NUMBER_COTTON:int = 2
    MAP_NUMBER_AMOR:int = 5
    MAP_NUMBER_SWORD:int = 5

    LLM_MODEL:str='gpt-4o-mini'

    # Check client timeout
    CHECK_CLIENT_TIMEOUT:bool = True
    CLIENT_PING_TIMEOUT:int = 10  # seconds




