import spidev
import time

# ─────────────────────────────────────────
# MCP2515 SPI COMMAND CONSTANTS
# ─────────────────────────────────────────
MCP_RESET    = 0xC0   # Reset command — restores all registers to default
MCP_READ     = 0x03   # Read register command
MCP_WRITE    = 0x02   # Write register command
MCP_READ_STATUS = 0xA0  # Quick status read command

# ─────────────────────────────────────────
# MCP2515 REGISTER ADDRESSES
# ─────────────────────────────────────────
REG_CANSTAT  = 0x0E   # CAN Status Register
REG_CANCTRL  = 0x0F   # CAN Control Register
REG_CNF1     = 0x2A   # Baud Rate Config 1
REG_CNF2     = 0x29   # Baud Rate Config 2
REG_CNF3     = 0x28   # Baud Rate Config 3
REG_TXB0CTRL = 0x30   # Transmit Buffer 0 Control
REG_RXB0CTRL = 0x60   # Receive Buffer 0 Control

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def read_register(spi, address):
    """
    Read a single register from MCP2515.
    Protocol: Send [READ_CMD, ADDRESS, 0x00]
    MCP2515 sends back the register value in the 3rd byte.
    """
    response = spi.xfer2([MCP_READ, address, 0x00])
    return response[2]


def write_register(spi, address, value):
    """
    Write a single byte to a register on MCP2515.
    Protocol: Send [WRITE_CMD, ADDRESS, DATA]
    """
    spi.xfer2([MCP_WRITE, address, value])


def reset_mcp2515(spi):
    """
    Send software reset to MCP2515.
    After reset, chip enters Configuration Mode (CANSTAT = 0x80).
    """
    spi.xfer2([MCP_RESET])
    time.sleep(0.1)   # Give chip 100ms to reset fully


def get_mode_name(canstat_value):
    """
    Decode CANSTAT register value into a human-readable mode name.
    Bits 7-5 of CANSTAT hold the operation mode.
    """
    mode_bits = (canstat_value >> 5) & 0x07
    modes = {
        0b000: "Normal Mode",
        0b001: "Sleep Mode",
        0b010: "Loopback Mode",
        0b011: "Listen-Only Mode",
        0b100: "Configuration Mode"
    }
    return modes.get(mode_bits, f"Unknown Mode ({bin(mode_bits)})")


# ─────────────────────────────────────────
# MAIN VERIFICATION FUNCTION
# ─────────────────────────────────────────

