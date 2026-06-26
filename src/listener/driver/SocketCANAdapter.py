from .CANconfig import CANConfig
from data_structures.CANFrame import CANFrame
from data_structures.BusStatistics import BusStatistics
from errors.TransmissionError import TransmissionError
import subprocess
import can
import re
from enum import Enum, auto
class BusState(Enum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    ERROR = "ERROR"

class SocketCANAdapter:
    config: CANConfig
    stats: BusStatistics
    bus: can.BusABC | None
    notifier: can.Notifier | None
    listeners: list[can.Listener]
    def __init__(self, config: CANConfig, listeners: list[can.Listener] = []):
        self.config = config
        self.stats = BusStatistics()
        self.listeners = listeners
    def open(self):
        print("SocketCAN opening started")
        subprocess.run(
            ["ip", "link", "set", self.config.channel, "down"],
            check=True,
        ) 
        if self.config.fd_enabled:
            subprocess.run([
                "ip", "link", "set", self.config.channel, "up",
                "type", "can",
                "bitrate", str(self.config.bitrate),
                "dbitrate", str(self.config.data_bitrate),  # e.g. 2000000
                "fd", "on",
                "restart-ms", str(self.config.restart_ms),
            ], check=True)
        else:
            subprocess.run([
                "ip", "link", "set", self.config.channel, "up",
                "type", "can",
                "bitrate", str(self.config.bitrate),
                "restart-ms", str(self.config.restart_ms),
            ], check=True)

        subprocess.run(
            ["ip", "link", "set", self.config.channel, "up"],
            check=True,
        )
        if self.config.fd_enabled:
            self.bus = can.Bus(interface=self.config.interface, channel=self.config.channel, fd=True)
        else:
            self.bus = can.Bus(interface=self.config.interface, channel=self.config.channel)
        
        self.notifier = can.Notifier(
            bus=self.bus,
            listeners=self.listeners
        )
        print("SocketCAN opened")
        
    def close(self):
        if self.bus is not None:
            self.bus.shutdown()
        self.bus = None


    def get_bus_state(self) -> BusState:
        result = subprocess.run(
            ["ip","-details","link","show",self.config.channel],
            capture_output=True, text=True, 
            check=True
        )
        output = result.stdout
        matcher = re.search(r"can state (\S+)", output)
        if matcher: 
            bus_state = matcher.group(1)
            match bus_state:
                case "ERROR-ACTIVE":
                    return BusState.ACTIVE
                case "ERROR-PASSIVE":
                    return BusState.PASSIVE
                case _:
                    return BusState.ERROR
            return bus_state
        return BusState.ERROR
    
    def send(self, frame: can.Message):
        msg = can.Message(
        arbitration_id=frame.arbitration_id,
        data=frame.data,
        is_extended_id=frame.is_extended_id,
        is_fd=frame.is_fd
        )
        try:
            self.bus.send(msg)
            self.stats.tx_frames += 1
            # print(self.stats.tx_frames)
        except can.CanError as e:
            self.stats.tx_error_frames += 1
            print(f"Error frame \n ID: {hex(msg.arbitration_id)}\n is_extended_id: {msg.is_extended_id}\n is_fd: {msg.is_fd}\n len(data): {len(msg.data)}\n data: {msg.data.hex()}")
            raise TransmissionError(msg.arbitration_id)
    
    def clear_filter(self):
        self.bus.set_filters([])

    def set_filter(self, filter_list: list):
        self.bus.set_filters(filter_list)

    def get_statistics(self) -> BusStatistics:
        result = subprocess.run(
            ["ip", "-details", "-statistics", "link", "show", self.config.channel],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout

        # Bus state
        state_match = re.search(r"can state (\S+)", output)
        if state_match:
            self.stats.bus_state = state_match.group(1)
    
        # RX/TX packets
        rx_match = re.search(r"RX:\s+bytes\s+packets\s+errors.*?\n\s*\d+\s+(\d+)\s+(\d+)",
                             output, re.DOTALL)
        tx_match = re.search(r"TX:\s+bytes\s+packets\s+errors.*?\n\s*\d+\s+(\d+)\s+(\d+)",
                             output, re.DOTALL)
    
        if rx_match:
            self.stats.rx_frames = int(rx_match.group(1))
            self.stats.rx_errors = int(rx_match.group(2))
    
        if tx_match:
            self.stats.tx_frames = int(tx_match.group(1))
            self.stats.tx_errors = int(tx_match.group(2))
    
        # Bus-off counter
        busoff_match = re.search(r"bus-off\s+(\d+)", output)
        if busoff_match:
            self.stats.bus_off_count = int(busoff_match.group(1))
    
        return self.stats
    
    
        

