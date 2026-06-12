# Quick Start Steps: SocketCAN Testing

### 1. Install Utilities
```bash
sudo apt-get update && sudo apt-get install -y can-utils
```

### 2. Bring Up Interface
* **For Physical Hardware (`can0`):**
  ```bash
  sudo ip link set can0 type can bitrate 500000
  sudo ip link set can0 up
  ```

### 3. To Start Listener
```bash
candump can0
```

### 4.To Inject Traffic
* **Single Frame:**
  ```bash
  cansend can0 123#112233
  ```
* **Continuous Flood:**
  ```bash
  cangen can0 -g 100 -I 100 -L 8
  ```