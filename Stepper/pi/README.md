# Raspberry Pi Robot Controller

This project runs on a Raspberry Pi 5 to control a 4-axis robot (2 Drive Steppers + 2 Turret Steppers). It supports control via a local USB Joystick (Xbox controller) or via UDP network packets (e.g., from a Steam Deck over Wi-Fi Direct). It also streams low-latency H.264 video to the connected client.

## Features
*   **Motor Control**: Drives 4 stepper motors using `lgpio` for precise timing.
*   **Dual Input**: Seamlessly switches between local USB Joystick and Network UDP commands.
*   **Safety**: Auto-stops motors if network connection is lost for >1 second.
*   **Wi-Fi Direct**: Acts as a Group Owner (Hotspot) for easy field connection without a router.
*   **Video Streaming**: Low-latency hardware-accelerated streaming via `rpicam-vid`.
*   **Systemd Integration**: Auto-starts all services on boot.

## System Architecture

![Architecture](../../assets/diagrams/architecture.png)

> Color key: **Blue**=Client, **Yellow**=Services, **Purple**=Hardware

<details>
<summary>Mermaid source</summary>
<!-- mermaid-output: assets/diagrams/architecture.png -->
```
graph TD
    %% Nodes
    subgraph Client["Steam Deck (Client)"]
        Unity["Unity App"]
    end

    subgraph Robot["Raspberry Pi 5"]
        subgraph Services["Systemd Services"]
            WifiService["wifi-direct.service<br/>(Network Setup)"]
            StepService["stepper-controller.service<br/>(stepper_pi)"]
            VidService["video-stream.service<br/>(rpicam-vid)"]
        end
        
        subgraph Hardware
            Camera["Pi Camera"]
            Drivers["Stepper Drivers (x4)"]
            Motors["Motors (L/R/Pan/Tilt)"]
            LocalJoy["Local Joystick (Optional)"]
        end
    end

    %% Network Interactions
    Unity -.->|Wi-Fi Direct Connection| WifiService
    Unity -->|UDP :5005<br/>JSON Command| StepService
    VidService -->|UDP :5600<br/>H.264 Stream| Unity

    %% Internal Interactions
    StepService -->|GPIO| Drivers
    Drivers --> Motors
    LocalJoy -->|USB| StepService
    Camera -->|CSI| VidService

    %% Styling
    classDef client fill:#d4e6f1,stroke:#2874a6,stroke-width:2px,color:black;
    classDef service fill:#fcf3cf,stroke:#d4ac0d,stroke-width:2px,color:black;
    classDef hardware fill:#ebdef0,stroke:#76448a,stroke-width:2px,color:black;
    
    class Unity client;
    class WifiService,StepService,VidService service;
    class Camera,Drivers,Motors,LocalJoy hardware;
```
</details>

## Hardware Pinout (BCM GPIO)

| Function | Enable | Direction | Pulse |
| :--- | :--- | :--- | :--- |
| **Left Drive** | 5 | 6 | 13 |
| **Right Drive** | 19 | 26 | 21 |
| **Turret Pan** | 23 | 24 | 25 |
| **Turret Tilt** | 12 | 16 | 20 |

*   **Activity LED**: GPIO 18

## 1. Base System Prep
- Flash Raspberry Pi OS (Bookworm or newer) to a microSD card and boot the Pi.
- Connect the Pi to the network and update the base image:
  ```bash
  sudo apt update
  sudo apt full-upgrade -y
  sudo reboot
  ```

## 2. Install Dependencies
Install the toolchain, libraries, and utilities:
```bash
sudo apt install -y build-essential cmake liblgpio-dev joystick git nlohmann-json3-dev dnsmasq psmisc
```
- `liblgpio-dev`: GPIO library for high-speed stepping.
- `nlohmann-json3-dev`: For parsing UDP JSON packets.
- `dnsmasq`: DHCP server for Wi-Fi Direct.

## 3. Build the Controller
The project uses CMake.

1.  Navigate to the `pi` directory:
    ```bash
    cd ~/Marp/Stepper/pi
    ```
2.  Create a build directory and compile:
    ```bash
    mkdir build && cd build
    cmake ..
    make
    ```
3.  The binary `stepper_pi` will be created in the `build` folder.

## 4. Installation (Auto-Start)
To set up Wi-Fi Direct, Video Streaming, and the Motor Controller to run automatically on boot:

1.  Run the installation script as root:
    ```bash
    cd ~/Marp/Stepper/pi/scripts
    chmod +x *.sh
    sudo ./install-services.sh
    ```
2.  This installs three systemd services:
    *   `wifi-direct.service`: Sets up the P2P network `DIRECT-xx-Robot-Pi5`.
    *   `stepper-controller.service`: Runs the robot logic.
    *   `video-stream.service`: Streams camera feed to the connected client.

## 5. Manual Usage
If you prefer to run things manually (e.g., for debugging):

**Start Wi-Fi Direct:**
```bash
sudo ./scripts/setup-wifi-direct.sh
```
*Connect your client (Steam Deck) to the SSID shown (e.g., `DIRECT-xx-Robot-Pi5`).*

**Start Motor Controller:**
```bash
sudo ./build/stepper_pi [optional_joystick_path]
```

**Start Video Stream:**
```bash
./scripts/start-video-stream.sh [CLIENT_IP]
```
*Defaults to `192.168.4.2`.*

