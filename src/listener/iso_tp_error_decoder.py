import isotp

class IsoTpErrorHandler:
    def __init__(self):
        self.error_count = 0
        self.last_error = None

    def __call__(self, error: isotp.IsoTpError):
        """
        Callback passed to the ISO-TP stack.
        """
        self.error_count += 1
        self.last_error = error

        print(
            "ISO-TP Error [%s]: %s",
            type(error).__name__,
            str(error)
        )

        if isinstance(error, isotp.FlowControlTimeoutError):
            print("Timed out waiting for Flow Control frame.")

        elif isinstance(error, isotp.ConsecutiveFrameTimeoutError):
            print("Timed out waiting for Consecutive Frame.")

        elif isinstance(error, isotp.WrongSequenceNumberError):
            print("Received Consecutive Frame with wrong sequence number.")

        elif isinstance(error, isotp.OverflowError):
            print("Receiver reported buffer overflow.")

        elif isinstance(error, isotp.UnexpectedFlowControlError):
            print("Unexpected Flow Control frame received.")

        elif isinstance(error, isotp.UnexpectedConsecutiveFrameError):
            print("Unexpected Consecutive Frame received.")

        else:
            print("Unhandled ISO-TP transport error.")

