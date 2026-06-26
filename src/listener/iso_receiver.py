import listener.main as main

def iso_receiver(receive_callback):
    
    while True:
        if main.stack.available():
            print("iso message received")
            payload = main.stack.recv()   # Reads from ISO-TP buffer, NOT the CAN bus
          
            # HeartBeat from ECU
            if payload[0] == 0x3E : 
                pass
            if receive_callback is not None:
                receive_callback(payload)
