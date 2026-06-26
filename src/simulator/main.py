from simulator.actuators.actuator import Actuator
import simulator.uds.Session as Session
security_level: str = 0
security_key: str = None
session_level: str = Session.DEFAULT_SESSION
import math
from simulator.DTC.DTCManager import DTCManager

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

#STEERING
steering_angle = 0.0                 # radians
MAX_STEERING = math.radians(35)      # ±35°
STEER_RATE = math.radians(90)        # degrees/sec
CENTER_RATE = math.radians(120)      # self-centering
WHEELBASE = 2.7                      # m
lateral_accel = 0
#Tyres
tyre_temps = [25, 25, 25, 25]

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

#STEERING DIRECTION
STRAIGHT = 0
LEFT = 1
RIGHT = 2

steering_direction = STRAIGHT

#DTC MANAGER
dtc_manager = DTCManager()
