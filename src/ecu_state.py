"""
ECU Shared State  —  used by app.py and the uds/ handlers.

This module provides session, security, and actuator state for the Flask process.
Parameters.py (the signal generator) runs as a SEPARATE process and manages its
own internal state.  The two share data only through the CSV file.
"""

from enum import Enum


# ─── Diagnostic Session ────────────────────────────────────────
SESSION_DEFAULT     = 0x01
SESSION_EXTENDED    = 0x03
SESSION_PROGRAMMING = 0x02

session_level = SESSION_DEFAULT


# ─── Security Access ───────────────────────────────────────────
security_level = 0
security_key   = None
_pending_seed  = None          # last seed sent to tester

# ─── DTC State ─────────────────────────────────────────────────
active_dtcs = ["P0102", "P0113", "U0100"]  # Simulated active faults

# ─── Firmware Flash State (0x34, 0x36, 0x37) ───────────────────
class FlashState:
    IDLE = 0
    DOWNLOADING = 1

flash_status = FlashState.IDLE
flash_expected_size = 0
flash_buffer = bytearray()
flash_block_sequence = 1
MAX_BLOCK_SIZE = 1024  # Standard block size for CAN UDS


# ─── Firmware Upload ───────────────────────────────────────────
upload_active  = False
upload_offset  = 0
firmware_image = b'\x00' * 256  # placeholder firmware image


# ─── Actuator Control ──────────────────────────────────────────
class Control(Enum):
    ECU    = 0x00
    RESET  = 0x01
    FREEZE = 0x02
    ADJUST = 0x03


class Actuator:
    """Represents a controllable actuator on the ECU."""
    def __init__(self, name: str, did: int, state: bool = False):
        self.name    = name
        self.did     = did
        self.state   = state
        self.control = Control.ECU


head_lamp    = Actuator("Head Lamp",    0xF410)
radiator_fan = Actuator("Radiator Fan", 0xF411)
fuel_pump    = Actuator("Fuel Pump",    0xF412)

ACTUATORS_DB = {
    0xF410: head_lamp,
    0xF411: radiator_fan,
    0xF412: fuel_pump,
}
