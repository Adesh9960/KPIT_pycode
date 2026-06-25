import math


def calculate_tire_pressures(
    speed_kmh,
    accel,
    lateral_accel,
    brake_force,
    dt,
    tire_temps,
    leak_rates=(0, 0, 0, 0),
):
    """
    Simulates pressure of each tire.

    Parameters
    ----------
    speed_kmh : float
    accel : float              # Longitudinal acceleration (m/s²)
    lateral_accel : float      # Lateral acceleration (m/s²)
    brake_force : float        # 0-100 %
    dt : float                 # Time step (s)
    tire_temps : list[float]   # [FL, FR, RL, RR] (°C)
    leak_rates : tuple         # psi/sec for each tire

    Returns
    -------
    pressures : list[float]
    updated_temperatures : list[float]
    """

    # ---------------- Vehicle ----------------
    mass = 1500.0                 # kg
    g = 9.81
    wheelbase = 2.7               # m
    track = 1.6                   # m
    cg_height = 0.55              # m
    front_weight = 0.60           # 60% front

    base_pressure = 32.0          # psi
    ambient_temp = 25.0           # °C

    # ---------------- Static Loads ----------------
    F_front = mass * g * front_weight / 2
    F_rear = mass * g * (1 - front_weight) / 2

    # ---------------- Dynamic Weight Transfer ----------------
    d_long = mass * accel * cg_height / wheelbase
    d_lat = mass * lateral_accel * cg_height / track

    load_FL = F_front - d_long / 2 + d_lat / 2
    load_FR = F_front - d_long / 2 - d_lat / 2
    load_RL = F_rear + d_long / 2 + d_lat / 2
    load_RR = F_rear + d_long / 2 - d_lat / 2

    loads = [load_FL, load_FR, load_RL, load_RR]
    nominal_load = mass * g / 4

    pressures = []
    new_temps = []

    # ---------------- Per Tire ----------------
    for i in range(4):

        temp = tire_temps[i]

        # Heat generation
        temp += (
            0.002 * speed_kmh +
            0.015 * brake_force +
            0.3 * abs(accel) +
            0.2 * abs(lateral_accel) -
            0.03 * (temp - ambient_temp)
        ) * dt

        new_temps.append(temp)

        # Ideal gas law
        pressure = base_pressure * ((temp + 273.15) / (20.0 + 273.15))

        # Load effect
        pressure += 0.00018 * (loads[i] - nominal_load)

        # High-speed heating
        pressure += 0.005 * speed_kmh / 100.0

        # Slow puncture
        pressure -= leak_rates[i] * dt

        pressures.append(round(pressure, 2))

    return pressures, new_temps