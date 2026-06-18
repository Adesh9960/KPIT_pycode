import pandas as pd
import cantools
import can
import time
from msg_map import MESSAGE_MAP
# from listener.TxRequest import TxRequest, TxRequestType
# from listener.listener import send_to_tx_queue

db = cantools.database.load_file("Vehicle.dbc")
last_processed_row = 0
sequence_number = 0
CAN_FD_Mask = 0x80000000

while True:
    try:
        with open(r"A:\KPIT_Internship\pycode\src\Data_generation\engine_telemetry_log.csv", "r") as f:
            df = pd.read_csv(f)

        current_row = len(df)
        if current_row > last_processed_row:
            new_rows = df.iloc[last_processed_row:current_row]

            for _, row in new_rows.iterrows():
                for msg_name, msg_config in MESSAGE_MAP.items():
                    try:
                        raw_id = msg_config["can_id"]
                        is_extended = msg_config["is_extended"]
                        is_fd = msg_config["is_fd"]
                        lookup_id = raw_id | CAN_FD_Mask if is_extended else raw_id

                        try:
                            msg_def = db.get_message_by_frame_id(lookup_id)
                        except KeyError:
                            print(f"[SKIP] {msg_name} not found in DBC.")
                            continue

                        if is_fd:
                            print("CAN FD is Detected")
                        else:
                            print("Classical CAN Frame")

                        # map telemetry CSV columns to DBC signal names
                        signals = {
                            dbc_signal: float(row[csv_col])
                            for dbc_signal, csv_col in msg_config["signals"].items()
                        }

                        for signal in msg_def.signals:
                            val = signals[signal.name]
                            if not (signal.minimum <= val <= signal.maximum):
                                print(f"[WARN] {signal.name}={val} out of range [{signal.minimum},{signal.maximum}]")

                        payload = msg_def.encode(signals)

                        frame = can.Message(
                            arbitration_id=raw_id,
                            data=payload,
                            dlc=msg_config["dlc"],
                            is_extended_id=is_extended,
                            is_fd=is_fd
                        )

                        # # To send to queue
                        # request = TxRequest(
                        #     priority=1,
                        #     enqueue_timestamp_ns=time.time_ns(),
                        #     request_id=int(time.time_ns()),
                        #     request_type=TxRequestType.RAWCAN,
                        #     payload=frame,
                        #     max_retries=3,
                        #     timeout_ms=1000,
                        #     uds_error_callback=None,
                        #     confirmation_callback=None
                        # )
                        # send_to_tx_queue(request)

                        sequence_number += 1
                        print(f"[SEQ #{sequence_number}] [{msg_name}] {frame}")

                    except Exception as e:
                        print(f"[ROW ERROR] {msg_name}: {e} — skipping")
                        continue

            last_processed_row = current_row

    except Exception as e:
        print(f"[ERROR] {e}")

    