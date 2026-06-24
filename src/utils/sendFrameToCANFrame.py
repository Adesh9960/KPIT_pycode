from data_structures.CANFrame import CANFrame
from can import Message
def sendFrameToCANFrame(frame: Message) -> CANFrame:
    return CANFrame(
        timestamp_ns= frame.timestamp,
        can_id=frame.arbitration_id,
        dlc = frame.dlc,
        data= frame.data,
        is_extended= frame.is_extended_id,
        is_fd= frame.is_fd,
        is_error= frame.is_error_frame
    )