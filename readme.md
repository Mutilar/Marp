# Marp

## Overview
| Aspect | Details |
| --- | --- |
| Mission | Home robot emphasizing modular hardware and intuitive control via Xbox gamepad. |
| Current Focus | Documenting component selections, integration needs, and outstanding research items. |
| Development Notes | Prioritize maintainable wiring, accessible diagnostics, and future sensor expansion. |

### High-Level Wiring Diagram

![High-Level Wiring Diagram](assets/diagrams/high-level-wiring.png)

> Color key: power distribution (green hues), individual fuses (yellow), drivers (blue), converters (lavender), compute core (teal), peripherals (orange), and motors (red).

<details>
<summary>Mermaid source</summary>

```mermaid
graph TD
    Battery["24 V Li-ion Battery\n10 Ah (240 Wh)"]
    Breaker["30 A Circuit Breaker"]
    Switch["24 V Safety Switch"]
    Meter["Inline Battery Meter"]
    FuseBlock["6-way Fuse Block\nFused outputs (5–20 A)"]
    FuseStepper24["Fuse 1: 20 A\n24 V Stepper drivers"]
    FuseBuck12["Fuse 2: 10 A\n24→12 V DC-DC"]
    FuseBuck5["Fuse 3: 15 A\n24→5 V DC-DC"]
    subgraph StepperDrivers24["24 V Stepper Drivers (TB6600)"]
        direction TB
        Stepper24Left["Left Driver\nTB6600 (≈2.5 A)"]
        Stepper24Right["Right Driver\nTB6600 (≈2.5 A)"]
    end
    Buck12["24→12 V DC-DC (10 A max)"]
    Buck5["24→5 V DC-DC (15 A max)"]
    subgraph StepperDrivers12["12 V Stepper Drivers (DRV8825/A4988)"]
        direction TB
        Stepper12Pan["Pan Driver\nDRV8825 (≈1 A)"]
        Stepper12Tilt["Tilt Driver\nDRV8825 (≈1 A)"]
    end
    Projector["Mini Projector\n12 V, 2.5 A"]
    Audio["Audio Amp + Speakers\n5 V via Pi"]
    Pi["Raspberry Pi 5 + Storage\n5 V, ≤5.4 A"]
    Kinect["Kinect & USB Peripherals\n5 V, ≤2 A"]
    LEDs["Addressable LEDs & Logic\n5 V, ≤3 A"]

    Battery --> Breaker --> Switch --> Meter --> FuseBlock
    FuseBlock --> FuseStepper24 --> Stepper24Left
    FuseStepper24 --> Stepper24Right
    FuseBlock --> FuseBuck12 --> Buck12
    Buck12 --> Stepper12Pan
    Buck12 --> Stepper12Tilt
    Buck12 --> Projector
    FuseBlock --> FuseBuck5 --> Buck5 --> Pi
    Pi --> Audio
    Pi --> Kinect
    Pi -->|5 V via Pi| LEDs
    Stepper24Left --> LeftWheel["Left Wheel KH56"]
    Stepper24Right --> RightWheel["Right Wheel KH56"]
    Stepper12Pan --> HeadPan["Head Pan M55"]
    Stepper12Tilt --> HeadTilt["Head Tilt M55"]

    class Battery battery
    class Breaker,Switch,Meter,FuseBlock distribution
    class FuseStepper24,FuseBuck12,FuseBuck5 fuse
    class Stepper24Left,Stepper24Right,Stepper12Pan,Stepper12Tilt driver
    class Buck12,Buck5 converter
    class Pi compute
    class Projector,Audio,Kinect,LEDs peripheral
    class LeftWheel,RightWheel,HeadPan,HeadTilt motor

    classDef battery fill:#69c06f,stroke:#2e8540,color:#0b3d17,stroke-width:2px
    classDef distribution fill:#bde2a1,stroke:#4d7c0f,color:#234300,stroke-width:1.5px
    classDef fuse fill:#ffe89c,stroke:#d49f00,color:#7a5d00,stroke-width:1.5px
    classDef driver fill:#88b3e1,stroke:#1f78b4,color:#08306b,stroke-width:1.5px
    classDef converter fill:#c2b5f4,stroke:#6a51a3,color:#3f007d,stroke-width:1.5px
    classDef compute fill:#8dd3c7,stroke:#238b45,color:#00441b,stroke-width:1.5px
    classDef peripheral fill:#fdb462,stroke:#d95f02,color:#7f2704,stroke-width:1.5px
    classDef motor fill:#fb8072,stroke:#e31a1c,color:#67000d,stroke-width:2px
```

