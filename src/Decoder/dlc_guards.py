def validate_dlc(msg, msg_def) :

        expected_dlc = msg_def.length
        received_dlc = msg.dlc

        if received_dlc < expected_dlc :

            raise ValueError(
                f"DLC mismatch :"
                f"expected ={expected_dlc}"
                f"got ={received_dlc}"
            )

        return True