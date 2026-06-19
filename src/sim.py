from simulator.uds.uds import handle_tester_request
import listener.listener as listener
import logger.logger as logger
import isotp
from encoder.encoder import encode
address = isotp.Address(
    isotp.AddressingMode.Normal_11bits,
    txid=0x62,
    rxid=0x22
)

listener.start(address, handle_tester_request, "can1")  
logger.start()
# encode()