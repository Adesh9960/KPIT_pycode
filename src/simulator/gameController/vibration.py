import os
from evdev import InputDevice, ecodes, ff, list_devices

# The selected input device instance, initialized as None until a match is discovered
controller: InputDevice | None = None

# Scan the system's /dev/input/ filesystem nodes to detect a compatible peripheral
for path in list_devices():
    dev = InputDevice(path)
    # Target peripheral check: Detect Sony DualShock/DualSense controllers by driver string names
    if "Sony" in dev.name:
        controller = dev
        break

try:
    if controller is not None:
        # Re-initialize or validate the active file descriptor handle for the input interface
        controller = InputDevice(controller.path)
        print("Controller connected.")
except (FileNotFoundError, OSError):
    print("No controller detected. Continuing without controller.")

# Define the peak upper boundary limit matching the engine simulation's redline bounds
MAX_RPM = 7000

# Tracks the active kernel-allocated force-feedback effect ID to allow clean lifecycle overrides
current_effect: int | None = None


def set_engine_rumble(rpm: float | int):
    """
    Translates simulation engine RPM indices directly into proportional controller vibration.

    This function updates the peripheral's dual-rumble motors by calculating a 
    proportional scalar mapped up to the standard 16-bit Linux force-feedback unsigned 
    integer spectrum (0x0000 to 0xFFFF). It uploads the new waveform properties directly into 
    the kernel ring-buffer, overrides active profiles, and executes an immediate pulse command.

    The force-feedback packet contains:
    - **Strong Magnitude:** Handles low-frequency rumble (simulating deep engine pistons).
    - **Weak Magnitude:** Handles high-frequency vibration (simulating higher mechanical revs).

    Args:
        rpm (float | int): The active simulated engine speed value used to scale intensity.
    """
    global current_effect
    
    # Short-circuit out of execution loops if no hardware interface handle is available
    if controller is None:
        return
        
    # Clamp inputs strictly between 0 and the redline boundary to prevent division or scaling errors
    rpm = max(0, min(rpm, MAX_RPM))

    # Scale the clamped percentage to the 16-bit Linux kernel threshold bounds: [0, 65535]
    intensity = int((rpm / MAX_RPM) * 0xFFFF)

    # Construct the Linux input force-feedback schema structure block
    effect = ff.Effect(
        ecodes.FF_RUMBLE, # Event category identifier tagging rumble events
        -1,               # Unique ID slot placeholder (assigned dynamically by the driver on upload)
        0,                # Direction orientation vector context (unused for basic non-directional rumble)
        ff.Trigger(0, 0), # External trigger button configuration rules
        ff.Replay(200, 0), # Waveform envelope timeline parameters: play for 200ms, delay 0ms before repeating
        ff.EffectType(
            ff_rumble_effect=ff.Rumble(
                strong_magnitude=intensity,     # Low-frequency motor power level
                weak_magnitude=intensity // 2   # High-frequency motor power level (halved for structural contrast)
            )
        )
    )

    # Clean-up Phase: Proactively free up limited kernel memory slots by deleting the old active wave ID
    if current_effect is not None:
        try:
            controller.erase_effect(current_effect)
        except OSError:
            # Catch exceptions gracefully if the effect expired naturally or was dropped by hardware resets
            pass

    # Execution Phase: Stream parameters directly down to the input subsystem socket lines
    if controller is not None:
        # Step 1: Upload the structure to driver memory allocations and receive a valid tracking token reference ID
        current_effect = controller.upload_effect(effect)
        
        # Step 2: Write an EV_FF event passing the tracking token ID and setting the play command flag state to 1
        controller.write(ecodes.EV_FF, current_effect, 1)