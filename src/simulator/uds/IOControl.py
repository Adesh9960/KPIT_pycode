from simulator.actuators.actuator import Control
from simulator.actuators.actuatorList import ACTUATORS_DB
import simulator.uds.negativeResponse as negative_response

def handleInputOutputControl(payload: bytearray) -> bytearray:
    """
    Processes an incoming UDS InputOutputControlByIdentifier (Service 0x2F) message.

    This service allows a diagnostic tester to temporarily bypass standard ECU control 
    logic and manipulate, freeze, or reset physical actuators or signals within the simulator database.
    
    The expected request frame structure follows:
    `[SID=0x2F][DataID_High][DataID_Low][InputOutputControlParameter][ControlState (Optional)]`

    Supported control parameters (sub-functions):
    - **Control.ECU (0x00):** Return control of the actuator back to the ECU's standard internal logic.
    - **Control.RESET (0x01):** Reset the actuator state to its default values.
    - **Control.FREEZE (0x02):** Lock the actuator at its current active hardware state.
    - **Control.ADJUST (0x03):** Force the actuator state to a specific manual value (ON/OFF) provided in the payload.

    Args:
        payload (bytearray): Raw incoming request stream from the diagnostic tool interface.

    Returns:
        bytearray: A finalized response buffer containing a positive confirmation signature (0x6F) 
                   echoing the DataID and ControlParameter, or an explicit Negative Response Code frame.
    """
    print("InputOutputControl")

    # Step 1: Enforce standard structural frame validation bounds
    if len(payload) < 4:
        return negative_response.create_negative_response(
            0x2F,
            negative_response.NRC_INCORRECT_MESSAGE_LENGTH
        )

    # Step 2: Extract the 2-byte actuator Data Identifier (DID) from indices 1 and 2
    actuator_id = int.from_bytes(payload[1:3], "big")
    actuator = ACTUATORS_DB.get(actuator_id)

    if actuator is None:
        return negative_response.create_negative_response(
            0x2F,
            negative_response.NRC_REQUEST_OUT_OF_RANGE
        )

    # Step 3: Parse and validate the InputOutputControlParameter sub-function byte at index 3
    try:
        control = Control(payload[3])
    except ValueError:
        return negative_response.create_negative_response(
            0x2F,
            negative_response.NRC_SUBFUNCTION_NOT_SUPPORTED
        )

    # Step 4: Direct payload parameters into the state machine switchboard
    match control:

        case Control.ECU:
            actuator.control = Control.ECU
            print(f"{actuator.name}: Control returned to ECU")

            return bytearray([
                0x6F,        # Positive Response SID (0x2F + 0x40)
                payload[1],  # Echo Actuator DataID High Byte
                payload[2],  # Echo Actuator DataID Low Byte
                control.value
            ])

        case Control.RESET:
            actuator.control = Control.RESET
            actuator.state = False
            print(f"{actuator.name}: Reset to default")

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value
            ])

        case Control.FREEZE:
            actuator.control = Control.FREEZE
            print(f"{actuator.name}: Frozen at {actuator.state}")

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value
            ])

        case Control.ADJUST:
            # Short-circuit verification: Force-adjusting state variables requires exactly 5 bytes total
            if len(payload) != 5:
                return negative_response.create_negative_response(
                    0x2F,
                    negative_response.NRC_INCORRECT_MESSAGE_LENGTH
                )

            actuator.control = Control.ADJUST
            actuator.state = bool(payload[4]) # Coerce index 4 control values directly to boolean states
            print(f"{actuator.name}: {'ON' if actuator.state else 'OFF'}")

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value,
                payload[4] # Include the explicit control state argument back inside positive echo logs
            ])