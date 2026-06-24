# UDS REST API Test Guide

This document contains example `curl` commands for testing all available REST endpoints exposed by the Flask UDS server.

## Base URL

```bash
http://localhost:5000
```

---

# 1. Read DID

Read a Diagnostic Identifier (DID) from the ECU.

### Request

```bash
curl http://localhost:5000/DID/61840
```

### Example Response

```json
{
  "status": "success",
  "data": "VIN123456789"
}
```

---

# 2. Write DID

Write data to a Diagnostic Identifier (DID).

### Request

```bash
curl -X POST http://localhost:5000/DID \
-H "Content-Type: application/json" \
-d '{
  "DID": 61838,
  "value": "KPIT002"
}'
```

### Example Response

```json
{
  "status": "success",
  "data": "Data written"
}
```

---

# 3. Download Logger Files

Downloads a ZIP archive containing all logger files.

### Request

```bash
curl http://localhost:5000/download/logger \
-o all_logs.zip
```

### Example Response

Downloaded file:

```text
all_logs.zip
```

---

# 4. Download Firmware

Triggers firmware upload and downloads the firmware image.

### Request

```bash
curl http://localhost:5000/download/firmware \
-o firmware.bin
```

### Example Response

Downloaded file:

```text
firmware.bin
```

> Note: Ensure the Flask route checks for:
>
> ```python
> if file == "firmware":
> ```
>
> instead of:
>
> ```python
> if file == "/firmware":
> ```

---

# 5. Security Access

Requests ECU security access.

## Level 1

```bash
curl http://localhost:5000/security_access/1
```

## Level 2

```bash
curl http://localhost:5000/security_access/2
```

## Level 3

```bash
curl http://localhost:5000/security_access/3
```

### Example Response

```json
{
  "status": "success",
  "message": "Security Access Granted"
}
```

---

# 6. Diagnostic Session Control

Changes the active ECU diagnostic session.

## Default Session

```bash
curl http://localhost:5000/diagnostics_session_control/1
```

## Programming Session

```bash
curl http://localhost:5000/diagnostics_session_control/3
```

## Extended Diagnostic Session

```bash
curl http://localhost:5000/diagnostics_session_control/2
```


### Example Response

```json
{
  "status": "success",
  "message": "Session Access Granted"
}
```

---

# 7. IO Control

Control an ECU actuator through UDS IO Control.

### Request

```bash
curl -X POST http://localhost:5000/IO_control \
-H "Content-Type: application/json" \
-d '{
  "DID": 4097,
  "control_parameter": 3,
  "control_state": true
}'
```

### Example Response

```json
{
  "status": "success",
  "message": "Control changed"
}
```

### Example Payload Fields

| Field             | Description            |
| ----------------- | ---------------------- |
| DID               | Actuator DID           |
| control_parameter | UDS IO Control command |
| control_state     | Desired actuator state |

---

# 8. Live Vehicle Data

Returns the latest decoded CAN analytics.

### Request

```bash
curl http://localhost:5000/live-data
```

### Example Response

```json
{
  "Speed_kmh": 45,
  "Engine_RPM": 2100,
  "Throttle_Pct": 32,
  "Fuel_Level": 67,
  "Engine_Temp": 88
}
```

---

# Complete Test Flow

Run the following commands in sequence to validate the complete system:

```bash
# Request Security Access
curl http://localhost:5000/security_access/1

# Enter Programming Session
curl http://localhost:5000/diagnostics_session_control/2

# Read VIN DID
curl http://localhost:5000/DID/61840

# Write DID
curl -X POST http://localhost:5000/DID \
-H "Content-Type: application/json" \
-d '{"DID":61840,"value":"TEST_VIN"}'

# Read Live Vehicle Data
curl http://localhost:5000/live-data

# Control Actuator
curl -X POST http://localhost:5000/IO_control \
-H "Content-Type: application/json" \
-d '{"DID":8193,"control_parameter":3,"control_state":true}'

# Download Logs
curl http://localhost:5000/download/logger \
-o all_logs.zip

# Download Firmware
curl http://localhost:5000/download/firmware \
-o firmware.bin
```

---

# API Summary

| Endpoint                                 | Method | Description                      |
| ---------------------------------------- | ------ | -------------------------------- |
| `/DID/<DID>`                             | GET    | Read DID                         |
| `/DID`                                   | POST   | Write DID                        |
| `/download/logger`                       | GET    | Download logger archive          |
| `/download/firmware`                     | GET    | Download firmware                |
| `/security_access/<level>`               | GET    | Perform UDS Security Access      |
| `/diagnostics_session_control/<session>` | GET    | Change diagnostic session        |
| `/IO_control`                            | POST   | Perform UDS IO Control           |
| `/live-data`                             | GET    | Get latest decoded CAN analytics |
