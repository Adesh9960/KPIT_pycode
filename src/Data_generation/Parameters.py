import time
import os
import sys
import requests

try:
    import keyboard
except ImportError:
    print("Please install the keyboard module first by running: pip install keyboard")
    sys.exit()

from encoder.encoder import encode_frame

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

def main():
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
    remaining_fuel_ml = load_fuel_state()  # Load from persistence file
    distance_km = 0.0            # Distance covered this trip
    fuel_save_counter = 0        # tick counter for periodic fuel save

    ambient_temp = get_live_ambient_temp()

    coolant_temp = ambient_temp
    oil_temp = ambient_temp       # oil lags ~10°C behind coolant
    target_temp = 90.0
    battery_voltage = 12.6        # volts

    clear_screen()
    print("Starting Continuous Physics Engine with Direct Encoder Feed...")
    time.sleep(1)

    while True:
        # Quit and Save Data
        if keyboard.is_pressed('q'):
            save_fuel_state(remaining_fuel_ml)
            clear_screen()
            print(f"Engine Turned Off. Trip Fuel Consumed: {total_fuel_ml:.1f} mL")
            print(f"Trip Distance: {distance_km:.3f} km")
            print(f"Fuel state saved. Remaining: {(remaining_fuel_ml/1000):.2f} Liters.")
            break

        # Refuel Logic
        if keyboard.is_pressed('r'):
            remaining_fuel_ml = MAX_FUEL_ML

        # Read all pedals
        is_accelerating = keyboard.is_pressed('space')
        is_braking = keyboard.is_pressed('b')
        is_clutch_down = keyboard.is_pressed('c')

        gear_grind_warning = False

        # Check for gear changes
        for g in ['n', '1', '2', '3', '4', '5']:
            if keyboard.is_pressed(g) and current_gear != g:
                if is_clutch_down:
                    current_gear = g
                    time_held = 0.0
                    if current_speed > 0:
                        # Slight momentum loss during shift
                        current_speed = max(0.0, current_speed - 1.5)
                        baseline_speed = current_speed
                else:
                    gear_grind_warning = True

        physics = gear_physics[current_gear]

        if is_accelerating and not was_accelerating:
            baseline_speed = current_speed
        was_accelerating = is_accelerating

        # Track previous speed for acceleration calculation (before physics update)
        prev_speed = current_speed

        # --- SPEED PHYSICS & EXPONENTIAL BRAKING ---
        drag_deceleration = (current_speed * 0.05) * refresh_rate

        if is_braking:
            # Exponential decay: scrubs more speed at higher speeds.
            brake_force = (current_speed * 0.8 + 10.0) * refresh_rate
            current_speed = max(0.0, current_speed - brake_force)
            time_held = 0.0

        elif is_accelerating and not is_clutch_down and current_gear != 'n':
            if remaining_fuel_ml > 0:
                time_held += refresh_rate
                acceleration = physics['k'] * (physics['max'] - current_speed)
                current_speed += acceleration * refresh_rate

        else:
            time_held = 0.0
            idle_speed = physics['idle']

            if current_gear == 'n' or is_clutch_down:
                drag_deceleration = (current_speed * 0.05) * refresh_rate
                current_speed = max(0.0, current_speed - drag_deceleration)
            else:
                if current_speed > idle_speed:
                    engine_braking = (current_speed * 0.05 + physics['k'] * 5) * refresh_rate
                    current_speed = max(float(idle_speed), current_speed - engine_braking)
                elif current_speed < idle_speed and current_speed > 0:
                    ecu_recovery = 2.0 * refresh_rate
                    # If out of fuel, ECU can't recover speed!
                    if remaining_fuel_ml > 0:
                        current_speed = min(float(idle_speed), current_speed + ecu_recovery)
                    else:
                        current_speed = max(0.0, current_speed - drag_deceleration)

        # Calculate Distance (km/h converted to km/s multiplied by time)
        distance_km += (current_speed / 3600.0) * refresh_rate

        # --- RPM PHYSICS ---
        if remaining_fuel_ml <= 0 and current_speed == 0:
            current_rpm = 0.0  # Out of gas AND stopped — engine dead
        elif is_clutch_down or current_gear == 'n':
            if is_accelerating and remaining_fuel_ml > 0:
                current_rpm = min(MAX_RPM, current_rpm + (4000.0 * refresh_rate))
            else:
                current_rpm = max(IDLE_RPM if remaining_fuel_ml > 0 else 0, current_rpm - (3000.0 * refresh_rate))
        else:
            if current_speed == 0:
                # Stopped in gear: engine holds idle (stall check done separately in alerts)
                current_rpm = IDLE_RPM
            else:
                speed_ratio = current_speed / physics['max']
                current_rpm = max(IDLE_RPM, 1000 + (speed_ratio * (MAX_RPM - 1000)))

        # --- FUEL CONSUMPTION LOGIC ---
        if current_rpm == 0:
            instant_fuel_rate = 0.0
        elif remaining_fuel_ml <= 0:
            instant_fuel_rate = 0.0
        elif is_clutch_down or current_gear == 'n':
            if is_accelerating:
                instant_fuel_rate = (current_rpm / MAX_RPM) * 3.0
            else:
                instant_fuel_rate = 0.5
        else:
            if is_accelerating:
                engine_load = (current_speed / max(1, physics['max'])) + 0.5
                instant_fuel_rate = engine_load * (current_rpm / MAX_RPM) * 12.0
            else:
                if current_rpm > IDLE_RPM + 150:
                    instant_fuel_rate = 0.0  # Coasting in gear
                else:
                    instant_fuel_rate = 0.5

        # Apply consumption to both total trip and actual tank
        consumed_this_tick = instant_fuel_rate * refresh_rate
        total_fuel_ml += consumed_this_tick
        remaining_fuel_ml = max(0.0, remaining_fuel_ml - consumed_this_tick)

        # --- THERMODYNAMICS ---
        if is_accelerating and current_gear != 'n' and not is_clutch_down and remaining_fuel_ml > 0:
            engine_load = (current_speed / max(1, physics['max'])) + 0.5
            heat_input = engine_load * 2.0 * refresh_rate
        else:
            if current_rpm > IDLE_RPM + 1000 and is_clutch_down:
                heat_input = 1.5 * refresh_rate
            else:
                heat_input = 0.3 * refresh_rate

        coolant_temp += heat_input

        if coolant_temp > target_temp:
            cooling_effect = ((coolant_temp - target_temp) * 0.2 + (current_speed * 0.01)) * refresh_rate
            coolant_temp -= cooling_effect
        else:
            ambient_cooling = ((coolant_temp - ambient_temp) * 0.01) * refresh_rate
            coolant_temp -= ambient_cooling

        # Oil temp lags coolant by ~10°C and rises/falls more slowly
        oil_target = coolant_temp + 10.0
        oil_temp += (oil_target - oil_temp) * 0.02 * refresh_rate

        # Battery: 14.2V when alternator is spinning (rpm > idle+50), else drains slowly
        if current_rpm > IDLE_RPM + 50:
            battery_voltage = min(14.4, battery_voltage + 0.01 * refresh_rate)
        else:
            battery_voltage = max(11.8, battery_voltage - 0.005 * refresh_rate)

        # --- DERIVED SIGNALS ---
        accel_ms2 = round((current_speed - prev_speed) / 0.1, 2)  # km/h per 0.1s -> approx m/s^2
        fuel_pct = round((remaining_fuel_ml / MAX_FUEL_ML) * 100.0, 1)

        # Engine load: how hard the engine is working (0.0-1.5 range mapped to 0-100%)
        if current_gear != 'n' and not is_clutch_down and current_speed > 0:
            raw_load = (current_speed / max(1, physics['max'])) + 0.5
        else:
            raw_load = current_rpm / MAX_RPM
        engine_load_pct = round(min(100.0, raw_load / 1.5 * 100.0), 1)

        # Throttle %: fraction of max possible fuel rate at current rpm
        max_possible_rate = (raw_load * (current_rpm / MAX_RPM) * 12.0) if current_rpm > 0 else 1.0
        throttle_pct = round(min(100.0, (instant_fuel_rate / max(0.01, max_possible_rate)) * 100.0), 1)

        rev_limiter = 1 if current_rpm >= MAX_RPM - 100 else 0
        stall_risk = 1 if (current_rpm < IDLE_RPM + 300 and current_gear != 'n' and not is_clutch_down and current_speed < 5) else 0

        # Engine state as single enum string
        if remaining_fuel_ml <= 0 and current_speed == 0:
            engine_state = "DEAD"
        elif current_rpm <= 100 and current_gear != 'n' and not is_clutch_down:
            engine_state = "STALLED"
        elif is_braking:
            engine_state = "BRAKING"
        elif is_clutch_down:
            engine_state = "CLUTCH_OUT"
        elif is_accelerating and current_gear != 'n':
            engine_state = "ACCELERATING"
        elif current_gear != 'n' and current_speed > physics['idle']:
            engine_state = "ENGINE_BRAKING"
        elif current_gear != 'n' and current_speed == physics['idle']:
            engine_state = "IDLE_CREEP"
        elif current_speed > 0:
            engine_state = "COASTING"
        else:
            engine_state = "IDLE"

        # Gear number as integer (0 for Neutral)
        gear_num = 0 if current_gear == 'n' else int(current_gear)

        # --- DIRECT ENCODER FEED (no CSV, no file I/O) ---
        telemetry_row = {
            "Speed_kmh": int(current_speed),
            "Engine_RPM": int(current_rpm),
            "Coolant_Temp_C": round(coolant_temp, 2),
            "Oil_Temp_C": round(oil_temp, 2),
            "Ambient_Temp_C": round(ambient_temp, 1),
            "Fuel_Rate_mL_s": round(instant_fuel_rate, 2),
            "Remaining_Fuel_L": round(remaining_fuel_ml / 1000, 3),
            "Fuel_Pct": fuel_pct,
            "Distance_km": round(distance_km, 4),
            "Accel_ms2": accel_ms2,
            "Engine_Load_Pct": engine_load_pct,
            "Throttle_Pct": throttle_pct,
            "Gear_Num": gear_num,
            "Battery_V": round(battery_voltage, 2),
            "Tyre_P_FL": 32.1,
            "Tyre_P_FR": 32.0,
            "Tyre_P_RL": 31.8,
            "Tyre_P_RR": 31.9,
            "Stall_Risk": stall_risk,
        }

        encode_frame(telemetry_row)

        # Bug fix: reliable tick-based fuel save instead of time.time() modulo
        fuel_save_counter += 1
        if fuel_save_counter >= 50:
            save_fuel_state(remaining_fuel_ml)
            fuel_save_counter = 0

        # --- DASHBOARD DISPLAY ---
        # clear_screen()
        # print("=" * 50)
        # print("         REAL-TIME ENGINE SIMULATOR")
        # print("=" * 50)

        # # Dashboard Alerts
        # if remaining_fuel_ml <= 0:
        #     print(" [!] OUT OF FUEL! PRESS 'R' TO REFUEL!")
        # elif remaining_fuel_ml < 4000:
        #     print(" [!] LOW FUEL WARNING!")
        # elif gear_grind_warning:
        #     print(" [!] GRINDING GEARS! PRESS CLUTCH ('c') TO SHIFT!")
        # elif stall_risk:
        #     print(" [!] STALL RISK! PRESS CLUTCH OR SHIFT DOWN!")
        # elif rev_limiter:
        #     print(" [!] REV LIMITER REACHED - SHIFT UP !!!")
        # elif coolant_temp > 105:
        #     print(" [!] ENGINE OVERHEATING!")
        # else:
        #     print("")

        # print("-" * 50)
        # print(f" GEAR:          [{physics['name']}]   STATE: [{engine_state}]")
        # print(f" SPEED:         {int(current_speed)} km/h       ACCEL: {accel_ms2} m/s^2")
        # print(f" RPM:           {int(current_rpm)} RPM")
        # print(f" COOLANT:       {coolant_temp:.1f} C       OIL: {oil_temp:.1f} C")
        # print(f" BATTERY:       {battery_voltage:.2f} V")
        # print("-" * 50)
        # fuel_percentage = fuel_pct
        # print(f" TRIP DIST:     {distance_km:.3f} km")
        # print(f" FUEL:          {fuel_percentage:.1f}%  ({remaining_fuel_ml/1000:.2f} L)")
        # if instant_fuel_rate == 0.0 and current_rpm > 0 and remaining_fuel_ml > 0:
        #     print(" FUEL RATE:     [INJECTORS OFF - COASTING]")
        # else:
        #     print(f" FUEL RATE:     {instant_fuel_rate:.1f} mL/sec   LOAD: {engine_load_pct}%")
        # print("-" * 50)
        # gas_str = "ON" if is_accelerating else "OFF"
        # brake_str = "ON" if is_braking else "OFF"
        # clutch_str = "DOWN" if is_clutch_down else "UP"
        # print(f" PEDALS:  [GAS:{gas_str}] [BRAKE:{brake_str}] [CLUTCH:{clutch_str}]")
        # print("=" * 50)
        # print(" [Space]:Accel  [B]:Brake  [C]:Clutch  [1-5/N]:Gear")
        # print(" [R]:Refuel  [Q]:Quit & Save")

        time.sleep(refresh_rate)

if __name__ == "__main__":
    main()