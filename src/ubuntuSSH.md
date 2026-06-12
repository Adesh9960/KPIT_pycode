# Ubuntu SSH Connection Guide

A step-by-step guide to installing, configuring, and connecting to an Ubuntu machine remotely using secure shell (SSH).

## Prerequisites

- A host machine running Ubuntu Linux.
- A client machine (Windows, macOS, or Linux) on the same network.
- Sudo privileges on the Ubuntu host machine.

---

## 1. Host Configuration (On the Ubuntu Machine)

Execute these commands in the terminal of the Ubuntu machine you want to access remotely.

### Step 1: Update System Packages
Ensure your package repository index is up to date:
```bash
sudo apt update
```

### Step 2: Install OpenSSH Server
Install the SSH server daemon:
```bash
sudo apt install openssh-server -y
```

### Step 3: Enable and Start SSH Service
Configure the SSH service to start automatically upon system boot and launch it immediately:
```bash
sudo systemctl enable --now ssh
```

### Step 4: Configure the Firewall
If the Uncomplicated Firewall (UFW) is active, allow incoming SSH traffic:
```bash
sudo ufw allow OpenSSH
```

### Step 5: Verify Service Status
Confirm that the SSH server is active and running:
```bash
sudo systemctl status ssh
```

### Step 6: Find the Host IP Address
Locate your local IP address under your network adapter interface (e.g., `eth0` or `wlan0`):
```bash
ip a
```
*Note your IP address (e.g., `192.168.1.50`) for the next section.*

---

## 2. Remote Connection (From the Client Machine)

Open your local terminal app (Terminal on macOS/Linux, or PowerShell/Command Prompt on Windows) to connect.

### Standard Connection Command
Run the following command, replacing placeholders with your actual remote details:
```bash
ssh username@remote_host_ip
```

### First-Time Connection Steps
1. **Trust Host**: Type `yes` and press `Enter` when prompted to accept the remote system's cryptographic signature.
2. **Authenticate**: Type the remote user's password. *Characters will not appear on the screen as you type.*

---

## Alternative Graphical Clients

If you prefer using a Graphic User Interface (GUI) instead of the standard terminal command, use these applications:

- **Windows**: [PuTTY](https://putty.org)
- **Cross-Platform**: [Termius](https://termius.com) or [MobaXterm](https://mobatek.net)
