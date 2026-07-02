# Usage

## Prerequisites

- Linux system with SocketCAN support
- Python virtual environment created with all dependencies installed
- CAN interface configured (`can0`, `vcan0`, etc.)

---

## Note for using a Virtual CAN (`vcan0`)

If you do not have physical CAN hardware, the tester and ECU simulator can communicate over Linux's virtual CAN interface.

### 1. Configure the Virtual CAN Interface

Before starting either application, create and enable the `vcan0` interface:

```bash
sudo ip link add dev vcan0 type vcan
sudo ip link set vcan0 up
````

### 2. Update the Tester

In `app.py`, change:

```python
listener.start(address, uds_client.on_response)
```

to:

```python
listener.start(address, uds_client.on_response, channel="vcan0")
```

### 3. Update the ECU Simulator

In `sim.py`, change:

```python
listener.start(address, handle_tester_request, enable_logger=False)
```

to:

```python
listener.start(address, handle_tester_request, "vcan0", enable_logger=False)
```

### 4. Run the Applications

Start the ECU simulator:

```bash
pyadmin sim.py
```

In a separate terminal, start the tester:

```bash
pyadmin app.py
```

Both applications will now communicate over the `vcan0` virtual CAN interface.

```
```


## Create a Convenient Alias (Recommended)

Instead of typing the full path to your virtual environment every time, create an alias.

Open your shell configuration:

```bash
nano ~/.bashrc
```

Add the following line (replace the path with your own virtual environment):

```bash
alias pyadmin='sudo /path/to/your/venv/bin/python'
```

Example:

```bash
alias pyadmin='sudo /home/user/uds_tester/.venv/bin/python'
```

Reload your shell:

```bash
source ~/.bashrc
```

Now you can execute Python scripts inside the virtual environment with root privileges using the `pyadmin` command.

---

## Running the UDS Tester

Start the tester application:

```bash
pyadmin app.py
```

---

## Running the ECU Simulator

Start the ECU simulator:

```bash
pyadmin sim.py
```

---

## Typical Workflow

1. Configure and bring up your CAN interface.
2. Start the ECU simulator:

```bash
pyadmin sim.py
```

3. In another terminal, start the UDS tester:

```bash
pyadmin app.py
```

4. Open the tester UI and begin communicating with the simulated ECU.

---

## Notes

- Both applications should use the same CAN interface and bitrate.
- Ensure the CAN interface is already up before launching either application.
- Running through the `pyadmin` alias guarantees the correct Python environment is used while preserving the required administrative privileges.