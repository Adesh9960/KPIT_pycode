from logger.logger import write_log

def lookup_message_definition(can_id: int, message_map : dict):
        lookup_id = can_id & ~0x80000000
        msg_def = message_map.get(lookup_id)

        if msg_def is None :
            # print(
            #     f"[Miss] Unknown CAN ID: "
            #     f"{hex(can_id)}"
            #  )
            write_log(f"[Warning] Unknown CAN ID : {hex(can_id)}")
            return None

        # print(
        #     f"[HIT] Found definitation: "
        #     f"{msg_def.name}"
        # )

        return msg_def
