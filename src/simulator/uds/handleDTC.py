import simulator.main as main
def handle_read_dtc():
    response = bytearray([0x59, 0x02])

    for dtc in main.dtc_manager.get_all():
        response.extend(
            dtc.code.to_bytes(3, "big")
        )
        response.append(dtc.status)

    return bytes(response)

def clear_dtc():
    main.dtc_manager.clear_all()
    return bytes([0x54])

def get_snapshot(dtcCode):
    main.dtc_manager.get_snapshot(dtcCode)

