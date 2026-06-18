# for validation of range
def validate_signals(msg_def, decoded_signals):

    signal_errors = {}

    frame_valid = True

    for signal in msg_def.signals:

        value = decoded_signals[signal.name]

        # Check minimum
        if (
            signal.minimum is not None
            and value < signal.minimum
        ):

            frame_valid = False

            signal_errors[signal.name] = {
                "value": value,
                "minimum": signal.minimum,
                "maximum": signal.maximum,
                "reason": "below_minimum"
            }

            continue

        # Check maximum
        if (
            signal.maximum is not None
            and value > signal.maximum
        ):

            frame_valid = False

            signal_errors[signal.name] = {
                "value": value,
                "minimum": signal.minimum,
                "maximum": signal.maximum,
                "reason": "above_maximum"
            }

    return frame_valid, signal_errors
