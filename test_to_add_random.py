import pandas as pd
import random
import time
import os

csv_file = "Vehicle.csv"

while True:

    new_row = {
        "timestamp": 0.0,      # Always 0.0
        "can_id": "0x100",
        "extended_id": False,
        "dlc": random.randint(1,16),
        "message": "VehicleData",
        "Speed": random.randint(0, 200),
        "RPM": random.randint(800, 5000),
        "Temp": random.randint(20, 120)
    }

    df = pd.DataFrame([new_row])

    df.to_csv(
        csv_file,
        mode='a',
        header=not os.path.exists(csv_file),
        index=False
    )

    print("Added:", new_row)

    time.sleep(2)