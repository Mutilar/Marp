# Raspberry Pi Setup for `stepper_pi.cpp`

This guide walks through preparing a fresh Raspberry Pi to build and run the stepper controller in `stepper_pi.cpp`. Follow the steps in order on a Rasberry Pi running Raspberry Pi OS (Bullseye or newer).

## 1. Base System Prep
- Flash Raspberry Pi OS (32- or 64-bit) Lite or Desktop to a microSD card and boot the Pi.
- Connect the Pi to the network and update the base image:
  ```bash
  sudo apt update
  sudo apt full-upgrade -y
  sudo reboot
  ```

## 2. Install Build & Runtime Dependencies
- Install the toolchain and libraries required by `stepper_pi.cpp`:
  ```bash
  sudo apt install -y build-essential pigpio libpigpio-dev joystick git
  ```
  - `build-essential` supplies `g++` and standard headers.
  - `pigpio` and `libpigpio-dev` provide the GPIO daemon and C client library.
  - `joystick` installs utilities like `jstest` for validating gamepad input.

## 3. Install Visual Studio Code (Optional)
To develop and debug directly on the Pi, install the official VS Code build for ARM:
```bash
sudo apt install -y curl gpg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /etc/apt/keyrings/packages.microsoft.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null
sudo apt update
sudo apt install -y code
```
- Launch VS Code with `code`. The first run may prompt to install recommended extensions.
- For remote editing from a desktop, install the **Remote - SSH** extension locally and connect to the Pi using the same repository path.

## 4. Enable the pigpio Daemon
`stepper_pi` talks to pigpio through the daemon. Enable and start it so it is available after every reboot:
```bash
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```
You can check its status with `systemctl status pigpiod`. All `pigpio` clients, including `stepper_pi`, require the daemon to be running.

## 5. Retrieve the Project Files
If the project is not already on the Pi:
```bash
cd ~
git clone https://github.com/Mutilar/Marp.git
cd Marp/Stepper/pi
```
Otherwise, copy the repository into place via your preferred method and change into `Stepper/pi`.

## 6. Build the Controller Binary
Compile the program with the required libraries:
```bash
g++ -std=c++20 stepper_pi.cpp -lpigpio -lrt -pthread -o stepper_pi
```
- `-lpigpio` links the pigpio client library.
- `-lrt` and `-pthread` satisfy pigpio's runtime dependencies.
- Adjust the output name (`-o stepper_pi`) if you prefer a different binary name.

Rebuild after every code change.

## 7. Wire the Hardware
Match the Raspberry Pi BCM GPIO numbers defined in the code with your stepper driver and optional activity LED:

| Signal | BCM GPIO | Notes |
| --- | --- | --- |
| `LED_GPIO` | `18` | Set to -1 in code to disable. Drives an indicator LED Active High. |
| `MOTOR_LEFT_ENABLE` | `5` | Active Low. Holds the left driver enabled when low. |
| `MOTOR_LEFT_DIRECTION` | `6` | Forward = High (code default). |
| `MOTOR_LEFT_PULSE` | `13` | Active High pulse; minimum width is 20 µs. |
| `MOTOR_RIGHT_ENABLE` | `19` | Active Low. |
| `MOTOR_RIGHT_DIRECTION` | `26` | Forward = High. |
| `MOTOR_RIGHT_PULSE` | `21` | Active High pulse. |

Additional wiring guidance:
- Tie the Pi ground to the stepper driver logic ground.
- Confirm the driver accepts 3.3 V logic; use level shifting if it requires 5 V.
- Keep enable lines asserted (low) only when the motor should hold torque.
- Add current-limiting resistors or opto-isolation if your driver recommends them.

## 8. Validate Joystick Input (Optional)
`stepper_pi` reads joystick events from `/dev/input/js0` by default. Before running the program:
```bash
jstest /dev/input/js0
```
- Move the analog stick and confirm axes 0 (X) and 1 (Y) respond.
- If the joystick enumerates at a different path, pass it as the first argument when launching `stepper_pi` (example: `sudo ./stepper_pi /dev/input/js1`).

## 9. Run the Controller
Execute the binary with root privileges (needed for GPIO and joystick access unless you add udev rules):
```bash
cd ~/Marp/Stepper/pi
sudo ./stepper_pi
```
- Terminate with `Ctrl+C`. The program handles `SIGINT`/`SIGTERM` and will shut down both motor workers before exiting.
- Expect console logs every 100 ms showing joystick mix and target speed values.
- The LED on GPIO 18, if connected, lights briefly during step bursts.

## 10. Troubleshooting Checklist
- **pigpiod not running**: `sudo systemctl status pigpiod` → if inactive, `sudo systemctl restart pigpiod`.
- **`Failed to open joystick`**: Re-check USB connection, ensure the `joystick` package is installed, and verify the device path.
- **Stepper driver always disabled**: Ensure ENA pins are wired correctly; the code uses active-low enable (`ENABLE_ACTIVE_LEVEL == 0`).
- **Jerky or stalled motion**: Confirm motor supply voltage/current and tune `MAX_SPEED_STEPS_PER_SEC` or `JOYSTICK_DEADZONE` in the source to suit your hardware.

## 11. Optional Improvements
- Add udev rules to grant non-root access to `/dev/input/js*` and `/dev/pigpio`. Place a rule in `/etc/udev/rules.d/` and reload with `sudo udevadm control --reload`.
- Cross-compile on a desktop using the Raspberry Pi toolchain if builds on the Pi are too slow.
- Enable SSH and `tmux` or `screen` for remote development sessions.

Following these steps provides a repeatable path to compile and run the stepper control logic on any Raspberry Pi that meets the hardware requirements.
