import simulator.main as main
import simulator.uds.negativeResponse as negativeResponse

def handle_read_dtc():
    response = bytearray()

    response.append(0x59)   # Positive response
    response.append(0x02)   # Subfunction
    response.append(0xFF)   # Status mask

    for dtc in main.dtc_manager.get_all():
        response.extend(dtc.code.to_bytes(3, "big"))
        response.append(dtc.status)

    return bytes(response)

def handle_clear_dtc(data):
    # Security check
    if main.security_level < 2:
        return negativeResponse.create_negative_response(0x14, 0x33)

    if len(data) != 3:
        return negativeResponse.create_negative_response(0x14, 0x13)   # IncorrectMessageLength

    group = int.from_bytes(data, "big")

    # 0xFFFFFF means clear all DTCs
    if group == 0xFFFFFF:
        main.dtc_manager.clear_all()
    else:
        main.dtc_manager.clear_dtc(group)

    return bytes([0x54]) + data


def get_snapshot(dtcCode):
    main.dtc_manager.get_snapshot(dtcCode)

