import simulator.main as main
import simulator.Data_generation.Parameters as params

from simulator.uds.Session import Session


def handleDiagonisticSessionControl(payload: bytearray):

    print("DiagnosticSessionControl")

    if len(payload) != 2:
        return bytearray([0x7F, 0x10, 0x13])

    requested_session = payload[1]

    match requested_session:

        # Default Session
        case 0x01:

            main.session_level = Session.SESSION_DEFAULT

            return bytearray([
                0x50,
                0x01
            ])

        # Extended Session
        case 0x03:

            main.session_level = Session.SESSION_EXTENDED

            return bytearray([
                0x50,
                0x03
            ])

        # Programming Session
        case 0x02:

            if params.current_speed != 0:
                return bytearray([
                    0x7F,
                    0x10,
                    0x22  # Conditions Not Correct
                ])

            if params.battery_voltage <= 11:
                return bytearray([
                    0x7F,
                    0x10,
                    0x22  # Conditions Not Correct
                ])

            main.session_level = Session.SESSION_PROGRAMMING

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