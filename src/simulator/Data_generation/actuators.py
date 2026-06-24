import simulator.main as main
from simulator.actuators.actuator import Control
def update_radiator_fan():

    if main.radiator_fan.control != Control.ECU:
        return

    if main.coolant_temp >= 95:
        main.radiator_fan.state = True

    elif main.coolant_temp <= 90:
        main.radiator_fan.state = False

def update_fuel_pump():

    if main.fuel_pump.control != Control.ECU:
        return

    if main.current_rpm > 0:
        main.fuel_pump.state = True
    else:
        main.fuel_pump.state = False

def update_headlamp():

    if main.head_lamp.control != Control.ECU:
        return

    main.head_lamp.state = main.headlamp_switch