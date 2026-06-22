from simulator.actuators.actuator import Actuator
from simulator.DTC.DTCManager import DTCManager
security_level: str
security_key: str
session_level: str
# security_expire_time: int

current_gear = 'n'
time_held = 0.0
refresh_rate = 0.1
current_speed = 0.0
prev_speed = 0.0          # for acceleration calculation
baseline_speed = 0.0
was_accelerating = False
# ENGINE VARIABLES
current_rpm = 800.0
IDLE_RPM = 800.0
MAX_RPM = 6500.0
gear_grind_warning = False
# FUEL & DISTANCE VARIABLES
instant_fuel_rate = 0.0      # mL per second
total_fuel_ml = 0.0          # Total fuel burned this trip
remaining_fuel_ml = 400  # Load from persistence file
distance_km = 0.0            # Distance covered this trip
fuel_save_counter = 0        # tick counter for periodic fuel save
ambient_temp = 25
coolant_temp = ambient_temp
oil_temp = ambient_temp       # oil lags ~10°C behind coolant
target_temp = 90.0
battery_voltage = 12.6        # volts
headlamp_switch = False

#Actuators
radiator_fan = Actuator("Radiator Fan")
fuel_pump = Actuator("Fuel Pump")
head_lamp = Actuator("Headlamp")
door_lock = Actuator("Door Lock")

#Firmware
upload_active = False
upload_offset = 0

firmware_image = bytearray(
    b"Simulator Firmware v1.0"
)

#DTC Manager

