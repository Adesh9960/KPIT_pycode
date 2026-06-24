class TransmissionError(Exception):
    """
    Raised when a CAN frame cannot be transmitted.
    """

    def __init__(
        self,
        arbitration_id: int | None = None
    ):
        self.arbitration_id = arbitration_id

        super().__init__()