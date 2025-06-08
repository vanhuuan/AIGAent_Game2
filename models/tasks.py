from pydantic import BaseModel, ConfigDict
from typing import List

class Position(BaseModel):
    row: int
    col: int

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

class WinCondition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    wood_need: int
    cotton_need: int
    player: object  # This will be Player type, defined in player.py

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