> Rendered with `scripts/render-mermaid.ps1` (`npm run render:mermaid`). Run the script after editing the Mermaid source below to refresh the image.
</details>


### Data Flow Diagram

![Data Flow Diagram](assets/diagrams/data-flow.png)

> Data flow color key: compute (teal), peripherals (orange), drivers (blue), motors (red).

<details>
<summary>Mermaid source</summary>

```mermaid
graph LR
    Pi["Raspberry Pi 5\nCore compute & control"]
    Projector["Mini Projector\nHDMI sink"]
    Kinect["Xbox Kinect Sensor\nUSB 3.0"]
    Controller["Xbox Controller Adapter\nUSB"]

    subgraph StepperDrivers24["24 V TB6600 Stepper Drivers"]
        StepperL["Left Driver\nStep / Dir / Enable"]
        StepperR["Right Driver\nStep / Dir / Enable"]
    end

    subgraph StepperDrivers12["12 V DRV8825/A4988 Stepper Drivers"]
        StepperPan["Pan Driver\nStep / Dir / Enable"]
        StepperTilt["Tilt Driver\nStep / Dir / Enable"]
    end

    subgraph StepperMotors24["24 V Stepper Motors"]
        MotorLeft["Left Wheel Motor\nA-/A+/B-/B+"]
        MotorRight["Right Wheel Motor\nA-/A+/B-/B+"]
    end

    subgraph StepperMotors12["12 V Stepper Motors"]
        MotorPan["Pan Motor\nA-/A+/B-/B+"]
        MotorTilt["Tilt Motor\nA-/A+/B-/B+"]
    end

    Pi -->|HDMI| Projector
    Pi -->|USB 3.0| Kinect
    Pi -->|USB| Controller
    Pi -->|GPIO: Step| StepperL
    Pi -->|GPIO: Dir| StepperL
    Pi -->|GPIO: Enable| StepperL
    Pi -->|GPIO: Step| StepperR
    Pi -->|GPIO: Dir| StepperR
    Pi -->|GPIO: Enable| StepperR
    Pi -->|GPIO: Step| StepperPan
    Pi -->|GPIO: Dir| StepperPan
    Pi -->|GPIO: Enable| StepperPan
    Pi -->|GPIO: Step| StepperTilt
    Pi -->|GPIO: Dir| StepperTilt
    Pi -->|GPIO: Enable| StepperTilt

    StepperL -->|A+| MotorLeft
    StepperL -->|A-| MotorLeft
    StepperL -->|B+| MotorLeft
    StepperL -->|B-| MotorLeft
    StepperR -->|A+| MotorRight
    StepperR -->|A-| MotorRight
    StepperR -->|B+| MotorRight
    StepperR -->|B-| MotorRight
    StepperPan -->|A+| MotorPan
    StepperPan -->|A-| MotorPan
    StepperPan -->|B+| MotorPan
    StepperPan -->|B-| MotorPan
    StepperTilt -->|A+| MotorTilt
    StepperTilt -->|A-| MotorTilt
    StepperTilt -->|B+| MotorTilt
    StepperTilt -->|B-| MotorTilt

    class Pi compute
    class Projector,Kinect,Controller peripheral
    class StepperL,StepperR,StepperPan,StepperTilt driver
    class MotorLeft,MotorRight,MotorPan,MotorTilt motor

    classDef compute fill:#8dd3c7,stroke:#238b45,color:#00441b,stroke-width:1.5px
    classDef peripheral fill:#fdb462,stroke:#d95f02,color:#7f2704,stroke-width:1.5px
    classDef driver fill:#88b3e1,stroke:#1f78b4,color:#08306b,stroke-width:1.5px
    classDef motor fill:#fb8072,stroke:#e31a1c,color:#67000d,stroke-width:2px
```

> Rendered with `scripts/render-mermaid.ps1 -DiagramIndex 1 -OutputPath assets/diagrams/data-flow.png`. Run the script after editing the Mermaid source below to refresh the image.
</details>

