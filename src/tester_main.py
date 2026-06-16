import logger.logger as logger
import listener.listener as listener
from encoder.encoder import encode
from uds_client.uds_client import UDS, UDSRoles

uds_client = UDS(UDSRoles.USER)
listener.start(uds_client.on_response)
logger.start()
vin = uds_client.readDataByIdentifier(0x1F90)
encode()
# listener.test_transmission()
