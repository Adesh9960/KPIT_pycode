from dataclasses import dataclass
@dataclass
class CANConfig:
	interface: str # socketcan, pcan, kvaser
	channel: str # can0, PCAN_USBBUS1
	bitrate: int
	restart_ms: int
	fd_enabled: bool = False
	data_bitrate: int | None = None