import simulator.main as main

import simulator.uds.Session as Session
import simulator.uds.negativeResponse as negative_response


def handleDiagonisticSessionControl(payload: bytearray):

    print("DiagnosticSessionControl")

    if len(payload) != 2:
        return bytearray([0x7F, 0x10, 0x13])
 
    requested_session = payload[1]
    if requested_session not in Session.ALLOWED_SESSIONS:
        return negative_response.create_negative_response(payload[0], negative_response.NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION)
    match requested_session:

        # Default Session
        case 0x01:

            main.session_level = Session.DEFAULT_SESSION

            return bytearray([
                0x50,
                0x01
            ])

        # Extended Session
        case 0x03:

            main.session_level = Session.EXTENDED_SESSION

            return bytearray([
                0x50,
                0x03
            ])

        # Programming Session
        case 0x02:

            if main.current_speed != 0:
                return bytearray([
                    0x7F,
                    0x10,
                    0x22  # Conditions Not Correct
                ])

            if main.battery_voltage <= 11:
                return bytearray([
                    0x7F,
                    0x10,
                    0x22  # Conditions Not Correct
                ])

            main.session_level = Session.PROGRAMMING_SESSION

            return bytearray([
                0x50,
                0x02
            ])

        # Unsupported Session
        case _:

            return bytearray([
                0x7F,
                0x10,
                0x12  # SubFunction Not Supported
            ])