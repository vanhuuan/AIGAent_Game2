from pydantic import BaseModel, ConfigDict

class FindContext(BaseModel):
    """Context for resource finding operations"""
    player: object  # This will be Player type, defined in player.py
    model_config = ConfigDict(arbitrary_types_allowed=True) 