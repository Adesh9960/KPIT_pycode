from .CANconfig import CANConfig
from data_structures.BusStatistics import BusStatistics
from errors.TransmissionError import TransmissionError
import subprocess
import can
import re
from enum import Enum

class BusState(Enum):
    """Enumeration representing the simplified physical health state of the CAN bus."""
    ACTIVE = "ACTIVE"       # Normal operational state; node fully participates in communication
    PASSIVE = "PASSIVE"     # Error-passive state; node can transmit but can only generate passive error frames
    ERROR = "ERROR"         # Catch-all for Bus-Off or unreadable interface error state

class SocketCANAdapter:
    """
    Hardware abstraction adapter wrapping Linux SocketCAN functionality.

    This adapter manages low-level operations for a specific CAN network interface,
    handling hardware initialization via shell commands (`ip link`), interface lifecycle,
    asynchronous packet notification registration, filtering, performance metrics scraping, 
    and thread-safe frame transmission.
    """
    config: CANConfig
    stats: BusStatistics
    bus: can.BusABC | None
    notifier: can.Notifier | None
    listeners: list[can.Listener]

    def __init__(self, config: CANConfig, listeners: list[can.Listener] = []):
        """
        Initializes the SocketCAN adapter wrapper instance.

        Args:
            config (CANConfig): Immutable configuration details containing bitrate, channel name, etc.
            listeners (list[can.Listener], optional): Callbacks attached to the asynchronous 
                notifier loop for intercepted frames. Defaults to [].
        """
        self.config = config
        self.stats = BusStatistics()
        self.listeners = listeners

    def open(self):
        """
        Brings down, reconfigures, sets up, and opens the system's Linux SocketCAN socket layer.

        Executes sequentially:
        1. Lowers the interface context to clear stale runtime operational configurations.
        2. Configures underlying hardware attributes (bitrate, fd properties, restart delays)
           by executing sub-process calls directly matching standard `ip link set` formats.
        3. Initialized the python-can raw bus socket abstract bindings.
        4. Links and fires up an active asynchronous background notification context thread.
        
        Raises:
            subprocess.CalledProcessError: If any of the shell command configurations fail.
        """
        print("SocketCAN opening started")
        # Step 1: Force interface down before applying changes
        subprocess.run(
            ["ip", "link", "set", self.config.channel, "down"],
            check=True,
        ) 
        
        # Step 2: Configure interface type and characteristics based on FD capability
        if self.config.fd_enabled:
            subprocess.run([
                "ip", "link", "set", self.config.channel, "up",
                "type", "can",
                "bitrate", str(self.config.bitrate),
                "dbitrate", str(self.config.data_bitrate),  # Data Phase bitrate for CAN FD (e.g., 2Mbps)
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

        # Ensure the interface status flag is explicitly set to active (UP)
        subprocess.run(
            ["ip", "link", "set", self.config.channel, "up"],
            check=True,
        )
        
        # Step 3: Instantiate python-can abstract bus handles binding to the kernel sockets
        if self.config.fd_enabled:
            self.bus = can.Bus(interface=self.config.interface, channel=self.config.channel, fd=True)
        else:
            self.bus = can.Bus(interface=self.config.interface, channel=self.config.channel)
        
        # Step 4: Fire up background worker loops responsible for dispatching incoming frames
        self.notifier = can.Notifier(
            bus=self.bus,
            listeners=self.listeners
        )
        print("SocketCAN opened")
        
    def close(self):
        """
        Gracefully terminates and closes down active bus connections.

        Ensures active thread notifications are canceled, file descriptors are cleared 
        internally, and resources are cleanly released back to the OS.
        """
        if self.bus is not None:
            self.bus.shutdown()
        self.bus = None

    def get_bus_state(self) -> BusState:
        """
        Queries the current kernel network interface link state using system commands.

        Invokes `ip -details link show <channel>` and processes stdout through regex
        matching to dynamically capture current physical hardware stability parameters.

        Returns:
            BusState: The current abstract representation matching ACTIVE, PASSIVE, or ERROR profiles.
        """
        result = subprocess.run(
            ["ip", "-details", "link", "show", self.config.channel],
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
        return BusState.ERROR
    
    def send(self, frame: can.Message):
        """
        Attempts immediate raw packet transmission onto the physical layer bus interface.

        Args:
            frame (can.Message): The target frame structure populated with payload and ID traits.

        Raises:
            TransmissionError: Custom wrapper payload passing failed arbitration metrics up 
                               if `can.CanError` triggers.
        """
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
            print(f"Error frame \n ID: {hex(msg.arbitration_id)}\n is_extended_id: {msg.is_extended_id}\n is_fd: {msg.is_fd}\n len(data): {len(msg.data)}\n data: {msg.data.hex()}")
            raise TransmissionError(msg.arbitration_id)
    
    def clear_filter(self):
        """Removes all applied reception filters, configuring the socket to accept all incoming traffic."""
        self.bus.set_filters([])

    def set_filter(self, filter_list: list):
        """
        Applies a predefined list of structured identifier mask rules to the socket layer filter.

        Args:
            filter_list (list): Configuration dictionaries specifying required 'can_id', 
                                'can_mask', and 'extended' validation logic.
        """
        self.bus.set_filters(filter_list)

    def get_statistics(self) -> BusStatistics:
        """
        Scrapes, parses, and updates real-time operational diagnostics parameters from the Linux kernel.

        Issues a detailed system statistics request and maps the output back to an 
        application `BusStatistics` metrics instance using regex grouping.

        Returns:
            BusStatistics: The synchronized local profile reference tracking cumulative frame performance indices.
        """
        result = subprocess.run(
            ["ip", "-details", "-statistics", "link", "show", self.config.channel],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout

        # Parse current Bus state
        state_match = re.search(r"can state (\S+)", output)
        if state_match:
            self.stats.bus_state = state_match.group(1)
    
        # Parse multi-line block capturing RX data packets and error tallies
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
    
        # Parse accumulated driver bus-off event triggers
        busoff_match = re.search(r"bus-off\s+(\d+)", output)
        if busoff_match:
            self.stats.bus_off_count = int(busoff_match.group(1))
    
        return self.stats