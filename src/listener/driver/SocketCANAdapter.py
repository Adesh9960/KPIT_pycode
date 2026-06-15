from .CANconfig import CANConfig
from data_structures.CANFrame import CANFrame
from data_structures.BusStatistics import BusStatistics
from errors.TransmissionError import TransmissionError
import subprocess
import can

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
            ["ip", "link", "set", "can0", "down"],
            check=True,
        ) 
        subprocess.run(
        [
          "ip","link","set",self.config.channel,"up",
            "type","can","bitrate",str(self.config.bitrate),
            "restart-ms",str(self.config.restart_ms)
        ],
        check=True
        )
        subprocess.run(
            ["ip", "link", "set", "can0", "up"],
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


    def get_bus_state(self) -> can.BusState:
        result = subprocess.run(
            ["ip","-details","link","show",self.config.channel],
            capture_output=True, text=True, 
            check=True
        )
        output = result.stdout
        print(output)
        return output
    
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
        except can.CanError as e:
            self.stats.tx_error_frames += 1
            raise TransmissionError(msg.arbitration_id)
    
    # def receive(self, timeout:float | None = None):
    #     msg = self.bus.recv(timeout)
    #     if msg is None:
    #         return None
        
    #     self.stats.rx_frames += 1
    #     if msg.is_error_frame:
    #         self.stats.error_frames += 1

    #     return CANFrame(
    #         timestamp_ns=int(msg.timestamp * 1_000_000_000),
    #         can_id=msg.arbitration_id,
    #         dlc=msg.dlc,
    #         data=msg.data,
    #         is_extended=msg.is_extended_id,
    #         is_fd=msg.is_fd,
    #         is_error=msg.is_error_frame
    #     )
    def clear_filter(self):
        self.bus.set_filters([])

    def set_filter(self, filter_list: list):
        self.bus.set_filters(filter_list)
    
    
        