def check_mcp2515_response():
    """
    Full MCP2515 connectivity and response verification.
    Steps:
      1. Open SPI
      2. Send RESET command
      3. Read CANSTAT — should return 0x80 (Configuration Mode)
      4. Read CANCTRL — verify control register
      5. Write a test value to CNF1, read it back
      6. Read quick status
      7. Report PASS or FAIL with reasons
    """

    print("=" * 55)
    print("  MCP2515 CONNECTIVITY CHECK")
    print("=" * 55)

    # ── Step 1: Open SPI ──────────────────────────────────
    spi = spidev.SpiDev()
    spi.open(0, 1)                    # Bus 0, Chip Select 0 (CE0)
    spi.max_speed_hz = 1_000_000      # 1 MHz — safe starting speed
    spi.mode = 0b00                   # MCP2515 requires SPI Mode 0,0
    spi.bits_per_word = 8

    print(f"\n[SPI] Opened successfully")
    print(f"      Speed : {spi.max_speed_hz} Hz")
    print(f"      Mode  : {spi.mode}")

    results = []   # Will store PASS/FAIL for each test

    # ── Step 2: Send RESET ───────────────────────────────
    print("\n[TEST 1] Sending RESET command (0xC0)...")
    reset_mcp2515(spi)
    print("         Reset sent. Waiting 100ms for chip to settle...")
    print("         DONE")
    results.append(("RESET command sent", True))

    # ── Step 3: Read CANSTAT ─────────────────────────────
    print("\n[TEST 2] Reading CANSTAT register (0x0E)...")
    canstat = read_register(spi, REG_CANSTAT)
    mode_name = get_mode_name(canstat)

    print(f"         Raw value  : {hex(canstat)} ({bin(canstat)})")
    print(f"         Mode bits  : {bin((canstat >> 5) & 0x07)}")
    print(f"         Mode name  : {mode_name}")

    if canstat == 0x80:
        print("         RESULT     : PASS — MCP2515 is alive and in Configuration Mode!")
        results.append(("CANSTAT = 0x80 (Config Mode)", True))
    elif canstat == 0x00:
        print("         RESULT     : FAIL — Got 0x00. Possible causes:")
        print("                      - MISO wire not connected")
        print("                      - Wrong SPI bus/device number")
        print("                      - MCP2515 not powered")
        results.append(("CANSTAT = 0x80 (Config Mode)", False))
    elif canstat == 0xFF:
        print("         RESULT     : FAIL — Got 0xFF. Possible causes:")
        print("                      - MISO line floating (not connected)")
        print("                      - SPI not enabled on Pi (run raspi-config)")
        print("                      - Chip not powered or damaged")
        results.append(("CANSTAT = 0x80 (Config Mode)", False))
    else:
        print(f"         RESULT     : PARTIAL — Got unexpected value {hex(canstat)}")
        print(f"                      Chip responded but not in expected mode")
        print(f"                      Mode detected: {mode_name}")
        results.append(("CANSTAT = 0x80 (Config Mode)", False))

    # ── Step 4: Read CANCTRL ─────────────────────────────
    print("\n[TEST 3] Reading CANCTRL register (0x0F)...")
    canctrl = read_register(spi, REG_CANCTRL)
    print(f"         Raw value  : {hex(canctrl)} ({bin(canctrl)})")

    # After reset, CANCTRL should be 0x87
    # Bits 7-5 = 100 (Config Mode), Bit 2-0 = 111 (OSM off, ABAT off, CLKOUT enabled)
    if canctrl == 0x87:
        print("         RESULT     : PASS — CANCTRL = 0x87 (expected default after reset)")
        results.append(("CANCTRL default value", True))
    else:
        print(f"         RESULT     : WARN — Expected 0x87, got {hex(canctrl)}")
        print("                      Chip is responding but register has unexpected value")
        results.append(("CANCTRL default value", False))

    # ── Step 5: Write and Read Back Test ─────────────────
    print("\n[TEST 4] Write-then-Read test on CNF1 register (0x2A)...")
    test_value = 0x55   # 01010101 in binary — easy to spot
    write_register(spi, REG_CNF1, test_value)
    time.sleep(0.01)
    read_back = read_register(spi, REG_CNF1)

    print(f"         Wrote      : {hex(test_value)} ({bin(test_value)})")
    print(f"         Read back  : {hex(read_back)} ({bin(read_back)})")

    if read_back == test_value:
        print("         RESULT     : PASS — Write/Read verified! SPI bidirectional works.")
        results.append(("Write/Read register test", True))
    else:
        print(f"         RESULT     : FAIL — Mismatch! Wrote {hex(test_value)}, got {hex(read_back)}")
        print("                      Possible causes:")
        print("                      - MOSI wire problem (Pi → MCP2515)")
        print("                      - MISO wire problem (MCP2515 → Pi)")
        print("                      - CS wire not connected properly")
        results.append(("Write/Read register test", False))

    # ── Step 6: Quick Status Read ─────────────────────────
    print("\n[TEST 5] Quick Status Read command (0xA0)...")
    status_response = spi.xfer2([MCP_READ_STATUS, 0x00])
    status_byte = status_response[1]
    print(f"         Status byte: {hex(status_byte)} ({bin(status_byte)})")
    print(f"         Bit 7 (TXB2REQ) : {'1 - TX buffer 2 pending' if (status_byte >> 7) & 1 else '0'}")
    print(f"         Bit 4 (TXB1REQ) : {'1 - TX buffer 1 pending' if (status_byte >> 4) & 1 else '0'}")
    print(f"         Bit 2 (TXB0REQ) : {'1 - TX buffer 0 pending' if (status_byte >> 2) & 1 else '0'}")
    print(f"         Bit 0 (RX1IF)   : {'1 - Message in RX buffer 1' if (status_byte >> 0) & 1 else '0'}")
    results.append(("Quick status read", True))

    # ── Step 7: Read All Config Registers ────────────────
    print("\n[TEST 6] Reading baud rate config registers...")
    cnf1 = read_register(spi, REG_CNF1)
    cnf2 = read_register(spi, REG_CNF2)
    cnf3 = read_register(spi, REG_CNF3)
    print(f"         CNF1 (0x2A) : {hex(cnf1)}")
    print(f"         CNF2 (0x29) : {hex(cnf2)}")
    print(f"         CNF3 (0x28) : {hex(cnf3)}")
    results.append(("Config registers readable", True))

    # ── Final Summary ─────────────────────────────────────
    spi.close()

    print("\n" + "=" * 55)
    print("  FINAL SUMMARY")
    print("=" * 55)

    passed = 0
    failed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "+" if result else "X"
        print(f"  [{symbol}] {status} — {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n  Total: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n  OVERALL: MCP2515 is connected and responding correctly!")
        print("           You can proceed to Layer 2 (SocketCAN setup).")
    elif passed >= 2:
        print("\n  OVERALL: Partial connection — chip is alive but has issues.")
        print("           Check wiring of MOSI, MISO, CS pins carefully.")
    else:
        print("\n  OVERALL: MCP2515 not responding — check hardware first.")
        print("           Verify: SPI enabled, 3.3V power, all 5 wires connected.")

    print("=" * 55)


# ─────────────────────────────────────────
# RUN THE CHECK
# ─────────────────────────────────────────
check_mcp2515_response()