## Control & Compute
| Component | Role | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Controller | Primary operator input | 5 | ≤1.5 | ≤7.5 | Gamepad form factor | [Xbox](https://www.xbox.com/en-US/accessories/controllers/elite-wireless-controller-series-2) | Wireless or USB |
| Pi 5 | Onboard coordination & processing | 5 | ≤5.4 | ≤27 | 3.35" × 2.20" × 0.71" | [Raspberry](https://www.raspberrypi.com/products/raspberry-pi-5/) | Wi-Fi / Bluetooth / USB; CSI/DSI; 16 GB RAM, 64 GB SD. |

## Locomotion
| Component | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Left wheel | 24 | 2.5 | 60 | 2.20" | [Nidec](https://www.nidec-advancedmotor.com/en/digital/pdf/KH56Q.pdf) | KH56 Stepper Motor |
| Right wheel | 24 | 2.5 | 60 | 2.20" | [Nidec](https://www.nidec-advancedmotor.com/en/digital/pdf/KH56Q.pdf) | KH56 Stepper Motor |
| Drivers | 24 | ≤2.5 | ≤120 | 3.4" × 1.8" × 1.3" | [Makerguides](https://www.makerguides.com/tb6600-stepper-motor-driver-arduino-tutorial/) | TB6600 × 2 |

## Actuation

| Component | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Head pan | 12 | 1.0 | 12 | Ø2.17" × 0.98" | [Mitsumi](https://product.minebeamitsumi.com/en/product/category/rotary/steppingmotor/pm/PMStandardtype.html) | M55SP-3NK Stepper Motor (stocked on [Radwell](https://www.radwell.com/Buy/MITSUMI/MITSUMI/M55SP-2NK)) |
| Head tilt | 12 | 1.0 | 12 | Ø2.17" × 0.98" | [Mitsumi](https://product.minebeamitsumi.com/en/product/category/rotary/steppingmotor/pm/PMStandardtype.html) | M55SP-3NK Stepper Motor (stocked on [Radwell](https://www.radwell.com/Buy/MITSUMI/MITSUMI/M55SP-2NK)) |
| Drivers | 12 | ≤2.0 | ≤24 | 0.8" × 0.6" | [Jeanoko](https://www.amazon.com/dp/B0C4P8997M) | DRV8825/A4988 × 2 |

## Power & Electronics
| Component | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Lithium Battery | 24 | 5 (Continuous), 10 (Peak) | 240 Wh | 5.8" × 3.2" × 2.8" | [Aegis](https://www.aegisbattery.com/collections/24v-lithium-batteries/products/aegis-24v-10ah-lithium-ion-battery-pack-nmc-24v-lithium-battery) | 10 Ah NMC pack (≈240 Wh capacity). |
| Battery Meter | 24 | ≤0.5 | ≤1.2 | 85mm x W: 42mm x H: 25mm | [Aegis](https://www.aegisbattery.com/collections/lithium-battery-meters-instruments/products/high-precision-battery-200a-watt-meter-and-power-analyzer) | Inline 200 A analyzer (voltage, amps, watts). |
| Anderson PP45 → ring adapter | 24 | 20 | 480 | M10 ring | [Aegis](https://www.aegisbattery.com/collections/adapters/products/anderson-to-ring-terminal-adapter) | Quick battery-to-system interface. |
| Circuit Breaker | 24 | 30 | 720 | 1.73"D x 1.93"W x 2.91"H | [Hamolar](https://www.amazon.com/gp/product/B095Z2F5F7/ref=ewc_pr_img_2?smid=A2TJVE0ZQTOQDP&th=1) | Main battery protection. |
| Safety Switch | 24 | 16 | 384 | 4.88 x 2.24 x 2.09 | [Vonvoff](https://www.amazon.com/dp/B0CKXPNBB2?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1) | Manual 24 V disconnect. |
| Fuse Block | 24 | 5–20 (per branch) | ≤640 (aggregate) | 3.66" × 1.77" × 4.88" | [Tutooper](https://www.amazon.com/gp/product/B0F4NJK6MZ/ref=ewc_pr_img_1?smid=AAWQNNL1TJNS4&th=1) | Six-position low-voltage distribution. |
| 12 V Converter | 24→12 | 10 | 120 | 2.04"D x 1.88"W x 0.74"H | [Tobsun](https://www.amazon.com/gp/product/B07V6X6L89/ref=ewc_pr_img_1?smid=A3GYM455B71YGR&th=1) | DC-DC buck for 12 V peripherals. |
| 5 V Converter | 24→5 | 15 | 75 | 0.71"D x 1.26"W x 0.71"H | [Tobsun](https://www.amazon.com/dp/B0BLSGDVHF?ref=ppx_yo2ov_dt_b_fed_asin_title) | DC-DC buck for logic and compute loads. |

## Sensors & Outputs

### Distance & Environment
| Sensor | Range / Resolution | Coverage | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ultrasonic pair (x2 sets) | Short-range (TBD) | Front/Rear or side placements TBD | 5 | ≤0.015 | ≤0.075 | ~1.77" × 0.79" modules | — | Use overlapping fields to reduce blind spots. |
| Single-direction LiDARs (~10) | Spec TBD | 360° array via multiple units | TBD | TBD | TBD | TBD | — | Define spacing and mounting for uniform perimeter sensing. |

### Vision & Interaction
| Component | Function | Coverage / Resolution | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Xbox Kinect | Depth + RGB sensing, Pose detection | Wide FoV; structured light | 5 | ≤2 | ≤10 | 11" × 2.6" × 1.5" | [OpenKinect](https://github.com/OpenKinect/libfreenect) | Confirm Raspberry Pi compatibility or plan for companion compute. |
| Mini Projector | Visual output | 1080p | 12 | 2.5 | 27 | 5.5" × 2.36" × 4.33" | [CiBest](https://www.amazon.com/dp/B0DRCRK3BQ?ref=ppx_yo2ov_dt_b_fed_asin_title) | Validate mounting, airflow, and HDMI cabling to Pi 5. |
| Camera | Vision input | 12 MP, 75° FoV; autofocus | 5 | ≤0.5 | ≤2.5 | 1.50" × 1.50" × 0.71" (w/ adapter) | [Arducam](https://www.amazon.com/dp/B0C9PYCV9S?ref=ppx_yo2ov_dt_b_fed_asin_title) | IMX708 |
| Addressable LED strip | Face ring | Pixel count TBD | 5 | ≤0.06 (per LED) | ≤0.3 (per 5 LEDs) | Flexible strip | — | Level-shift 3.3 V logic up to 5 V. |

### Audio
| Component | Role | Voltage (V) | Amperage (A) | Wattage (W) | Physical Dimensions (") | Link | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Left speaker | Stereo output | TBD (per amplifier) | TBD | TBD | TBD | — | Powered via amplifier module (TBD). |
| Right speaker | Stereo output | TBD (per amplifier) | TBD | TBD | TBD | — | Match impedance with amplifier selection. |

## Open Items
| Item | Status | Next Step |
| --- | --- | --- |
| Head stepper motor selection | Pending | Determine torque requirements and mechanical constraints. |
| Projector specification | Pending | Evaluate models for brightness, interface, and mounting. |
| Sensor placement plan | Pending | Draft layout for ultrasonic and LiDAR modules; validate wiring paths. |
| Power budget verification | Pending | Sum draw across motors, compute, sensors, and converters; size fuses accordingly. |
| Projector integration | In progress | Design bracket and power branch for 12 V, 2.5 A load; verify HDMI adapter fit. |

## I/O & Pin Planning
| Device / Bus | Qty | Pins (each) | Total Pins | Notes |
| --- | --- | --- | --- | --- |
| 24 V stepper drivers (L/R) | 2 | Step, Dir, Enable (3) | 6 | TB6600 opto-isolated inputs; share enable line if wiring permits. |
| 12 V stepper drivers (pan/tilt) | 2 | Step, Dir, Enable (3) | 6 | Reserve two GPIOs for limit/home sensing. |
| Ultrasonic modules | 2 | Trigger, Echo (2) | 4 | Consider HC-SR04-compatible interface. |
| LiDAR modules | ~10 | I²C (shared 2) or UART (2 each) | 2–20 | Prioritize I²C/RS485 variants to conserve GPIO. |
| Xbox Kinect | 1 | USB | 0 | Draws only from USB bus. |
| Addressable LED strip | 1 | Data (1) | 1 | Level-shift 3.3 V logic up to 5 V. |
| Audio amp control | 1 | Enable / I²C | 1–2 | Depends on module selection. |
| Budget margin | — | — | ≥4 | Hold for future peripherals. |

### Pin mitigation options
- Offload high-rate GPIO to a microcontroller (e.g., RP2040, Arduino) and bridge via USB/UART.
- Add I²C GPIO expanders (MCP23017, TCA9548A) or SPI shift registers for sensor triggering.
- Share enable signals across compatible stepper drivers or use differential buses for LiDAR arrays.

