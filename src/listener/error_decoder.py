from data_structures.CANFrame import CANFrame
# Linux SocketCAN error flags
CAN_ERR_TX_TIMEOUT = 0x00000001
CAN_ERR_LOSTARB    = 0x00000002
CAN_ERR_CRTL       = 0x00000004
CAN_ERR_PROT       = 0x00000008
CAN_ERR_TRX        = 0x00000010
CAN_ERR_ACK        = 0x00000020
CAN_ERR_BUSOFF     = 0x00000040
CAN_ERR_BUSERROR   = 0x00000080
CAN_ERR_RESTARTED  = 0x00000100

error_timings = {}

def decode_error(frame: CANFrame):
    """
    Decode a SocketCAN error frame.

    Args:
        frame: CANFrame

    Returns:
        frame with details of human-readable error descriptions.
    """
    errors = []

    # Rate Limiting 
    last_error = error_timings.get((frame.can_id, bytes(frame.data))) 
    error_timings[(frame.can_id, bytes(frame.data))] = frame.timestamp_ns
    if last_error is not None:
        timeout = frame.timestamp_ns - last_error  
        if(timeout < 100 * 1000):
            return None
        
    if frame.can_id & CAN_ERR_TX_TIMEOUT:
        errors.append("TX timeout")

    if frame.can_id & CAN_ERR_LOSTARB:
        errors.append(
            f"Lost arbitration (bit {frame.data[0]})"
            if len(frame.data) > 0 else
            "Lost arbitration"
        )

    if frame.can_id & CAN_ERR_CRTL:
        errors.append("Controller error")

        if len(frame.data) > 1:
            status = frame.data[1]

            if status & 0x01:
                errors.append("RX overflow")

            if status & 0x02:
                errors.append("TX overflow")

            if status & 0x04:
                errors.append("RX warning")

            if status & 0x08:
                errors.append("TX warning")

            if status & 0x10:
                errors.append("RX passive")

            if status & 0x20:
                errors.append("TX passive")

    if frame.can_id & CAN_ERR_PROT:
        errors.append("Protocol violation")

    if frame.can_id & CAN_ERR_TRX:
        errors.append("Transceiver error")

    if frame.can_id & CAN_ERR_ACK:
        errors.append("ACK error (no acknowledgement received)")

    if frame.can_id & CAN_ERR_BUSOFF:
        errors.append("Bus-Off")

    if frame.can_id & CAN_ERR_BUSERROR:
        errors.append("Bus error")

    if frame.can_id & CAN_ERR_RESTARTED:
        errors.append("Controller restarted")
    

    frame.details =  "; ".join(errors)
    return frame

    

    