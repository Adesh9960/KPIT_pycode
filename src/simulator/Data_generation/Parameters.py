import time
import os
import sys
import requests
import simulator.Data_generation.actuators as actuators
from .display_data import display_stats
try:
    import keyboard
except ImportError:
    print("Please install the keyboard module first by running: pip install keyboard")
    sys.exit()

from encoder.encoder import encode_frame
import simulator.main as main

# --- CONSTANTS & CONFIG ---
FUEL_SAVE_FILE = "fuel_save.txt"
MAX_FUEL_ML = 40000.0  # 40 Liters

# Physics Dictionary
gear_physics = {
    'n': {'max': 0,   'idle': 0,  'name': 'Neutral',  'k': 0},
    '1': {'max': 40,  'idle': 8,  'name': '1st Gear', 'k': 1.2},
    '2': {'max': 90,  'idle': 15, 'name': '2nd Gear', 'k': 0.6},
    '3': {'max': 135, 'idle': 25, 'name': '3rd Gear', 'k': 0.15},
    '4': {'max': 170, 'idle': 35, 'name': '4th Gear', 'k': 0.08},
    '5': {'max': 190, 'idle': 45, 'name': '5th Gear', 'k': 0.04}
}
# headlamp switch timeout
headlamp_switch_timeout = time.time()

def load_fuel_state():
    """Loads the remaining fuel from a save file to simulate a real physical tank."""
    if os.path.exists(FUEL_SAVE_FILE):
        try:
            with open(FUEL_SAVE_FILE, 'r') as f:
                return float(f.read().strip())
        except Exception:
            return MAX_FUEL_ML
    return MAX_FUEL_ML

def save_fuel_state(fuel_ml):
    """Saves the fuel level so the engine remembers it on next startup."""
    with open(FUEL_SAVE_FILE, 'w') as f:
        f.write(str(fuel_ml))

