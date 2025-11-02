# Marp

## Overview
| Aspect | Details |
| --- | --- |
| Mission | Home robot emphasizing modular hardware and intuitive control via Xbox gamepad. |
| Current Focus | Documenting component selections, integration needs, and outstanding research items. |
| Development Notes | Prioritize maintainable wiring, accessible diagnostics, and future sensor expansion. |

## Control & Compute
| Component | Role | Voltage (V) | Current (A) | Interface / Bandwidth |
| --- | --- | --- | --- | --- |
| Xbox controller | Primary operator input | N/A | N/A | Wireless or USB; low-latency gamepad protocol. |
| Raspberry Pi (assumed) | Onboard coordination & processing | 5 | ~3 (model dependent) | Wi-Fi / Bluetooth / USB; CSI/DSI for vision peripherals. |

## Locomotion & Actuation
| Component | Voltage (V) | Current (A) | Notes |
| --- | --- | --- | --- |
| Left wheel motor (KH56) | 24 | 2.5 | Stepper-class drive; paired with right motor for differential motion. |
| Right wheel motor (KH56) | 24 | 2.5 | Matching unit for balanced drive. |
| Head pan stepper | TBD | TBD | Model selection pending; ensure torque for horizontal sweep. |
| Head tilt stepper | TBD | TBD | Model selection pending; confirm load handling for vertical motion. |
| Stepper drivers | Supply-dependent | Per motor | Dedicated H-bridge/H-drive required per stepper axis. |

## Power & Electronics
| Component | Specs | Notes |
| --- | --- | --- |
| Waterproof inline safety switch | DPST, 16 A @ 24 V / 20 A @ 12 V <br> [Product link](https://www.amazon.com/dp/B0CKXPNBB2?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1) | Red-lit rocker; inline two-side cable entry for quick power isolation. |
| DC converters (2-pack) | Step-down 12 V/24 V → 5 V, 15 A (75 W) <br> [Product link](https://www.amazon.com/dp/B0BLSGDVHF?ref=ppx_yo2ov_dt_b_fed_asin_title) | Supports logic rails & peripherals; consider heatsinking under sustained load. |
| Aegis lithium battery | 24 V, 10 Ah (NMC) with 3 A charger <br> $206.98 — [Aegis Battery](https://www.aegisbattery.com/) | Primary power source; verify enclosure ventilation and mounting. |
| Anderson PP45 → ring adapter | 10 mm ring | $15.99; enables quick battery-to-system connection. |
| Battery watt meter | 200 A analyzer | Inline monitoring for voltage, current, and consumption profiling. |
| Power distribution | TBD | Size wiring, fusing, and bus bars after final load calculations. |
| Protection circuitry | TBD | Include overcurrent, reverse polarity, and surge protection. |

## Sensors & Outputs

### Distance & Environment
| Sensor | Range / Resolution | Coverage | Notes |
| --- | --- | --- | --- |
| Ultrasonic pair (x2 sets) | Short-range (exact spec TBD) | Front/Rear or side placements TBD | Use overlapping fields to reduce blind spots. |
| Single-direction LiDARs (~10) | Spec TBD | 360° array via multiple units | Define spacing and mounting for uniform perimeter sensing. |

### Vision & Interaction
| Component | Function | Coverage / Resolution | Notes |
| --- | --- | --- | --- |
| Xbox Kinect | Depth + RGB sensing | Wide FoV; structured light | Confirm Raspberry Pi compatibility or plan for companion compute. |
| Small projector | Visual output | Throw ratio & lumen TBD | Evaluate compact models compatible with available power budget. |
| Addressable LED strip | Facial animation | Pixel count TBD | Requires 5 V rail; map animation channels in software. |

### Audio
| Component | Role | Placement | Notes |
| --- | --- | --- | --- |
| Left speaker | Stereo output | Head/body panel | Powered via amplifier module (TBD). |
| Right speaker | Stereo output | Head/body panel | Match impedance with amplifier selection. |

## Open Items
| Item | Status | Next Step |
| --- | --- | --- |
| Head stepper motor selection | Pending | Determine torque requirements and mechanical constraints. |
| Projector specification | Pending | Evaluate models for brightness, interface, and mounting. |
| Sensor placement plan | Pending | Draft layout for ultrasonic and LiDAR modules; validate wiring paths. |
| Power budget verification | Pending | Sum draw across motors, compute, sensors, and converters; size fuses accordingly. |

