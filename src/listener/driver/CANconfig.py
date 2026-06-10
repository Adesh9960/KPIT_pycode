from dataclasses import dataclass
@dataclass
class CANConfig:
	interface: str # socketcan, pcan, kvaser
	channel: str # can0, PCAN_USBBUS1
	bitrate: int
	fd_enabled: bool = False
	data_bitrate: int | None = None
	restart_ms: int