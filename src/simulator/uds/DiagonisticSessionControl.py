import simulator.main as main
import simulator.uds.Session as Session
import simulator.uds.negativeResponse as negative_response

def handleDiagonisticSessionControl(payload: bytearray) -> bytearray:
    """
    Processes an incoming UDS DiagnosticSessionControl (Service 0x10) request.

    Manages transitions between distinct server execution environments:
    - **Default Session (0x01):** The initial, unrestricted startup state. 
      Drops high-tier security states and safe overrides.
    - **Extended Diagnostic Session (0x03):** Enables advanced diagnostics, 
      such as data writes and hardware IO adjustments.
    - **Programming Session (0x02):** Enables memory flashing routines. 
      Enforces strict physical interlocks before accepting the transition:
      1. The vehicle speed must be completely stationary ($\text{speed} == 0$).
      2. Operating voltage must be stable ($\text{battery voltage} > 11\text{V}$) to prevent block corruption.

    Args:
        payload (bytearray): The raw incoming request buffer structured as `[SID=0x10][DiagnosticSessionType]`.

    Returns:
        bytearray: A finalized positive response buffer (0x50 + Echoed Session Type) 
                   or a 3-byte Negative Response frame (0x7F) containing the matching NRC 
                   (e.g., 0x13 Incorrect Length, 0x22 Conditions Not Correct, 0x12 SubFunction Not Supported).
    """
    print("DiagnosticSessionControl")

    # Frame Check: Service 0x10 requests must strictly consist of exactly 2 bytes
    if len(payload) != 2:
        return bytearray([0x7F, 0x10, 0x13]) # NRC 0x13: IncorrectMessageLength
 
    requested_session = payload[1]
    
    # Global Session Check: Filter against the server configuration's overall support boundaries
    if requested_session not in Session.ALLOWED_SESSIONS:
        return negative_response.create_negative_response(
            payload[0], 
            negative_response.NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION
        )
        
    # State Machine Switching Core
    match requested_session:

        # Case 1: Default Session (0x01)
        case 0x01:
            main.session_level = Session.DEFAULT_SESSION
            return bytearray([
                0x50, # Positive Response Service Identifier (0x10 + 0x40)
                0x01  # Echoed Diagnostic Session Type
            ])

        # Case 2: Extended Diagnostic Session (0x03)
        case 0x03:
            main.session_level = Session.EXTENDED_SESSION
            return bytearray([
                0x50,
                0x03
            ])

        # Case 3: Programming Session (0x02)
        case 0x02:
            # Physical Safety Check: Ensure the vehicle is stationary before allowing software flashing
            if main.current_speed != 0:
                return bytearray([
                    0x7F,
                    0x10,
                    0x22  # NRC 0x22: ConditionsNotCorrect
                ])

            # Physical Safety Check: Verify sufficient supply voltage to maintain memory stability
            if main.battery_voltage <= 11:
                return bytearray([
                    0x7F,
                    0x10,
                    0x22  # NRC 0x22: ConditionsNotCorrect
                ])

            main.session_level = Session.PROGRAMMING_SESSION
            return bytearray([
                0x50,
                0x02
            ])

        # Fallback Case: Catch-all for unsupported sub-functions passing structural list checks
        case _:
            return bytearray([
                0x7F,
                0x10,
                0x12  # NRC 0x12: SubFunctionNotSupported
            ])