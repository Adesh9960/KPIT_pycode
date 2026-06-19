import pandas as pd
import cantools
import can
import time

db = cantools.database.load_file("Vehicle.dbc")
last_processed_row = 0
sequence_number = 0
CAN_FD_Mask = 0x80000000

while True:
    df = pd.read_csv("Vehicle.csv")
    current_row = len(df)
    
    # gets new rows entries
    if current_row > last_processed_row:
        new_rows = df.iloc[last_processed_row:current_row]   
        
         # checks whether id is extended grab whatever text in extended_id and converts it into py bool
        for _, row in new_rows.iterrows():
            raw_id = int(row["can_id"], 16)
            is_extended = str(row["extended_id"]).lower() == "true"  

            # add of 0x80000000
            lookup_id = raw_id | CAN_FD_Mask  if is_extended else raw_id 

            # If Id not found in dbc
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

            # for checking if signal are within min,max value
            signals = {signal.name: row[signal.name] for signal in msg_def.signals} 
            
            for signal in msg_def.signals:
                 val = row[signal.name]
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

            # add sequence no. to each can frame
            sequence_number += 1
            print(f"[SEQ #{sequence_number}] {frame}")  
            

        last_processed_row = current_row

    # sleeps every 1 sec
    time.sleep(1) 
