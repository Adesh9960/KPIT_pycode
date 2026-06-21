import simulator.main as main
def display_stats(is_clutch_down, is_accelerating, physics, is_braking, engine_state):
        print("=" * 50)
        print("         REAL-TIME ENGINE SIMULATOR")
        print("=" * 50)

        # # Dashboard Alerts
        if main.remaining_fuel_ml <= 0:
            print(" [!] OUT OF FUEL! PRESS 'R' TO REFUEL!")
        elif main.remaining_fuel_ml < 4000:
            print(" [!] LOW FUEL WARNING!")
        elif main.gear_grind_warning:
            print(" [!] GRINDING GEARS! PRESS CLUTCH ('c') TO SHIFT!")
        # elif stall_risk:
        #     print(" [!] STALL RISK! PRESS CLUTCH OR SHIFT DOWN!")
        # elif rev_limiter:
        #     print(" [!] REV LIMITER REACHED - SHIFT UP !!!")
        elif main.coolant_temp > 105:
            print(" [!] ENGINE OVERHEATING!")
        else:
            print("")

        print("-" * 50)
        print(f" GEAR:          [{physics['name']}]   STATE: [{engine_state}]")
        print(f" SPEED:         {int(main.current_speed)} km/h")
        print(f" RPM:           {int(main.current_rpm)} RPM")
        print(f" COOLANT:       {main.coolant_temp:.1f} C       OIL: {main.oil_temp:.1f} C")
        print(f" BATTERY:       {main.battery_voltage:.2f} V")
        print(f" HeadLamp:       {"ON" if main.head_lamp.state else "OFF"}")

        print("-" * 50)
        # fuel_percentage = fuel_pct
        print(f" TRIP DIST:     {main.distance_km:.3f} km")
        print(f" FUEL:          ({main.remaining_fuel_ml/1000:.2f} L)")
        if main.instant_fuel_rate == 0.0 and main.current_rpm > 0 and main.remaining_fuel_ml > 0:
            print(" FUEL RATE:     [INJECTORS OFF - COASTING]")
        # else:
        #     print(f" FUEL RATE:     {main.instant_fuel_rate:.1f} mL/sec   LOAD: {engine_load_pct}%")
        print("-" * 50)
        gas_str = "ON" if is_accelerating else "OFF"
        brake_str = "ON" if is_braking else "OFF"
        clutch_str = "DOWN" if is_clutch_down else "UP"
        print(f" PEDALS:  [GAS:{gas_str}] [BRAKE:{brake_str}] [CLUTCH:{clutch_str}]")
        print("=" * 50)
        print(" [Space]:Accel  [B]:Brake  [C]:Clutch  [1-5/N]:Gear")
        print(" [R]:Refuel  [Q]:Quit & Save")