def snapshot_to_bytes(snapshot):
    data = bytearray()

    data.extend(snapshot["Speed"].to_bytes(2, "big"))
    data.extend(snapshot["RPM"].to_bytes(2, "big"))
    data.extend(snapshot["CoolantTemp"].to_bytes(1, "big"))

    return bytes(data)