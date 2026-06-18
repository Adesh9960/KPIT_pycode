import pandas as pd
import cantools
import can
import time

db = cantools.database.load_file("Vehicle.dbc")
last_processed_row = 0
sequence_number = 0
CAN_FD_Mask = 0x80000000

while True:
    try:
        with open("Vehicle.csv", "r") as f:
            df = pd.read_csv(f)
        
        #gets new row entries
        current_row = len(df)
        if current_row > last_processed_row:
            new_rows = df.iloc[last_processed_row:current_row]

            # checks whether id is extended grab whatever text in extended_id and converts it into py bool
            for _, row in new_rows.iterrows():
                try:
                    raw_id = int(row["can_id"], 16)
                    is_extended = str(row["extended_id"]).lower() == "true"

                    # add of 0x80000000
                    lookup_id = raw_id | CAN_FD_Mask if is_extended else raw_id

                    # If Id not found in dbc
                    try:
                        msg_def = db.get_message_by_frame_id(lookup_id)
                    except KeyError:
                        print(f"[SKIP] 0x{raw_id:X} not found in DBC.")
                        continue

                    # to decide whether fd or not
                    is_fd = str(row["is_fd"]).lower() == "true"

                    if is_fd:
                        print("CAN FD is Detected")
                    else:
                        print("Classical CAN Frame")

                    # for checking if signal are within min,max value
                    signals = {
                        signal.name: float(row[signal.name])
                        for signal in msg_def.signals
                    }

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
                        dlc=row["dlc"],
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

                    # add sequence no. to each can frame
                    sequence_number += 1
                    print(f"[SEQ #{sequence_number}] {frame}")

                except Exception as e:
                    print(f"[ROW ERROR] {e} — skipping row")
                    continue

            last_processed_row = current_row 

    except Exception as e:
        print(f"[ERROR] {e}")

    # sleeps every 1 sec
    time.sleep(1)