## 6. Client Connection (Steam Deck / Unity)
*   **Network**: Connect to the Pi's Wi-Fi Direct network.
*   **UDP Control Port**: `5005` (Send JSON packets to `192.168.4.1`).
*   **Video Stream Port**: `5600` (MJPEG stream from `192.168.4.1`).

**JSON Packet Format:**
```json
{
  "joysticks": {
    "left": [x_float, y_float],   // Drive: -1.0 to 1.0
    "right": [x_float, y_float]  // Turret: -1.0 to 1.0
  }
}
```

## 7. Video Streaming (Multiplexer)
The video system uses a unified **Video Multiplexer** that provides:
- Single persistent MJPEG stream on port 5600
- Hot-swap between video sources without connection drops
- Built-in web viewer for debugging
- Configurable resolution and quality

### Available Video Sources
| Source | Native Resolution | Notes |
|--------|-------------------|-------|
| `kinect_rgb` | 640x480 | Scalable via `scale` parameter |
| `kinect_ir` | 640x480 | Infrared, scalable |
| `kinect_depth` | 640x480 | Colorized depth map, scalable |
| `picam` | Configurable | See presets below |

### Resolution Settings

**Kinect Resolution**: Fixed at 640x480 by the sync API. Use the `scale` parameter to resize output:
| Scale | Output Resolution |
|-------|-------------------|
| 0.5 | 320x240 |
| 0.75 | 480x360 |
| 1.0 | 640x480 (default) |
| 1.5 | 960x720 |
| 2.0 | 1280x960 |

**Pi Camera Presets** (`picam_res` parameter):
| Preset | Resolution | FPS |
|--------|------------|-----|
| `low` | 640x480 | 30 |
| `medium` | 1280x720 | 24 |
| `high` | 1280x800 | 24 (default) |
| `full` | 1920x1080 | 15 |

**JPEG Quality** (`quality` parameter): 1-100, default 70. Higher = better quality, more bandwidth.

### Endpoints
| URL | Description |
|-----|-------------|
| `http://<ip>:5600/` | Web viewer with controls |
| `http://<ip>:5600/stream.mjpg` | Raw MJPEG stream |
| `http://<ip>:5600/status` | JSON status |
| `http://<ip>:5600/switch?source=X` | Switch source |
| `http://<ip>:5600/switch?quality=N` | Set JPEG quality (1-100) |
| `http://<ip>:5600/switch?scale=N` | Set Kinect scale (0.25-2.0) |
| `http://<ip>:5600/switch?picam_res=X` | Set Pi cam preset |
| TCP port `5603` | Control server |

### Usage
```bash
# Start the multiplexer (via start-video-stream.sh)
./scripts/start-video-stream.sh

# Or directly with options
python3 scripts/video_multiplexer.py --source kinect_rgb --quality 80 --scale 1.5 --debug

# Switch sources via TCP
echo "kinect_ir" | nc localhost 5603

# Change quality via TCP
echo "quality 50" | nc localhost 5603

# Change Kinect scale via TCP  
echo "scale 1.5" | nc localhost 5603

# Change Pi camera resolution via TCP
echo "picam_res full" | nc localhost 5603

# Use the client for viewing/control
python3 scripts/video_client.py --host 192.168.4.1
```

### Integration with Unity/Clients
Clients connect to `http://192.168.4.1:5600/stream.mjpg` for MJPEG. To switch sources or settings:
```csharp
// HTTP requests - can combine multiple parameters
UnityWebRequest.Get("http://192.168.4.1:5600/switch?source=kinect_depth");
UnityWebRequest.Get("http://192.168.4.1:5600/switch?quality=50&scale=1.5");
UnityWebRequest.Get("http://192.168.4.1:5600/switch?source=picam&picam_res=full");

// Or via TCP socket to port 5603
socket.Send("kinect_ir\n");
socket.Send("quality 80\n");
socket.Send("scale 2.0\n");
```

## 8. Kinect Support with libfreenect
If you plan to steer the robot with a Kinect (RGB/depth, accelerometer, motor/LED control), the repository vendors [`OpenKinect/libfreenect`](https://github.com/OpenKinect/libfreenect) as a submodule.

1. **Sync the submodule**
  ```bash
  cd ~/Marp
  git submodule update --init --recursive Stepper/pi/libfreenect
  ```

2. **Install Kinect build prerequisites**
  ```bash
  sudo apt install -y libusb-1.0-0-dev freeglut3-dev mesa-utils python3 python3-opencv python3-numpy
  ```

3. **Build libfreenect**
  ```bash
  cd ~/Marp/Stepper/pi/libfreenect
  mkdir -p build && cd build
  cmake -L .. -DBUILD_PYTHON3=ON
  make -j$(nproc)
  ```

4. **Test Kinect locally** (optional, requires display)
  ```bash
  # Run the built-in GL viewer
  ./bin/freenect-glview
  
  # Or use the hiview for high-resolution
  ./bin/freenect-hiview
  ```

## 9. Optional: VS Code Setup
To develop and debug directly on the Pi, install the official VS Code build for ARM:
```bash
sudo apt install -y curl gpg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /etc/apt/keyrings/packages.microsoft.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null
sudo apt update
sudo apt install -y code
```
