# Logger Unit Tests

This document describes the unit tests implemented for the Logger module and provides instructions for executing them.

## Running the Unit Tests

From the `src` directory, execute the following command:

```bash
python -m unittest discover -s ../tests/logger
```

This command discovers and executes all unit tests located in the `tests/logger` directory.

## Unit Test Descriptions

| **Test Case**                     | **Description**                                                                                                                                                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_single_frame()`             | Verifies that the `frames_to_logs()` function correctly converts a single `CANFrame` object into a log entry. Ensures that one log record is generated and contains the expected timestamp and CAN identifier.              |
| `test_start_initializes_logger()` | Verifies that the `start()` function correctly initializes the logger service by setting the running state, creating the ring buffer, and starting the background write thread.                                             |
| `test_push_frame()`               | Verifies that the `write_log()` function successfully inserts a `CANFrame` into the logger's ring buffer. Ensures that the frame is stored correctly and that its CAN identifier matches the transmitted value.             |
| `test_stop()`                     | Verifies that the `stop()` function flushes pending log data to the CSV writer during logger shutdown. The test mocks file-writing operations to confirm that the CSV writer is invoked without performing actual file I/O. |

## Expected Result

If all tests pass successfully, the output will resemble:

```text
....
----------------------------------------------------------------------
Ran 4 tests in <execution_time>s

OK
```

A successful execution confirms that the logger module correctly:

* Converts CAN frames into log records.
* Initializes the logging service and its required resources.
* Buffers CAN frames in the ring buffer.
* Flushes buffered log data during shutdown.
