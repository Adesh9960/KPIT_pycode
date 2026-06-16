import pandas as pd
import cantools
import can
import time
from listener.TxRequest import TxRequest, TxRequestType
from listener.listener import send_to_tx_queue


def encode():
    db = cantools.database.load_file("./encoder/Vehicle.dbc")
    last_processed_row = 0
    sequence_number = 0
    while True:
        df = pd.read_csv("./encoder/Vehicle.csv")
        current_row = len(df)

        if current_row > last_processed_row:
            new_rows = df.iloc[last_processed_row:current_row]

            for _, row in new_rows.iterrows():
                raw_id = int(row["can_id"], 16)
                is_extended = str(row["extended_id"]).lower() == "true"

                # cantools requires bit 31 set for extended frame lookups
                lookup_id = raw_id | 0x80000000 if is_extended else raw_id

                try:
                    msg_def = db.get_message_by_frame_id(lookup_id)
                except KeyError:
                    print(f"[SKIP] 0x{raw_id:X} not found in DBC.")
                    continue
                
                # to decide whether fd or not
                is_fd = str(row["is_fd"]).lower() == "true"

                if is_fd :
                    print("CAN FD is Detected")
                else:
                    print("Classical CAN Frame")


                signals = {signal.name: row[signal.name] for signal in msg_def.signals}

                for signal in msg_def.signals:
                     val = row[signal.name]
                     if not (signal.minimum <= val <= signal.maximum):
                        print(f"[WARN] {signal.name}={val} out of range [{signal.minimum},{signal.maximum}]")


                payload = msg_def.encode(signals)
                frame = can.Message(
                    arbitration_id=raw_id,      # ← still use the raw ID here
                    data=payload,
                    dlc=row["dlc"],
                    is_extended_id=is_extended,
                    is_fd=is_fd
                )
                print("encoded frame: ")
                print(frame)


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

                print(
                    f"Queued Frame: "
                    f"{hex(frame.arbitration_id)}"
                )

                sequence_number += 1
                print(f"[SEQ #{sequence_number}] {frame}")



            last_processed_row = current_row

        time.sleep(1)
