import time
import math
import os
import sys
import requests
import simulator.Data_generation.actuators as actuators
from simulator.Data_generation.display_data import display_stats
from simulator.dids.didList import DID_DATABASE
import random
# from simulator.Data_generation.UDSHandler import UDSHandler
from encoder.encoder import encode_frame
from simulator.Data_generation.steering import update_steering, calculate_lateral_accel
from simulator.Data_generation.tyres import calculate_tire_pressures
try:
    import keyboard
except ImportError:
    print("Please install the keyboard module first by running: pip install keyboard")
    sys.exit()

import simulator.main as main

# ═══════════════════════════════════════════════════════════════
# CONSTANTS & CONFIG
# ═══════════════════════════════════════════════════════════════
FUEL_SAVE_FILE  = "fuel_save.txt"
MAX_FUEL_ML     = 40000.0       # 40 Liters

# Engine constants (naturally aspirated petrol engine model)
ENGINE_DISPLACEMENT_L   = 1.6   # litres
AIR_DENSITY_KG_M3       = 1.204 # kg/m³ at sea level, 20°C
VOLUMETRIC_EFFICIENCY   = 0.85  # typical NA petrol engine
STOICH_AFR              = 14.7  # stoichiometric air-fuel ratio
IDLE_FUEL_TRIM_PCT      = 0.0   # learned fuel trim (long-term adaptation)


# Physics Dictionary
gear_physics = {
    'n': {'max': 0,   'idle': 0,  'name': 'Neutral',  'k': 0},
    '1': {'max': 40,  'idle': 8,  'name': '1st Gear', 'k': 1.2},
    '2': {'max': 90,  'idle': 15, 'name': '2nd Gear', 'k': 0.6},
    '3': {'max': 135, 'idle': 25, 'name': '3rd Gear', 'k': 0.15},
    '4': {'max': 170, 'idle': 35, 'name': '4th Gear', 'k': 0.08},
    '5': {'max': 190, 'idle': 45, 'name': '5th Gear', 'k': 0.04}
}

# ABS PARAMETERS
brake_force = 0
wheel_fl = 0
wheel_fr = 0
wheel_rl = 0
wheel_rr = 0
# Module-level UDS handler — single instance shared via import
# uds_handler = UDSHandler()

headlamp_switch_timeout = time.time()



# ═══════════════════════════════════════════════════════════════
# FUEL PERSISTENCE
# ═══════════════════════════════════════════════════════════════
def load_fuel_state():
    if os.path.exists(FUEL_SAVE_FILE):
        try:
            with open(FUEL_SAVE_FILE, 'r') as f:
                return float(f.read().strip())
        except Exception:
            return MAX_FUEL_ML
    return MAX_FUEL_ML

def save_fuel_state(fuel_ml):
    with open(FUEL_SAVE_FILE, 'w') as f:
        f.write(str(fuel_ml))


