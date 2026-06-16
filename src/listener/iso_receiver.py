import time
import listener.main as main
from data_structures.CANFrame import CANFrame

def iso_receiver(receive_callback):
    
    while True:
        if main.stack.available():
            print("iso message received")
            payload = main.stack.recv()   # Reads from ISO-TP buffer, NOT the CAN bus
            uds_message = CANFrame(
                timestamp_ns= time.time_ns(),
                can_id=main.rxid,
                dlc = len(payload),
                data=bytes(payload),
                is_extended=main.last_is_extended,
                is_fd=main.last_is_fd,
                is_error=False
            )
            # HeartBeat from ECU
            if payload[0] == 0x3E : 
                pass
            if receive_callback is not None:
                receive_callback(payload)
