import spidev
import time

# MCP2515 Instruction Opcodes (From the chip datasheet)
SPI_RESET       = 0xC0
SPI_WRITE       = 0x02
SPI_READ        = 0x03

# Target Hardware Register Addresses
# TXB0CTRL (Transmit Buffer 0 Control Register) is a safe read/write register at 0x30
TEST_REGISTER   = 0x30
TEST_VALUE      = 0x5A  # Binary: 01011010 (A distinct alternating bit pattern)

def run_raw_spi_test():
    # 1. Initialize SPI Bus 0, Chip Select 0
    spi = spidev.SpiDev()
    spi.open(0, 1)

    # Set safe, stable speed for jumper wires (1 MHz)
    spi.max_speed_hz = 500000
    spi.mode = 0b11  # MCP2515 operates on SPI Mode 0

    print("--- Initiating Raw SPI Bidirectional Test ---")

    try:
        # 2. Send a hardware RESET command to the MCP2515 over MOSI
        print("\nSending Reset command to MCP2515...")
        spi.xfer2([SPI_RESET])
        time.sleep(0.5) # Give the chip a moment to reboot internal circuits

        # 3. WRITE the test value to the chip register
        # We send a packet of 3 bytes: [Write-Cmd, Register-Address, Byte-To-Store]
        print(f"Writing value 0x{TEST_VALUE:02X} to register address 0x{TEST_REGISTER:02X}...")
        spi.xfer2([SPI_WRITE, TEST_REGISTER, TEST_VALUE])

        time.sleep(0.05)

        # 4. READ the value back from the chip register
        # To read, we send [Read-Cmd, Register-Address] over MOSI,
        # and append a dummy byte [0x00] to pulse the SCLK line so the chip can push data back over MISO.
        print("Requesting register read-back over MISO wire...")
        response = spi.xfer2([SPI_READ, TEST_REGISTER, 0x00])

        # The data byte returned from MISO will be sitting in the 3rd index slot of our transfer array
        returned_value = response[2]

        # 5. Verify the full-duplex transmission matches
        print("\n--- Test Results ---")
        print(f"Bytes Sent (MOSI): 0x{TEST_VALUE:02X}")
        print(f"Bytes Received (MISO): 0x{returned_value:02X}")

        if returned_value == TEST_VALUE:
            print("\n🎉 SUCCESS! Raw SPI is perfectly bidirectional.")
            print("The data traveled to the MCP2515 and back completely uncorrupted.")
        elif returned_value == 0x00 or returned_value == 0xFF:
            print("\n❌ ERROR: Received flat line data (0x00 or 0xFF).")
            print("Your Pi is pulsing the clock, but the MISO wire is disconnected or the chip has no power.")
        else:
            print("\n❌ ERROR: Data corruption detected.")
            print(f"Sent 0x{TEST_VALUE:02X} but got back 0x{returned_value:02X}. Check for loose wiring!")

    except Exception as e:
        print(f"An unexpected script error occurred: {e}")
    finally:
        spi.close()

if __name__ == "__main__":
    run_raw_spi_test()