# ═══════════════════════════════════════════════════════════════
# LIVE AMBIENT TEMP
# ═══════════════════════════════════════════════════════════════
def get_live_ambient_temp():
    print("Fetching live weather data for engine cold-start...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=18.52&longitude=73.85&current_weather=true"
    try:
        response  = requests.get(url, timeout=5)
        data      = response.json()
        live_temp = data['current_weather']['temperature']
        print(f"Weather fetched! Starting ambient temperature is {live_temp}°C")
        return float(live_temp)
    except Exception:
        print("Warning: Could not connect to weather API. Defaulting to 25.0°C")
        return 25.0

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ═══════════════════════════════════════════════════════════════
# GEAR CHANGE
# ═══════════════════════════════════════════════════════════════
def check_gear(is_clutch_down):
    for g in ['n', '1', '2', '3', '4', '5']:
        if keyboard.is_pressed(g) and main.current_gear != g:
            if is_clutch_down:
                main.current_gear = g
                main.time_held    = 0.0
                if main.current_speed > 0:
                    main.current_speed  = max(0.0, main.current_speed - 1.5)
                    main.baseline_speed = main.current_speed
                main.gear_grind_warning = False
            else:
                main.gear_grind_warning = True


# ═══════════════════════════════════════════════════════════════
# PHYSICS HANDLERS (unchanged from before)
# ═══════════════════════════════════════════════════════════════
def handle_rpm_physics(is_clutch_down, is_accelerating, physics):
    if main.remaining_fuel_ml <= 0 and main.current_speed == 0:
        main.current_rpm = 0.0
    elif is_clutch_down or main.current_gear == 'n':
        if is_accelerating and main.remaining_fuel_ml > 0:
            main.current_rpm = min(main.MAX_RPM, main.current_rpm + (4000.0 * main.refresh_rate))
        else:
            main.current_rpm = max(
                main.IDLE_RPM if main.remaining_fuel_ml > 0 else 0,
                main.current_rpm - (3000.0 * main.refresh_rate)
            )
    else:
        if main.current_speed == 0:
            main.current_rpm = main.IDLE_RPM
        else:
            speed_ratio      = main.current_speed / physics['max']
            main.current_rpm = max(main.IDLE_RPM, 1000 + (speed_ratio * (main.MAX_RPM - 1000)))
    
    if(main.current_rpm >= 7000):
        main.dtc_manager.set_dtc(
            code=0x200003,
            description="Engine OverSpeed",
            snapshot={
                "battery": main.battery_voltage,
                "speed": main.current_speed,
                "rpm": main.current_rpm,
                "gear": main.current_gear
            }
        )


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
            engine_load            = (main.current_speed / max(1, physics['max'])) + 0.5
            main.instant_fuel_rate = engine_load * (main.current_rpm / main.MAX_RPM) * 12.0
        else:
            if main.current_rpm > main.IDLE_RPM + 150:
                main.instant_fuel_rate = 0.0
            else:
                main.instant_fuel_rate = 0.5

    consumed_this_tick      = main.instant_fuel_rate * main.refresh_rate
    main.total_fuel_ml     += consumed_this_tick
    main.remaining_fuel_ml  = max(0.0, main.remaining_fuel_ml - consumed_this_tick)


def handle_speed(is_clutch_down, is_accelerating, physics, is_braking):
    drag_deceleration = (main.current_speed * 0.05) * main.refresh_rate

    if is_braking:
        brake_force        = (main.current_speed * 0.8 + 10.0) * main.refresh_rate
        main.current_speed = max(0.0, main.current_speed - brake_force)
        main.time_held     = 0.0
    elif is_accelerating and not is_clutch_down and main.current_gear != 'n':
        if main.remaining_fuel_ml > 0:
            main.time_held    += main.refresh_rate
            acceleration       = physics['k'] * (physics['max'] - main.current_speed)
            main.current_speed += acceleration * main.refresh_rate
    else:
        main.time_held = 0.0
        idle_speed     = physics['idle']
        if main.current_gear == 'n' or is_clutch_down:
            main.current_speed = max(0.0, main.current_speed - drag_deceleration)
        else:
            if main.current_speed > idle_speed:
                engine_braking     = (main.current_speed * 0.05 + physics['k'] * 5) * main.refresh_rate
                main.current_speed = max(float(idle_speed), main.current_speed - engine_braking)
            elif main.current_speed < idle_speed and main.current_speed > 0:
                ecu_recovery = 2.0 * main.refresh_rate
                if main.remaining_fuel_ml > 0:
                    main.current_speed = min(float(idle_speed), main.current_speed + ecu_recovery)
                else:
                    main.current_speed = max(0.0, main.current_speed - drag_deceleration)


def handle_battery_and_temp(is_clutch_down, is_accelerating, physics):
    if is_accelerating and main.current_gear != 'n' and not is_clutch_down and main.remaining_fuel_ml > 0:
        engine_load = (main.current_speed / max(1, physics['max'])) + 0.5
        heat_input  = engine_load * 2.0 * main.refresh_rate
    else:
        if main.current_rpm > main.IDLE_RPM + 1000 and is_clutch_down:
            heat_input = 1.5 * main.refresh_rate
        else:
            heat_input = 0.3 * main.refresh_rate

    main.coolant_temp += heat_input

    if main.coolant_temp > main.target_temp:
        cooling_effect    = ((main.coolant_temp - main.target_temp) * 0.2 + (main.current_speed * 0.01)) * main.refresh_rate
        main.coolant_temp -= cooling_effect
    else:
        ambient_cooling   = ((main.coolant_temp - main.ambient_temp) * 0.01) * main.refresh_rate
        main.coolant_temp -= ambient_cooling

    oil_target     = main.coolant_temp + 10.0
    main.oil_temp += (oil_target - main.oil_temp) * 0.02 * main.refresh_rate

    if main.current_rpm > main.IDLE_RPM + 50:
        main.battery_voltage = min(14.4, main.battery_voltage + 0.01 * main.refresh_rate)
    else:
        main.battery_voltage = max(11.8, main.battery_voltage - 0.005 * main.refresh_rate)

    if main.battery_voltage < 10.5:
        main.dtc_manager.set_dtc(
            code=0x100001,
            description="Battery Voltage Low",
            snapshot={
                "battery": main.battery_voltage,
                "speed": main.current_speed
            }
        )
    if main.battery_voltage > 15:
        main.dtc_manager.set_dtc(
            code=0x100002,
            description="Battery Voltage High",
            snapshot={
                "battery": main.battery_voltage,
                "speed": main.current_speed
            }
        )


def get_engine_state(is_clutch_down, is_accelerating, physics, is_braking) -> str:
    if main.remaining_fuel_ml <= 0 and main.current_speed == 0:
        return "DEAD"
    elif main.current_rpm <= 100 and main.current_gear != 'n' and not is_clutch_down:
        return "STALLED"
    elif is_braking:
        return "BRAKING"
    elif is_clutch_down:
        return "CLUTCH_OUT"
    elif is_accelerating and main.current_gear != 'n':
        return "ACCELERATING"
    elif main.current_gear != 'n' and main.current_speed > physics['idle']:
        return "ENGINE_BRAKING"
    elif main.current_gear != 'n' and main.current_speed == physics['idle']:
        return "IDLE_CREEP"
    elif main.current_speed > 0:
        return "COASTING"
    else:
        return "IDLE"

def get_abs_parameter():
    wheel_fl = main.current_speed + random.uniform(-0.5, 0.5)
    wheel_fr = main.current_speed + random.uniform(-0.5, 0.5)
    wheel_rl = main.current_speed + random.uniform(-0.5, 0.5)
    wheel_rr = main.current_speed + random.uniform(-0.5, 0.5)
# ═══════════════════════════════════════════════════════════════
# DERIVED PARAMETER CALCULATORS
# All values simulated/derived from existing physics state.
# No real sensor needed — these mirror what a real ECU computes.
# ═══════════════════════════════════════════════════════════════

def _derive_raw_load(is_clutch_down, physics) -> float:
    """Shared engine load fraction (0.0–1.5) used by multiple derived params."""
    if main.current_gear != 'n' and not is_clutch_down and main.current_speed > 0:
        return (main.current_speed / max(1, physics['max'])) + 0.5
    return main.current_rpm / main.MAX_RPM


def calc_map_kpa(raw_load: float) -> float:
    """
    Manifold Absolute Pressure (kPa).
    At idle/light load: near vacuum (~30 kPa).
    At full throttle: near atmospheric (101.3 kPa).
    Formula: MAP = atm_pressure × throttle_fraction × volumetric_efficiency
    """
    atm_kpa        = 101.3
    throttle_frac  = min(1.0, raw_load / 1.5)
    map_kpa        = 20.0 + (atm_kpa - 20.0) * throttle_frac * VOLUMETRIC_EFFICIENCY
    return round(map_kpa, 1)


def calc_maf_gs(map_kpa: float) -> float:
    """
    Mass Air Flow (g/s).
    Derived from MAP, RPM, displacement, and air density.
    MAF = (RPM/2) × (displacement/1000 in m³) × VE × air_density × (MAP/101.3)
    """
    if main.current_rpm < 100:
        return 0.0
    rpm_per_cycle   = main.current_rpm / 2.0          # 4-stroke: one intake per 2 revolutions
    vol_per_cycle_m3 = (ENGINE_DISPLACEMENT_L / 1000.0) / 2.0  # per cylinder pair
    air_vol_per_s   = rpm_per_cycle / 60.0 * vol_per_cycle_m3 * VOLUMETRIC_EFFICIENCY
    density_adj     = map_kpa / 101.3
    maf             = air_vol_per_s * AIR_DENSITY_KG_M3 * density_adj * 1000.0  # kg→g
    return round(max(0.0, maf), 2)


def calc_injector_pulse_ms(raw_load: float) -> float:
    """
    Injector pulse width (ms).
    At stoichiometric AFR: pulse = (fuel_rate_per_cylinder / injector_flow_rate) × 1000
    Simplified: scales with fuel rate and RPM.
    Typical range: 1.5 ms (idle) → 12 ms (WOT).
    """
    if main.current_rpm < 100:
        return 0.0
    injections_per_sec = main.current_rpm / 60.0   # each cylinder fires once per rev (2-stroke approx)
    if injections_per_sec == 0:
        return 0.0
    # fuel_rate_ml_s → ml per injection → pulse width
    ml_per_injection = main.instant_fuel_rate / max(1.0, injections_per_sec)
    # Injector flow rate: ~200 ml/min → 3.33 ml/s
    injector_flow_ml_s = 3.33
    pulse_ms = (ml_per_injection / injector_flow_ml_s) * 1000.0
    return round(min(15.0, max(0.0, pulse_ms)), 2)


def calc_ignition_timing_deg(raw_load: float) -> float:
    """
    Ignition timing advance (degrees BTDC).
    High RPM, low load → more advance (up to ~35°).
    High load → retarded to prevent knock (~8°).
    Base timing: 10° BTDC.
    """
    if main.current_rpm < 100:
        return 0.0
    rpm_factor  = (main.current_rpm / main.MAX_RPM) * 25.0   # 0→25 deg with RPM
    load_retard = (raw_load / 1.5) * 15.0                     # 0→15 deg retard with load
    timing      = 10.0 + rpm_factor - load_retard
    return round(min(40.0, max(0.0, timing)), 1)


def calc_fuel_trim_pct(raw_load: float) -> float:
    """
    Short-term fuel trim (%).
    In a real ECU this corrects for O2 sensor feedback.
    Simulated: small oscillation around learned baseline,
    larger deviation at extremes of load.
    """
    base_trim    = IDLE_FUEL_TRIM_PCT
    load_dev     = (raw_load - 0.5) * 4.0        # deviation from mid-load
    oscillation  = math.sin(time.monotonic() * 2.0) * 1.5   # ±1.5% hunting
    trim         = base_trim + load_dev + oscillation
    return round(min(25.0, max(-25.0, trim)), 1)


def calc_knock_count() -> int:
    """
    Knock sensor activity (event count this second).
    Knock is more likely near rev limiter and under high load.
    Simulated as probabilistic event.
    """
    import random
    if main.current_rpm > main.MAX_RPM - 300:
        return random.choices([0, 1, 2], weights=[60, 30, 10])[0]
    elif main.current_rpm > main.MAX_RPM * 0.85:
        return random.choices([0, 1], weights=[85, 15])[0]
    return 0


def calc_catalyst_temp_c() -> float:
    """
    Catalytic converter temperature (°C).
    Lags engine load and coolant temp.
    Typical operating range: 400–800°C.
    Lights off temperature: ~250°C.
    """
    if main.current_rpm < 100:
        # Cold / dead engine: catalyst cools toward ambient
        main._cat_temp = getattr(main, '_cat_temp', main.ambient_temp)
        main._cat_temp = max(main.ambient_temp, main._cat_temp - 5.0 * main.refresh_rate)
        return round(main._cat_temp, 1)

    engine_load_frac = min(1.0, main.instant_fuel_rate / 12.0)
    target_cat       = 350.0 + engine_load_frac * 500.0   # 350°C idle → 850°C WOT
    main._cat_temp   = getattr(main, '_cat_temp', main.ambient_temp)
    main._cat_temp  += (target_cat - main._cat_temp) * 0.005 * main.refresh_rate
    return round(max(main.ambient_temp, main._cat_temp), 1)


def calc_alternator_output_v() -> float:
    """
    Alternator output voltage (V).
    Above idle: 13.8–14.4V regulated.
    Below idle or stalled: 0V (not spinning).
    """
    if main.current_rpm > main.IDLE_RPM + 50:
        return round(min(14.4, 13.8 + (main.current_rpm / main.MAX_RPM) * 0.6), 2)
    return 0.0


def calc_fuel_pressure_bar() -> float:
    """
    Fuel rail pressure (bar).
    Pump running: nominal 3.5 bar.
    Pump off: drops toward 0.
    """
    if main.fuel_pump.state:
        return round(3.5 - (main.instant_fuel_rate / 12.0) * 0.3, 2)
    return 0.0


def calc_brake_pedal_pct(is_braking: bool) -> float:
    """
    Brake pedal position (%).
    Simplified binary from keyboard — 0% or 100%.
    A real sensor would give analog value.
    """
    return 100.0 if is_braking else 0.0


def calc_trans_fluid_temp_c() -> float:
    """
    Transmission fluid temperature (°C).
    Lags oil temp by ~5°C and rises more slowly.
    """
    main._trans_temp = getattr(main, '_trans_temp', main.ambient_temp)
    target           = main.oil_temp - 5.0
    main._trans_temp += (target - main._trans_temp) * 0.01 * main.refresh_rate
    return round(main._trans_temp, 1)


def calc_battery_soc_pct() -> float:
    """Battery state of charge (%) derived from voltage."""
    bv  = main.battery_voltage
    soc = (bv - 11.8) / (14.4 - 11.8) * 100.0
    return round(max(0.0, min(100.0, soc)), 1)


def calc_idle_speed_adaptation() -> int:
    """
    Learned idle RPM adaptation.
    Starts at base IDLE_RPM, adjusts slightly with long-term running.
    Simulated as stable value near IDLE_RPM.
    """
    return int(main.IDLE_RPM + IDLE_FUEL_TRIM_PCT * 10)


# ═══════════════════════════════════════════════════════════════
# MAIN TELEMETRY BUILDER
# ═══════════════════════════════════════════════════════════════
def get_telemetry_entry(is_clutch_down, physics, is_braking: bool = False) -> dict:
    # ── Base calculations ──
    accel_ms2   = round((main.current_speed - main.prev_speed) / 0.1, 2)
    fuel_pct    = round((main.remaining_fuel_ml / MAX_FUEL_ML) * 100.0, 1)
    if fuel_pct < 5:
        main.dtc_manager.set_dtc(
            code=0x500001,
            description="Fuel low",
            snapshot={
                fuel_pct: fuel_pct,
            }
        )
    raw_load    = _derive_raw_load(is_clutch_down, physics)
    engine_load_pct = round(min(100.0, raw_load / 1.5 * 100.0), 1)

    max_possible_rate = (raw_load * (main.current_rpm / main.MAX_RPM) * 12.0) if main.current_rpm > 0 else 1.0
    throttle_pct      = round(min(100.0, (main.instant_fuel_rate / max(0.01, max_possible_rate)) * 100.0), 1)

    rev_limiter = 1 if main.current_rpm >= main.MAX_RPM - 100 else 0
    stall_risk  = 1 if (
        main.current_rpm < main.IDLE_RPM + 300
        and main.current_gear != 'n'
        and not is_clutch_down
        and main.current_speed < 5
    ) else 0

    # ── Derived parameters ──
    map_kpa         = calc_map_kpa(raw_load)
    maf_gs          = calc_maf_gs(map_kpa)
    injector_pw_ms  = calc_injector_pulse_ms(raw_load)
    ign_timing_deg  = calc_ignition_timing_deg(raw_load)
    fuel_trim_pct   = calc_fuel_trim_pct(raw_load)
    knock_count     = calc_knock_count()
    cat_temp_c      = calc_catalyst_temp_c()
    alt_output_v    = calc_alternator_output_v()
    fuel_press_bar  = calc_fuel_pressure_bar()
    brake_pedal_pct = calc_brake_pedal_pct(is_braking)
    trans_fluid_c   = calc_trans_fluid_temp_c()
    battery_soc     = calc_battery_soc_pct()
    idle_adapt_rpm  = calc_idle_speed_adaptation()

    return {
        # ══ 1. ENGINE & POWERTRAIN ══════════════════════════════
        "Speed_kmh":            int(main.current_speed),
        "Engine_RPM":           int(main.current_rpm),
        "Engine_Load_Pct":      engine_load_pct,
        "Throttle_Pct":         throttle_pct,
        "MAF_g_s":              maf_gs,             # Mass Air Flow (g/s)
        "MAP_kPa":              map_kpa,             # Manifold Absolute Pressure (kPa)
        "IAT_C":                round(main.ambient_temp, 1),  # Intake Air Temp ≈ ambient
        "Coolant_Temp_C":       round(main.coolant_temp, 2),
        "Oil_Temp_C":           round(main.oil_temp, 2),
        "Ambient_Temp_C":       round(main.ambient_temp, 1),
        "Fuel_Pressure_bar":    fuel_press_bar,      # Fuel rail pressure
        "Fuel_Trim_Pct":        fuel_trim_pct,       # Short-term fuel trim
        "Ign_Timing_deg":       ign_timing_deg,      # Ignition timing advance (BTDC)
        "Knock_Count":          knock_count,          # Knock sensor events
        "Injector_PW_ms":       injector_pw_ms,      # Injector pulse width
        "Catalyst_Temp_C":      cat_temp_c,          # Catalytic converter temp
        "Fuel_Rate_mL_s":       round(main.instant_fuel_rate, 2),
        "Remaining_Fuel_L":     round(main.remaining_fuel_ml / 1000, 3),
        "Fuel_Pct":             fuel_pct,
        "Distance_km":          round(main.distance_km, 4),
        "Accel_ms2":            accel_ms2,

        # ══ 2. TRANSMISSION ═════════════════════════════════════
        "Gear":                 main.current_gear.upper(),
        "Gear_Num":             0 if main.current_gear == 'n' else int(main.current_gear),
        "Trans_Fluid_Temp_C":   trans_fluid_c,       # Transmission fluid temperature
        "Clutch_State":         "DOWN" if is_clutch_down else "UP",
        "Brake_State":          "PRESSED" if is_braking else "OFF",

        # ══ 3. ELECTRICAL & BATTERY ═════════════════════════════
        "Battery_V":            round(main.battery_voltage, 2),
        "Battery_SOC_Pct":      battery_soc,         # State of charge %
        "Alternator_V":         alt_output_v,         # Alternator output voltage

        # ══ 4. CHASSIS & SAFETY ═════════════════════════════════
        # All 4 wheel speeds = vehicle speed (no slip model)
        "Wheel_Speed_FL_kmh":   int(main.current_speed),
        "Wheel_Speed_FR_kmh":   int(main.current_speed),
        "Wheel_Speed_RL_kmh":   int(main.current_speed),
        "Wheel_Speed_RR_kmh":   int(main.current_speed),
        "Brake_Pedal_Pct":      brake_pedal_pct,     # 0% or 100%
        "Tyre_P_FL":            32.1,
        "Tyre_P_FR":            32.0,
        "Tyre_P_RL":            31.8,
        "Tyre_P_RR":            31.9,

        # ══ 5. STATUS FLAGS ═════════════════════════════════════
        "Stall_Risk":           stall_risk,
        "Rev_Limiter":          rev_limiter,

        # ══ 6. ACTUATORS ════════════════════════════════════════
        "Head_Lamp":            int(main.head_lamp.state),
        "Radiator_Fan":         int(main.radiator_fan.state),
        "Fuel_Pump":            int(main.fuel_pump.state),

        # ══ 7. ADAPTATIONS ══════════════════════════════════════
        "Idle_Speed_Adapt_RPM": idle_adapt_rpm,      # Learned idle RPM

        # ══ 8. UDS SESSION ══════════════════════════════════════
        # "UDS_Session":          uds_handler.get_session(),
    }


# ═══════════════════════════════════════════════════════════════
# MAIN SIMULATOR LOOP
# ═══════════════════════════════════════════════════════════════
def run_vehicle_simulator():
    global headlamp_switch_timeout

    main.remaining_fuel_ml = load_fuel_state()
    main.ambient_temp      = get_live_ambient_temp()
    main.coolant_temp      = main.ambient_temp
    main.oil_temp          = main.ambient_temp

    clear_screen()
    print("Starting Continuous Physics Engine with Direct Encoder Feed...")
    print(f"UDS Session: Default (0x01)")
    time.sleep(1)

    while True:
        if keyboard.is_pressed('q'):
            save_fuel_state(main.remaining_fuel_ml)
            clear_screen()
            print(f"Engine Turned Off.")
            print(f"Trip Fuel: {main.total_fuel_ml:.1f} mL | Distance: {main.distance_km:.3f} km")
            print(f"Remaining: {main.remaining_fuel_ml/1000:.2f} L")
            break

        if keyboard.is_pressed('r'):
            main.remaining_fuel_ml = MAX_FUEL_ML

        dt = 0.05

        left_pressed = keyboard.is_pressed("<")
        right_pressed = keyboard.is_pressed(">")

        update_steering(left_pressed, right_pressed, dt)

  
        is_accelerating = keyboard.is_pressed('space')
        is_braking      = keyboard.is_pressed('b')
        is_clutch_down  = keyboard.is_pressed('c')

        if keyboard.is_pressed('o') and time.time() - headlamp_switch_timeout > 0.1:
            main.headlamp_switch    = not main.headlamp_switch
            headlamp_switch_timeout = time.time()

        check_gear(is_clutch_down)
        physics = gear_physics[main.current_gear]

        if is_accelerating and not main.was_accelerating:
            main.baseline_speed = main.current_speed
        main.was_accelerating = is_accelerating
        main.prev_speed       = main.current_speed

        # ── Physics ──
        handle_speed(is_clutch_down, is_accelerating, physics, is_braking)
        calculate_lateral_accel()
        main.distance_km += (main.current_speed / 3600.0) * main.refresh_rate
        handle_rpm_physics(is_clutch_down, is_accelerating, physics)
        handle_fuel_physics(is_clutch_down, is_accelerating, physics)
        handle_battery_and_temp(is_clutch_down, is_accelerating, physics)

        # ── Actuators ──
        actuators.update_fuel_pump()
        actuators.update_headlamp()
        actuators.update_radiator_fan()

        # ── Engine state ──
        engine_state = get_engine_state(is_clutch_down, is_accelerating, physics, is_braking)

        # ── UDS S3 timer ──
        # uds_handler.tick()

        # ── Telemetry ──
        telemetry_row = get_telemetry_entry(is_clutch_down, physics, is_braking)
        telemetry_row["Engine_State"] = engine_state

        # 1. Fetch STATIC ECU data directly from didList.py (VIN, ECU#, S/W, H/W)
        # Using .decode() because DID_DATABASE stores values as raw bytes
        try:
            live_vin = DID_DATABASE[0xF190].value.decode('utf-8').strip('\x00') if 0xF190 in DID_DATABASE else "N/A"
            live_ecu = DID_DATABASE[0xF18C].value.decode('utf-8').strip('\x00') if 0xF18C in DID_DATABASE else "N/A"
            live_sw  = DID_DATABASE[0xF181].value.decode('utf-8').strip('\x00') if 0xF181 in DID_DATABASE else "N/A"
            live_hw  = DID_DATABASE[0xF180].value.decode('utf-8').strip('\x00') if 0xF180 in DID_DATABASE else "N/A"
        except Exception:
            live_vin, live_ecu, live_sw, live_hw = "ERROR", "ERROR", "ERROR", "ERROR"

        tyre_pressure, main.tyre_temps = calculate_tire_pressures(
            main.current_speed,
            float(telemetry_row.get("Accel_ms2", 0)),
            main.lateral_accel,
            brake_force,
            dt,
            main.tyre_temps,
              )
        # 3. Build the final payload containing STATIC ECU info, UI strings, and live DIDs
        payload = {
            # --- STATIC ECU INFO FETCHED FROM didList.py ---
            "vin": live_vin,
            "ecu_serial": live_ecu,
            "sw_version": live_sw,
            "hw_version": live_hw,

            # --- FULL LIST OF UI STRINGS (DO NOT OMIT) ---
            # "time": telemetry_row.get("System_Time", 0),
            # "gear": telemetry_row.get("Gear", "N"),

            "Gear_Num": int(telemetry_row.get("Gear_Num", 0)),
            "Speed_kmh": float(telemetry_row.get("Speed_kmh", 0)),
            "Engine_RPM": int(telemetry_row.get("Engine_RPM", 0)),
            "Coolant_Temp_C": float(telemetry_row.get("Coolant_Temp_C", 0)),
            "Oil_Temp_C": float(telemetry_row.get("Oil_Temp_C", 0)),
            "Ambient_Temp_C": float(telemetry_row.get("Ambient_Temp_C", 0)),
            "Fuel_Pct": float(telemetry_row.get("Fuel_Pct", 0)),
            "Fuel_Rate_mL_s": float(telemetry_row.get("Fuel_Rate_mL_s", 0)),
            "Remaining_Fuel_L": float(telemetry_row.get("Remaining_Fuel_L", 0)),
            "Distance_km": float(telemetry_row.get("Distance_km", 0)),
            "Accel_ms2": float(telemetry_row.get("Accel_ms2", 0)),
            "Engine_Load_Pct": float(telemetry_row.get("Engine_Load_Pct", 0)),
            "Throttle_Pct": float(telemetry_row.get("Throttle_Pct", 0)),
            "Rev_Limiter": int(telemetry_row.get("Rev_Limiter", 0)),
            # "engine_state": engine_state, # Extracted from local variable
            "Stall_Risk": int(telemetry_row.get("Stall_Risk", 0)),
            "Clutch_State": telemetry_row.get("Clutch_State", "UP"),
            "Brake_State": telemetry_row.get("Brake_State", "UP"),
            "Battery_V": float(telemetry_row.get("Battery_V", 0)),
            "Head_Lamp": int(main.head_lamp.state),
            "Radiator_Fan": int(main.radiator_fan.state),
            "Fuel_Pump": int(main.fuel_pump.state),
            # Tyres
            "Tyre_P_FL" : tyre_pressure[0],
            "Tyre_P_FR" :tyre_pressure[1],
            "Tyre_P_RL" : tyre_pressure[2],
            "Tyre_P_RR": tyre_pressure[3],
            #ChassisDynamics
            "Brake_Force_Pct": brake_force,
            "Steering_Angle_deg": main.steering_angle,
            "Lateral_Accel_ms2": main.lateral_accel,
            "Steering_Direction": main.steering_direction,


        }

        # 4. Transmit the data to encoder
        encode_frame(payload)


        # ── Fuel save every 50 ticks ──
        main.fuel_save_counter += 1
        if main.fuel_save_counter >= 50:
            save_fuel_state(main.remaining_fuel_ml)
            main.fuel_save_counter = 0

        # display_stats(is_clutch_down, is_accelerating, physics, is_braking, engine_state)
        time.sleep(main.refresh_rate)


if __name__ == "__main__":
    run_vehicle_simulator()