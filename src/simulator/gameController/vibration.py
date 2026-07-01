from evdev import InputDevice, ecodes, ff

controller = None
try:
    controller = InputDevice("/dev/input/event10")
    print("Controller connected.")
except (FileNotFoundError, OSError):
    print("No controller detected. Continuing without controller.")
MAX_RPM = 7000
current_effect = None


def set_engine_rumble(rpm):
    global current_effect
    if controller is None:
        return
    # Clamp RPM
    rpm = max(0, min(rpm, MAX_RPM))

    # Scale to 0-65535
    intensity = int((rpm / MAX_RPM) * 0xFFFF)

    effect = ff.Effect(
        ecodes.FF_RUMBLE,
        -1,
        0,
        ff.Trigger(0, 0),
        ff.Replay(200, 0),   # Effect lasts 200 ms
        ff.EffectType(
            ff_rumble_effect=ff.Rumble(
                strong_magnitude=intensity,
                weak_magnitude=intensity // 2
            )
        )
    )

    # Remove previous effect
    if current_effect is not None:
        try:
            controller.erase_effect(current_effect)
        except OSError:
            pass

    current_effect = controller.upload_effect(effect)
    controller.write(ecodes.EV_FF, current_effect, 1)
