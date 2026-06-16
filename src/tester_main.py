import logger.logger as logger
import listener.listener as listener
from encoder.encoder import encode
listener.start()
logger.start()
encode()
# listener.test_transmission()
