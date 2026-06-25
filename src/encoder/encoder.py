import cantools
import can
from encoder.msg_map import MESSAGE_MAP
from listener.TxRequest import TxRequest, TxRequestType
from listener.listener import send_to_tx_queue
from data_structures.CANFrame import CANFrame
import time

db = cantools.database.load_file("encoder/Vehicle.dbc")
sequence_number = 0
CAN_FD_Mask = 0x80000000


def encode_frame(telemetry_row: dict):
    global sequence_number

    for msg_name, msg_config in MESSAGE_MAP.items():
        try:
            raw_id = msg_config["can_id"]
            is_extended = msg_config["is_extended"]
            is_fd = msg_config["is_fd"]

            # add of 0x80000000
            lookup_id = raw_id | CAN_FD_Mask if is_extended else raw_id

            # If Id not found in dbc
            try:
                msg_def = db.get_message_by_frame_id(lookup_id)
            except KeyError:
                print(f"[SKIP] {msg_name} not found in DBC.")
                continue

            # map telemetry CSV columns to DBC signal names
            signals = {
                dbc_signal: float(telemetry_row[csv_col])
                for dbc_signal, csv_col in msg_config["signals"].items()
            }

            # for checking if signal are within min,max value
            for signal in msg_def.signals:
                val = signals[signal.name]
                if not (signal.minimum <= val <= signal.maximum):
                    print(f"[WARN] {signal.name}={val} out of range [{signal.minimum},{signal.maximum}]")

            # encodes the bytes and signal
            payload = msg_def.encode(signals)

            # maps and create can frame
            frame = can.Message(
                arbitration_id=raw_id,
                data=payload,
                dlc=msg_config["dlc"],
                is_extended_id=is_extended,
                is_fd=is_fd
            )
            # frame = CANFrame(
            #     timestamp_ns= time.time_ns(),
            #     can_id = raw_id,
            #     dlc = msg_config["dlc"],
            #     data=payload,
            #     is_extended=is_extended,
            #     is_fd=is_fd,
            #     is_error=False
            # )
            # if raw_id == 0x100 or raw_id == 0x200 or raw_id == 0x400 or raw_id == 0x101 or raw_id == 0x18FF0500:
                # To send to queue
            request = TxRequest(
                priority=1,
                enqueue_timestamp_ns=time.time_ns(),
                request_id=int(time.time_ns()),
                request_type=TxRequestType.RAWCAN,
                payload=frame,
                max_retries=3,
                timeout_ms=1000,
                uds_error_callback=None,
                confirmation_callback=None
            )
            send_to_tx_queue(request)
            # main.can_queue.put(frame)

            # add sequence no. to each can frame
            sequence_number += 1
            # print(f"[SEQ #{sequence_number}] [{msg_name}] {frame}")

        except Exception as e:
            # print(f"[ROW ERROR] {msg_name}: {e} — skipping")
            continue