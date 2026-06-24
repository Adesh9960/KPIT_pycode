from .actuator import Actuator
import simulator.main as main
ACTUATORS_DB = {
    0x1001: main.radiator_fan,
    0x1002: main.fuel_pump,
    0x1003: main.head_lamp,
    0x1004: main.door_lock,
}