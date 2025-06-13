from dataclasses import dataclass, field

@dataclass
class Event:
    message: str=""

@dataclass
class WinConditionEvent(Event):
    fabric: int = 2
    wood: int = 5
    fabric_to_cotton_ratio: int = 3 

    message: str = "To complete this game, you need to collect 5 units of wood and 2 units of fabric. Every 3 units of cotton can be converted into 1 unit of fabric."
    
    def __post_init__(self):

        # Build the final message using those coordinates, duration, etc.
        self.message = (
            f"To complete this game, you need to collect {self.wood} units of wood and {self.fabric} units of fabric."
            f"Every {self.fabric_to_cotton_ratio} units of cotton can be converted into 1 unit of fabric."
        )
    
@dataclass
class FireEvent(Event):
    message: str = "wood is burning, you can not collect it"
    duration: int = 60
    def __post_init__(self):
        # Build the poison message using those coordinates plus wood/cotton values
        self.message = (
            f"All wood is fire, it take about {self.duration}s "
            f"If you collect it, you will lose all items on hand, go home and paused in {self.duration} seconds"
        )

@dataclass
class RewardPunishmentEvent(Event):
    message: str = "RewardPunishmentEvent"
    duration: int = 60  
    cotton: int = 0
    wood: int = 0
    event_at_rows: list[int] = field(default_factory=lambda: [])
    event_at_cols: list[int] = field(default_factory=lambda: [])

from dataclasses import dataclass, field

# (Assume RewardPunishmentEvent is defined elsewhere)
@dataclass
class RewardPunishmentEvent(Event):
    massage: str = "RewardPunishmentEvent"
    event_at_rows: list[int] = field(default_factory=lambda: [0, 0])
    event_at_cols: list[int] = field(default_factory=lambda: [1, 1])
    icon_name: str = ''

    duration: int = 60
    cotton: int  = 0
    wood: int    = 0



