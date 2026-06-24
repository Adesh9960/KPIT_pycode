from simulator.actuators.actuator import Control
from simulator.actuators.actuatorList import ACTUATORS_DB
import simulator.uds.negativeResponse as negative_response

def handleInputOutputControl(payload: bytearray):

    print("InputOutputControl")

    if len(payload) < 4:
        return negative_response.create_negative_response(
            0x2F,
            negative_response.NRC_INCORRECT_MESSAGE_LENGTH
        )

    actuator_id = int.from_bytes(payload[1:3], "big")

    actuator = ACTUATORS_DB.get(actuator_id)

    if actuator is None:
        return negative_response.create_negative_response(
            0x2F,
            negative_response.NRC_REQUEST_OUT_OF_RANGE
        )

    try:
        control = Control(payload[3])
    except ValueError:
        return negative_response.create_negative_response(
            0x2F,
            negative_response.NRC_SUBFUNCTION_NOT_SUPPORTED
        )

    match control:

        case Control.ECU:

            actuator.control = Control.ECU

            print(
                f"{actuator.name}: "
                "Control returned to ECU"
            )

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value
            ])

        case Control.RESET:

            actuator.control = Control.RESET
            actuator.state = False

            print(
                f"{actuator.name}: "
                "Reset to default"
            )

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value
            ])

        case Control.FREEZE:

            actuator.control = Control.FREEZE

            print(
                f"{actuator.name}: "
                f"Frozen at {actuator.state}"
            )

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value
            ])

        case Control.ADJUST:

            if len(payload) != 5:
                return negative_response.create_negative_response(
                    0x2F,
                    negative_response.NRC_INCORRECT_MESSAGE_LENGTH
                )

            actuator.control = Control.ADJUST
            actuator.state = bool(payload[4])

            print(
                f"{actuator.name}: "
                f"{'ON' if actuator.state else 'OFF'}"
            )

            return bytearray([
                0x6F,
                payload[1],
                payload[2],
                control.value,
                payload[4]
            ])