import listener.main as main

iso_rx_count = 0
def iso_receiver(receive_callback):
    global iso_rx_count
    while True:
        if main.stack.available():
            print("iso message received")
            payload = main.stack.recv()   # Reads from ISO-TP buffer, NOT the CAN bus
            print("ISO payload: :", payload)
            print("RX ISO COUNT: ", iso_rx_count)
            iso_rx_count += 1
            # HeartBeat from ECU
            if payload[0] == 0x3E : 
                pass
            if receive_callback is not None:
                receive_callback(payload)
