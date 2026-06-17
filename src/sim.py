from simulator.uds.uds import handle_tester_request
import listener.listener as listener

listener.start(handle_tester_request)  