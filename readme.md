# CAN Monitor and Simulation

## Overview

CAN Monitor and Simulation is a Python-based project for monitoring, simulating, and logging CAN (Controller Area Network) traffic. It provides utilities for generating CAN frames, processing incoming messages, and recording communication for debugging and analysis.

## Features

* CAN frame simulation
* CAN message monitoring
* Logging of CAN traffic
* Thread-safe data handling
* Modular project structure for easy extension and testing

## Project Structure

```text
.
├── src/
│   ├── logger/
│   ├── data_structures/
│   ├── listener/
│   ├── simulator/
│   └── ...
├── tests/
├── requirements.txt
└── README.md
```

## Prerequisites

* Python 3.10 or later
* `pip` package manager

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd <repository-folder>
```

(Optional) Create and activate a virtual environment.

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Execution Instructions
### Setting `PYTHONPATH`

Before running the project or tests, set `PYTHONPATH` to the `src` directory.

#### Windows PowerShell

From the project root directory:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

#### Windows Command Prompt (`cmd`)

From the project root directory:

```cmd
set PYTHONPATH=%CD%\src
```

#### Verify the setting

PowerShell:

```powershell
echo $env:PYTHONPATH
```

Command Prompt:

```cmd
echo %PYTHONPATH%
```

Run the application from the project root directory:

```bash
python src/main.py
```

If your entry point is different, replace `src/main.py` with the appropriate script.

## Running Unit Tests

Execute all tests using:

```bash
python -m unittest discover -s tests
```

Or run an individual test file:

```bash
python -m unittest tests.test_logger
```

## Notes

* Run commands from the project root directory.
* Ensure all required dependencies are installed before execution.
* If using hardware-specific CAN interfaces, verify that the required drivers and libraries are properly configured.

## License

Add your preferred license information here.
