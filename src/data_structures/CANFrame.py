class CANFrame:
    timestamp_ns: int
    can_id: int
    dlc: int
    data: bytes
    is_extended: bool
    is_fd: bool
    is_error: bool
    def __init__(self, timestamp_ns, can_id, dlc, data, is_extended, is_fd, is_error):
        self.timestamp_ns = timestamp_ns
        self.can_id = can_id
        self.dlc = dlc
        self.data = data
        self.is_extended = is_extended
        self.is_fd = is_fd
        self.is_error = is_error