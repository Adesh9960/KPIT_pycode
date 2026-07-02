import simulator.Data_generation.Parameters as parameters
import listener.listener as listener
from simulator.uds.uds import handle_tester_request
import isotp

address = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x62,
        rxid=0x22
)
listener.start(address, handle_tester_request, "vcan0", enable_logger=False)
parameters.run_vehicle_simulator()