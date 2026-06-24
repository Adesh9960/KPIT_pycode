import logger.logger as logger
import listener.listener as listener
from encoder.encoder import encode
from uds_client.uds_client import UDS, UDSRoles
import Decoder.decoder_thread as decoder
import isotp

address = isotp.Address(
    isotp.AddressingMode.Normal_11bits,
    txid=0x22,
    rxid=0x62
)

uds_client = UDS(UDSRoles.USER)

listener.start(address, uds_client.on_response)
decoder.start()
logger.start()

vin = uds_client.readDataByIdentifier(0xF190)
# listener.test_transmission()
   
