struct MotorConfig {
  uint8_t enablePin;
  uint8_t directionPin;
  uint8_t pulsePin;
};

struct MotorState {
  MotorConfig pins;
  int16_t targetSpeedStepsPerSec;
  unsigned long lastStepTimeUs;
  unsigned long pulseChangeTimeUs;
  bool pulseHigh;
  bool directionForward;
};

constexpr MotorConfig MOTOR_LEFT_CONFIG{8, 9, 10};
constexpr MotorConfig MOTOR_RIGHT_CONFIG{5, 6, 7};

// Adjust these if your driver expects the opposite logic polarity.
constexpr bool ENABLE_ACTIVE_LEVEL = LOW;
constexpr bool PULSE_ACTIVE_LEVEL = HIGH;

constexpr uint8_t JOYSTICK_X_PIN = A0;  // VRx
constexpr uint8_t JOYSTICK_Y_PIN = A1;  // VRy

constexpr int JOYSTICK_DEADZONE = 25;
constexpr int16_t MAX_SPEED_STEPS_PER_SEC = 100;
constexpr unsigned long PULSE_WIDTH_US = 20;
constexpr unsigned long STEP_LED_DURATION_MS = 50;
constexpr unsigned long LOG_INTERVAL_MS = 100;
constexpr unsigned long SERIAL_BAUD = 115200;

MotorState motorLeft{MOTOR_LEFT_CONFIG, 0, 0, 0, false, true};
MotorState motorRight{MOTOR_RIGHT_CONFIG, 0, 0, 0, false, true};

bool stepIndicatorActive = false;
unsigned long stepIndicatorTimestampMs = 0;
unsigned long lastLogTimestampMs = 0;
int xCommandRaw = 0;
int yCommandRaw = 0;
int leftMixCommand = 0;
int rightMixCommand = 0;

void configureMotor(MotorState& motor, uint8_t defaultDirectionLevel);
void readJoystick();
int16_t commandToSpeed(int command);
void updateMotor(MotorState& motor);
void updateStepIndicator();
void logStatus();

void setup() {
  configureMotor(motorLeft, HIGH);
  configureMotor(motorRight, HIGH);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.begin(SERIAL_BAUD);
  delay(200);
  Serial.println(F("# Joystick stepper tester ready"));
}

void loop() {
  readJoystick();
  updateMotor(motorLeft);
  updateMotor(motorRight);
  updateStepIndicator();
  logStatus();
}

void configureMotor(MotorState& motor, uint8_t defaultDirectionLevel) {
  pinMode(motor.pins.enablePin, OUTPUT);
  pinMode(motor.pins.directionPin, OUTPUT);
  pinMode(motor.pins.pulsePin, OUTPUT);

  digitalWrite(motor.pins.enablePin, ENABLE_ACTIVE_LEVEL);
  digitalWrite(motor.pins.directionPin, defaultDirectionLevel);
  digitalWrite(motor.pins.pulsePin, !PULSE_ACTIVE_LEVEL);

  motor.directionForward = (defaultDirectionLevel == HIGH);
  motor.pulseHigh = false;
  motor.lastStepTimeUs = micros();
  motor.pulseChangeTimeUs = 0;
  motor.targetSpeedStepsPerSec = 0;
}

void readJoystick() {
  xCommandRaw = analogRead(JOYSTICK_X_PIN) - 512;
  yCommandRaw = analogRead(JOYSTICK_Y_PIN) - 512;

  if (abs(xCommandRaw) < JOYSTICK_DEADZONE) {
    xCommandRaw = 0;
  }
  if (abs(yCommandRaw) < JOYSTICK_DEADZONE) {
    yCommandRaw = 0;
  }

  leftMixCommand = constrain(yCommandRaw + xCommandRaw, -512, 512);
  rightMixCommand = constrain(yCommandRaw - xCommandRaw, -512, 512);

  motorLeft.targetSpeedStepsPerSec = commandToSpeed(leftMixCommand);
  motorRight.targetSpeedStepsPerSec = commandToSpeed(rightMixCommand);
}

int16_t commandToSpeed(int command) {
  if (abs(command) < JOYSTICK_DEADZONE) {
    return 0;
  }

  long scaled = static_cast<long>(command) * MAX_SPEED_STEPS_PER_SEC;
  scaled /= 512;
  return static_cast<int16_t>(scaled);
}

void updateMotor(MotorState& motor) {
  const int16_t speed = motor.targetSpeedStepsPerSec;
  unsigned long nowUs = micros();

  if (speed == 0) {
    // Optional: disable motor to reduce heating when idle.
    digitalWrite(motor.pins.enablePin, !ENABLE_ACTIVE_LEVEL);
    motor.pulseHigh = false;
    digitalWrite(motor.pins.pulsePin, !PULSE_ACTIVE_LEVEL);
    return;
  }

  digitalWrite(motor.pins.enablePin, ENABLE_ACTIVE_LEVEL);

  bool forward = (speed > 0);
  if (motor.directionForward != forward) {
    digitalWrite(motor.pins.directionPin, forward ? HIGH : LOW);
    motor.directionForward = forward;
    motor.lastStepTimeUs = nowUs;
  }

  uint16_t absSpeed = static_cast<uint16_t>(abs(speed));
  unsigned long stepIntervalUs = 1000000UL / absSpeed;
  if (!motor.pulseHigh && (nowUs - motor.lastStepTimeUs) >= stepIntervalUs) {
    digitalWrite(motor.pins.pulsePin, PULSE_ACTIVE_LEVEL);
    motor.pulseHigh = true;
    motor.pulseChangeTimeUs = nowUs;
    motor.lastStepTimeUs = nowUs;

    digitalWrite(LED_BUILTIN, HIGH);
    stepIndicatorActive = true;
    stepIndicatorTimestampMs = millis();

    // Serial.print(F("STEP pin="));
    // Serial.print(motor.pins.pulsePin);
    // Serial.print(F(" speed="));
    // Serial.println(speed);
  }

  if (motor.pulseHigh && (nowUs - motor.pulseChangeTimeUs) >= PULSE_WIDTH_US) {
    digitalWrite(motor.pins.pulsePin, !PULSE_ACTIVE_LEVEL);
    motor.pulseHigh = false;
    motor.pulseChangeTimeUs = nowUs;
  }
}

void updateStepIndicator() {
  if (stepIndicatorActive && (millis() - stepIndicatorTimestampMs) >= STEP_LED_DURATION_MS) {
    digitalWrite(LED_BUILTIN, LOW);
    stepIndicatorActive = false;
  }
}

void logStatus() {
  unsigned long nowMs = millis();
  if (nowMs - lastLogTimestampMs < LOG_INTERVAL_MS) {
    return;
  }
  lastLogTimestampMs = nowMs;

  Serial.print(F("JOY X="));
  Serial.print(xCommandRaw);
  Serial.print(F(" Y="));
  Serial.print(yCommandRaw);
  Serial.print(F(" MixL="));
  Serial.print(leftMixCommand);
  Serial.print(F(" MixR="));
  Serial.print(rightMixCommand);
  Serial.print(F(" SpdL="));
  Serial.print(motorLeft.targetSpeedStepsPerSec);
  Serial.print(F(" SpdR="));
  Serial.println(motorRight.targetSpeedStepsPerSec);
}