def get_live_ambient_temp():
    print("Fetching live weather data for engine cold-start...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=18.52&longitude=73.85&current_weather=true"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        live_temp = data['current_weather']['temperature']
        print(f"Weather fetched! Starting ambient temperature is {live_temp}°C")
        return float(live_temp)
    except Exception:
        print("Warning: Could not connect to weather satellite. Defaulting to 25.0°C")
        return 25.0

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_gear(is_clutch_down):
            # Check for gear changes
        for g in ['n', '1', '2', '3', '4', '5']:
            if keyboard.is_pressed(g) and main.current_gear != g:
                if is_clutch_down:
                    main.current_gear = g
                    main.time_held = 0.0
                    if main.current_speed > 0:
                        # Slight momentum loss during shift
                        main.current_speed = max(0.0, main.current_speed - 1.5)
                        main.baseline_speed = main.current_speed
                    main.gear_grind_warning = False
                else:
                    main.gear_grind_warning = True

def handle_rpm_physics(is_clutch_down, is_accelerating, physics):
        if main.remaining_fuel_ml <= 0 and main.current_speed == 0:
            main.current_rpm = 0.0  # Out of gas AND stopped — engine dead
        elif is_clutch_down or main.current_gear == 'n':
            if is_accelerating and main.remaining_fuel_ml > 0:
                main.current_rpm = min(main.MAX_RPM, main.current_rpm + (4000.0 * main.refresh_rate))
            else:
                main.current_rpm = max(main.IDLE_RPM if main.remaining_fuel_ml > 0 else 0, main.current_rpm - (3000.0 * main.refresh_rate))
        else:
            if main.current_speed == 0:
                # Stopped in gear: engine holds idle (stall check done separately in alerts)
                main.current_rpm = main.IDLE_RPM
            else:
                speed_ratio = main.current_speed / physics['max']
                main.current_rpm = max(main.IDLE_RPM, 1000 + (speed_ratio * (main.MAX_RPM - 1000)))

def handle_fuel_physics(is_clutch_down, is_accelerating, physics):
        if main.current_rpm == 0:
            main.instant_fuel_rate = 0.0
        elif main.remaining_fuel_ml <= 0:
            main.instant_fuel_rate = 0.0
        elif is_clutch_down or main.current_gear == 'n':
            if is_accelerating:
                main.instant_fuel_rate = (main.current_rpm / main.MAX_RPM) * 3.0
            else:
                main.instant_fuel_rate = 0.5
        else:
            if is_accelerating:
                engine_load = (main.current_speed / max(1, physics['max'])) + 0.5
                main.instant_fuel_rate = engine_load * (main.current_rpm / main.MAX_RPM) * 12.0
            else:
                if main.current_rpm > main.IDLE_RPM + 150:
                    main.instant_fuel_rate = 0.0  # Coasting in gear
                else:
                    main.instant_fuel_rate = 0.5

        # Apply consumption to both total trip and actual tank
        consumed_this_tick = main.instant_fuel_rate * main.refresh_rate
        main.total_fuel_ml += consumed_this_tick
        main.remaining_fuel_ml = max(0.0, main.remaining_fuel_ml - consumed_this_tick)

def handle_speed(is_clutch_down, is_accelerating, physics, is_braking):
        drag_deceleration = (main.current_speed * 0.05) * main.refresh_rate

        if is_braking:
            # Exponential decay: scrubs more speed at higher speeds.
            brake_force = (main.current_speed * 0.8 + 10.0) * main.refresh_rate
            main.current_speed = max(0.0, main.current_speed - brake_force)
            main.time_held = 0.0

        elif is_accelerating and not is_clutch_down and main.current_gear != 'n':
            if main.remaining_fuel_ml > 0:
                main.time_held += main.refresh_rate
                acceleration = physics['k'] * (physics['max'] - main.current_speed)
                main.current_speed += acceleration * main.refresh_rate

        else:
            main.time_held = 0.0
            idle_speed = physics['idle']

            if main.current_gear == 'n' or is_clutch_down:
                drag_deceleration = (main.current_speed * 0.05) * main.refresh_rate
                main.current_speed = max(0.0, main.current_speed - drag_deceleration)
            else:
                if main.current_speed > idle_speed:
                    engine_braking = (main.current_speed * 0.05 + physics['k'] * 5) * main.refresh_rate
                    main.current_speed = max(float(idle_speed), main.current_speed - engine_braking)
                elif main.current_speed < idle_speed and main.current_speed > 0:
                    ecu_recovery = 2.0 * main.refresh_rate
                    # If out of fuel, ECU can't recover speed!
                    if main.remaining_fuel_ml > 0:
                        main.current_speed = min(float(idle_speed), main.current_speed + ecu_recovery)
                    else:
                        main.current_speed = max(0.0, main.current_speed - drag_deceleration)



def handle_battery_and_temp(is_clutch_down, is_accelerating, physics):
    if is_accelerating and main.current_gear != 'n' and not is_clutch_down and main.remaining_fuel_ml > 0:
            engine_load = (main.current_speed / max(1, physics['max'])) + 0.5
            heat_input = engine_load * 2.0 * main.refresh_rate
    else:
        if main.current_rpm > main.IDLE_RPM + 1000 and is_clutch_down:
            heat_input = 1.5 * main.refresh_rate
        else:
            heat_input = 0.3 * main.refresh_rate

        main.coolant_temp += heat_input

    if main.coolant_temp > main.target_temp:
        cooling_effect = ((main.coolant_temp - main.target_temp) * 0.2 + (main.current_speed * 0.01)) * main.refresh_rate
        main.coolant_temp -= cooling_effect
    else:
        ambient_cooling = ((main.coolant_temp - main.ambient_temp) * 0.01) * main.refresh_rate
        main.coolant_temp -= ambient_cooling

        # Oil temp lags coolant by ~10°C and rises/falls more slowly
    oil_target = main.coolant_temp + 10.0
    main.oil_temp += (oil_target - main.oil_temp) * 0.02 * main.refresh_rate

        # Battery: 14.2V when alternator is spinning (rpm > idle+50), else drains slowly
    if main.current_rpm > main.IDLE_RPM + 50:
        main.battery_voltage = min(14.4, main.battery_voltage + 0.01 * main.refresh_rate)
    else:
        main.battery_voltage = max(11.8, main.battery_voltage - 0.005 * main.refresh_rate)

def get_engine_state(is_clutch_down, is_accelerating, physics, is_braking):
        if main.remaining_fuel_ml <= 0 and main.current_speed == 0:
            engine_state = "DEAD"
        elif main.current_rpm <= 100 and main.current_gear != 'n' and not is_clutch_down:
            engine_state = "STALLED"
        elif is_braking:
            engine_state = "BRAKING"
        elif is_clutch_down:
            engine_state = "CLUTCH_OUT"
        elif is_accelerating and main.current_gear != 'n':
            engine_state = "ACCELERATING"
        elif main.current_gear != 'n' and main.current_speed > physics['idle']:
            engine_state = "ENGINE_BRAKING"
        elif main.current_gear != 'n' and main.current_speed == physics['idle']:
            engine_state = "IDLE_CREEP"
        elif main.current_speed > 0:
            engine_state = "COASTING"
        else:
            engine_state = "IDLE"

def get_telemetry_entry(is_clutch_down, physics):
        accel_ms2 = round((main.current_speed - main.prev_speed) / 0.1, 2)  # km/h per 0.1s -> approx m/s^2
        fuel_pct = round((main.remaining_fuel_ml / MAX_FUEL_ML) * 100.0, 1)

        # Engine load: how hard the engine is working (0.0-1.5 range mapped to 0-100%)
        if main.current_gear != 'n' and not is_clutch_down and main.current_speed > 0:
            raw_load = (main.current_speed / max(1, physics['max'])) + 0.5
        else:
            raw_load = main.current_rpm / main.MAX_RPM
        engine_load_pct = round(min(100.0, raw_load / 1.5 * 100.0), 1)

        # Throttle %: fraction of max possible fuel rate at current rpm
        max_possible_rate = (raw_load * (main.current_rpm / main.MAX_RPM) * 12.0) if main.current_rpm > 0 else 1.0
        throttle_pct = round(min(100.0, (main.instant_fuel_rate / max(0.01, max_possible_rate)) * 100.0), 1)

        rev_limiter = 1 if main.current_rpm >= main.MAX_RPM - 100 else 0
        stall_risk = 1 if (main.current_rpm < main.IDLE_RPM + 300 and main.current_gear != 'n' and not is_clutch_down and main.current_speed < 5) else 0

        return {
            "Speed_kmh": int(main.current_speed),
            "Engine_RPM": int(main.current_rpm),
            "Coolant_Temp_C": round(main.coolant_temp, 2),
            "Oil_Temp_C": round(main.oil_temp, 2),
            "Ambient_Temp_C": round(main.ambient_temp, 1),
            "Fuel_Rate_mL_s": round(main.instant_fuel_rate, 2),
            "Remaining_Fuel_L": round(main.remaining_fuel_ml / 1000, 3),
            "Fuel_Pct": fuel_pct,
            "Distance_km": round(main.distance_km, 4),
            "Accel_ms2": accel_ms2,
            "Engine_Load_Pct": engine_load_pct,
            "Throttle_Pct": throttle_pct,
            "Gear_Num": 0 if main.current_gear == 'n' else int(main.current_gear),
            "Battery_V": round(main.battery_voltage, 2),
            "Tyre_P_FL": 32.1,
            "Tyre_P_FR": 32.0,
            "Tyre_P_RL": 31.8,
            "Tyre_P_RR": 31.9,
            "Stall_Risk": stall_risk,
            #actuators
            "Head_Lamp": main.head_lamp,
            "Radiator_Fan": main.radiator_fan,
            "Fuel_pump": main.fuel_pump
        }

def run_vehicle_simulator():
    global headlamp_switch_timeout
    main.remaining_fuel_ml = load_fuel_state()
    main.ambient_temp = get_live_ambient_temp()
    main.coolant_temp = main.ambient_temp
    main.oil_temp = main.ambient_temp 
    clear_screen()
    print("Starting Continuous Physics Engine with Direct Encoder Feed...")
    time.sleep(1)

    while True:
        # Quit and Save Data
        if keyboard.is_pressed('q'):
            save_fuel_state(main.remaining_fuel_ml)
            clear_screen()
            print(f"Engine Turned Off. Trip Fuel Consumed: {main.total_fuel_ml:.1f} mL")
            print(f"Trip Distance: {main.distance_km:.3f} km")
            print(f"Fuel state saved. Remaining: {(main.remaining_fuel_ml/1000):.2f} Liters.")
            break

        # Refuel Logic
        if keyboard.is_pressed('r'):
            main.remaining_fuel_ml = MAX_FUEL_ML

        # Read all pedals
        is_accelerating = keyboard.is_pressed('space')
        is_braking = keyboard.is_pressed('b')
        is_clutch_down = keyboard.is_pressed('c')
        if keyboard.is_pressed('o') and time.time() - headlamp_switch_timeout > 0.1:
            main.headlamp_switch = not main.headlamp_switch
            headlamp_switch_timeout = time.time()

        check_gear(is_clutch_down)

        physics = gear_physics[main.current_gear]

        if is_accelerating and not main.was_accelerating:
            main.baseline_speed = main.current_speed
        main.was_accelerating = is_accelerating

        # Track previous speed for acceleration calculation (before physics update)
        main.prev_speed = main.current_speed

        # --- SPEED PHYSICS & EXPONENTIAL BRAKING ---
        handle_speed(is_clutch_down, is_accelerating, physics, is_braking)

        # Calculate Distance (km/h converted to km/s multiplied by time)
        main.distance_km += (main.current_speed / 3600.0) * main.refresh_rate

        # --- RPM PHYSICS ---
        handle_rpm_physics(is_clutch_down, is_accelerating, physics)

        # --- FUEL CONSUMPTION LOGIC ---
        handle_fuel_physics(is_clutch_down, is_accelerating, physics)

        # --- THERMODYNAMICS ---
        handle_battery_and_temp(is_clutch_down, is_accelerating, physics)

        actuators.update_fuel_pump()
        actuators.update_headlamp()
        actuators.update_radiator_fan()
        
        # Engine state as single enum string
        engine_state = get_engine_state(is_clutch_down, is_accelerating,physics, is_braking)

        #send data to encoder stage
        telemetry_row = get_telemetry_entry(is_clutch_down, physics)
        # encode_frame(telemetry_row)

        # reliable tick-based fuel save instead of time.time() modulo
        main.fuel_save_counter += 1
        if main.fuel_save_counter >= 50:
            save_fuel_state(main.remaining_fuel_ml)
            main.fuel_save_counter = 0

        display_stats(is_clutch_down, is_accelerating, physics, is_braking, engine_state)
        time.sleep(main.refresh_rate)

if __name__ == "__main__":
    run_vehicle_simulator()