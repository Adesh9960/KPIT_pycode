import time
from simulator.DTC.DTC import DTC
class DTCManager:
    def __init__(self):
        self.dtcs = {}

    def set_dtc(self, code, description, snapshot):
        self.dtcs[code] = DTC(
            code=code,
            description=description,
            status=0x2F,
            timestamp=time.time(),
            snapshot=snapshot
        )
    def get_snapshot(self, code):
        dtc = self.dtcs.get(code)
        if(dtc): return dtc.snapshot
        else: return None

    def clear_dtc(self, code):
        self.dtcs.pop(code, None)

    def clear_all(self):
        self.dtcs.clear()

    def get_all(self):
        return list(self.dtcs.values())