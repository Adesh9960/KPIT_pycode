from dataclasses import dataclass, field
from enum import Enum
class Control(Enum):
    ECU = 0  # Return Control To ECU
    RESET = 1  # Reset To Default
    FREEZE = 2 # Freeze Current State
    ADJUST = 3  # Short Term Adjustment
@dataclass
class Actuator:
    name: str
    control: Control = Control.ECU
    state: bool = False
    
