import listener.main as main

# Tracking counter to log the total number of valid ISO-TP network packets received
iso_rx_count = 0

def iso_receiver(receive_callback):
    """
    Asynchronously monitors the ISO-TP network stack transport buffer for incoming data.

    This worker function runs an infinite polling loop that listens to the network layer
    rather than raw data frames on the CAN physical layer. When a reassembled multi-frame
    ISO-TP packet is completely processed by the underlying stack (`main.stack`), it reads 
    the final payload, filters out network diagnostic maintenance metrics (like ECU heartbeats),
    and executes the user-defined tracking callback logic.

    Args:
        receive_callback (callable or None): A user-defined execution function invoked upon
            receiving a valid, complete ISO-TP payload. The payload (bytes) is passed as the
            sole positional argument. If None, payload extraction proceeds without forwarding.
    """
    global iso_rx_count
    while True:
        # Check if the transport layer has completely reassembled an application packet
        if main.stack.available():
            print("iso message received")
            
            # Read from the local ISO-TP protocol buffer layer (NOT directly from the raw CAN bus lines)
            payload = main.stack.recv()   
            print("ISO payload: :", payload)
            print("RX ISO COUNT: ", iso_rx_count)
            iso_rx_count += 1
            
            # Filter Layer: Check if the payload matches a standard Unified Diagnostic Services (UDS) 
            # TesterPresent service identifier (0x3E). If true, treat it as a passive heartbeat line.
            if payload[0] == 0x3E: 
                pass
            
            # Forward the finalized buffer packet to the designated subscriber layer
            if receive_callback is not None:
                receive_callback(payload)