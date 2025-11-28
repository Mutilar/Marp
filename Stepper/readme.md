## Stepper Driver Prototype Plan

### 1. Goals
- Drive a NEMA-class bipolar stepper motor via the microstep driver using an Arduino Uno R3.
- Support enable, direction, and pulse control with configurable microstepping and speed profiles.
- Build a reusable code scaffold for quick experimentation with motion routines and future peripherals (limit switches, sensors, UI).

### 2. Hardware Assumptions
- Driver exposes differential pairs: ENA+/-, DIR+/-, PUL+/-, plus motor coils (A+/A-, B+/B-) and power (VCC/GND).
- Arduino Uno R3 provides 5 V logic signals; confirm the driver tolerates 5 V differential inputs and allow common ground connection.
- External motor supply delivers appropriate voltage/current (typically 12–36 V); Arduino is powered separately via USB or 5 V regulator.
- Stepper motor wiring: pair A+ to coil 1 positive, A- to coil 1 negative, B+ to coil 2 positive, B- to coil 2 negative. Verify with datasheet or continuity test.

### 3. Safety and Power-Up Checklist
- Disconnect power while wiring; verify no shorts between motor phases.
- Use a bench supply with current limiting; start at low current and ramp up as necessary.
- Ensure driver heatsink has airflow; keep fingers clear of moving parts.
- Add flyback diode or snubber if the driver documentation requires external suppression (most integrated drivers handle this internally).

### 4. Wiring Plan
- Logic reference: tie Arduino GND to driver GND- (often ENA-, DIR-, PUL- share the same reference).
- ENA+: connect to Arduino digital output (default HIGH to enable; confirm active level in driver docs).
- DIR+: connect to Arduino digital output for direction control.
- PUL+: connect to Arduino digital output (use `digitalWrite` or timer-driven pulse generation).
- Optional: add inline 220 Ω resistors on logic lines to limit inrush and ringing.
- Consider opto-isolation requirements: if the driver inputs are opto-isolated, ENA+/DIR+/PUL+ should see +5 V while the corresponding negatives tie to Arduino ground.
- Leave VCC/GND for motor power only; do not back-feed Arduino 5 V from the driver.

### 5. Firmware Approach
1. Define pin assignments and active logic levels (enable polarity, direction default, pulse high phase polarity).
2. Implement a `StepperDriver` class or module handling:
	- `begin()` to configure pins, default states, and optional microstepping setup.
	- `enable()` / `disable()` wrapping ENA control.
	- `setDirection(bool clockwise)` abstraction.
	- `step(uint32_t steps, uint32_t pulseMicros)` for blocking test moves.
3. Provide a non-blocking step generator in a later iteration using `micros()` timers or Timer1 interrupt for consistent pulse timing.
4. Add configuration constants for max speed, acceleration (future), and microstep settings.

### 6. Prototype Experiments
- **Smoke Test:** Single step pulses at low frequency (e.g., 100 Hz) to confirm motor movement and direction.
- **Speed Sweep:** Iterate pulse timing from slow to faster while monitoring missed steps or overheating.
- **Microstepping:** If driver has DIP switches, document the positions and note expected steps per revolution; track in code comments or constants.
- **Motion Profiles:** Add simple functions for relative moves, homing simulation, and repetitive motion patterns to evaluate stability.
- **Diagnostics:** Use serial logging to print step counts, direction, enable state, and measured loop timing.

### 7. Documentation and Artifacts
- Capture wiring diagram (Mermaid or hand-drawn) and place under `assets/diagrams`.
- Store Arduino sketches in `Stepper/arduino/` (create folder) and name iterations clearly (`uno_basic_step.ino`, `uno_timer_step.ino`, etc.).
- Record test observations, tuning data, and issues in this README for quick reference.

### 8. Next Steps
- Confirm driver datasheet to validate logic polarity and current limits.
- Source or confirm motor specifications (phase resistance, current rating) to set driver current.
- Decide on microstepping mode and calculate steps per revolution for later kinematic work.
- Plan integration of limit switches or sensors if the final setup requires homing or safety interlocks.
