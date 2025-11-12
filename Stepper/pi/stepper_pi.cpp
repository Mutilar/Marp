#include <pigpio.h>
#include <linux/joystick.h>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <thread>
#include <unistd.h>

namespace {
constexpr int LED_GPIO = 18;                    // Set to -1 to disable the activity LED output.
constexpr unsigned MOTOR_LEFT_ENABLE = 5;       // BCM GPIO numbers; adjust to match your wiring.
constexpr unsigned MOTOR_LEFT_DIRECTION = 6;
constexpr unsigned MOTOR_LEFT_PULSE = 13;
constexpr unsigned MOTOR_RIGHT_ENABLE = 19;
constexpr unsigned MOTOR_RIGHT_DIRECTION = 26;
constexpr unsigned MOTOR_RIGHT_PULSE = 21;

constexpr bool ENABLE_ACTIVE_LEVEL = 0;         // LOW keeps stepper drivers enabled on many boards.
constexpr bool PULSE_ACTIVE_LEVEL = 1;          // HIGH drives the pulse line active.

constexpr int JOYSTICK_AXIS_X = 0;              // Xbox left stick X axis index.
constexpr int JOYSTICK_AXIS_Y = 1;              // Xbox left stick Y axis index.
constexpr int JOYSTICK_DEADZONE = 25;
constexpr int16_t MAX_SPEED_STEPS_PER_SEC = 100;
constexpr unsigned PULSE_WIDTH_US = 20;
constexpr unsigned STEP_LED_DURATION_MS = 50;
constexpr unsigned LOG_INTERVAL_MS = 100;

constexpr int MAX_JOYSTICK_VALUE = 32767;       // Signed 16-bit joystick axis max.
constexpr char DEFAULT_JOYSTICK_PATH[] = "/dev/input/js0";

struct MotorPins {
    unsigned enable;
    unsigned direction;
    unsigned pulse;
};

struct MotorState {
    MotorPins pins;
    std::atomic<int16_t> targetSpeed{0};
    bool directionForward{true};
    bool enabled{false};
};

std::atomic<bool> running{true};
std::atomic<bool> stepIndicatorOn{false};
std::atomic<uint64_t> stepIndicatorDeadlineMs{0};

uint32_t tickDiff(uint32_t later, uint32_t earlier) {
    return (later >= earlier) ? (later - earlier)
                              : (0xFFFFFFFFu - earlier + 1u + later);
}

uint64_t steadyClockMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

int clamp(int value, int minValue, int maxValue) {
    return std::max(minValue, std::min(value, maxValue));
}

int16_t commandToSpeed(int command) {
    if (std::abs(command) < JOYSTICK_DEADZONE) {
        return 0;
    }
    long scaled = static_cast<long>(command) * MAX_SPEED_STEPS_PER_SEC;
    scaled /= 512;
    return static_cast<int16_t>(scaled);
}

void ensurePinSetup(const MotorPins& pins) {
    gpioSetMode(pins.enable, PI_OUTPUT);
    gpioSetMode(pins.direction, PI_OUTPUT);
    gpioSetMode(pins.pulse, PI_OUTPUT);
    gpioWrite(pins.enable, ENABLE_ACTIVE_LEVEL);
    gpioWrite(pins.direction, 1);
    gpioWrite(pins.pulse, !PULSE_ACTIVE_LEVEL);
}

void signalHandler(int) {
    running.store(false);
}

void motorWorker(MotorState& motor) {
    uint32_t lastStepTick = gpioTick();
    while (running.load(std::memory_order_relaxed)) {
        int16_t speed = motor.targetSpeed.load(std::memory_order_relaxed);
        if (speed == 0) {
            if (motor.enabled) {
                gpioWrite(motor.pins.enable, !ENABLE_ACTIVE_LEVEL);
                motor.enabled = false;
            }
            gpioDelay(2000);
            continue;
        }

        if (!motor.enabled) {
            gpioWrite(motor.pins.enable, ENABLE_ACTIVE_LEVEL);
            motor.enabled = true;
        }

        bool forward = (speed > 0);
        if (motor.directionForward != forward) {
            gpioWrite(motor.pins.direction, forward ? 1 : 0);
            motor.directionForward = forward;
            lastStepTick = gpioTick();
        }

        uint16_t absSpeed = static_cast<uint16_t>(std::abs(speed));
        unsigned long stepInterval = 1000000UL / absSpeed;
        if (stepInterval <= PULSE_WIDTH_US) {
            stepInterval = PULSE_WIDTH_US + 1;
        }

        uint32_t nowTick = gpioTick();
        uint32_t elapsed = tickDiff(nowTick, lastStepTick);
        if (elapsed >= stepInterval) {
            gpioWrite(motor.pins.pulse, PULSE_ACTIVE_LEVEL);
            gpioDelay(PULSE_WIDTH_US);
            gpioWrite(motor.pins.pulse, !PULSE_ACTIVE_LEVEL);
            lastStepTick = gpioTick();

            if (LED_GPIO >= 0) {
                stepIndicatorDeadlineMs.store(steadyClockMs() + STEP_LED_DURATION_MS,
                                              std::memory_order_relaxed);
                if (!stepIndicatorOn.exchange(true, std::memory_order_relaxed)) {
                    gpioWrite(LED_GPIO, 1);
                }
            }
            continue;
        }

        uint32_t waitUs = stepInterval - elapsed;
        if (waitUs > 1000) {
            waitUs = 1000;
        }
        gpioDelay(waitUs);
    }

    gpioWrite(motor.pins.pulse, !PULSE_ACTIVE_LEVEL);
    gpioWrite(motor.pins.enable, !ENABLE_ACTIVE_LEVEL);
}

int openJoystick(const char* path) {
    int fd = open(path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        std::cerr << "Failed to open joystick at " << path << ": "
                  << std::strerror(errno) << '\n';
    }
    return fd;
}

int scaleAxis(int16_t raw) {
    double normalized = static_cast<double>(raw) / MAX_JOYSTICK_VALUE;
    int scaled = static_cast<int>(std::lround(normalized * 512.0));
    return clamp(scaled, -512, 512);
}

}  // namespace

int main(int argc, char* argv[]) {
    const char* joystickPath = (argc > 1) ? argv[1] : DEFAULT_JOYSTICK_PATH;

    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    if (gpioInitialise() < 0) {
        std::cerr << "pigpio initialisation failed" << '\n';
        return 1;
    }

    if (LED_GPIO >= 0) {
        gpioSetMode(LED_GPIO, PI_OUTPUT);
        gpioWrite(LED_GPIO, 0);
    }

    MotorState motorLeft{{MOTOR_LEFT_ENABLE, MOTOR_LEFT_DIRECTION, MOTOR_LEFT_PULSE}};
    MotorState motorRight{{MOTOR_RIGHT_ENABLE, MOTOR_RIGHT_DIRECTION, MOTOR_RIGHT_PULSE}};
    ensurePinSetup(motorLeft.pins);
    ensurePinSetup(motorRight.pins);

    int joystickFd = openJoystick(joystickPath);
    if (joystickFd < 0) {
        gpioTerminate();
        return 1;
    }

    std::thread leftThread(motorWorker, std::ref(motorLeft));
    std::thread rightThread(motorWorker, std::ref(motorRight));

    int16_t axes[8] = {0};
    int xCommandRaw = 0;
    int yCommandRaw = 0;
    int leftMixCommand = 0;
    int rightMixCommand = 0;

    auto nextLogTime = std::chrono::steady_clock::now();

    while (running.load(std::memory_order_relaxed)) {
        js_event event;
        ssize_t bytes = read(joystickFd, &event, sizeof(event));
        while (bytes == sizeof(event)) {
            event.type &= ~JS_EVENT_INIT;
            if (event.type == JS_EVENT_AXIS && event.number < 8) {
                axes[event.number] = event.value;
            }
            bytes = read(joystickFd, &event, sizeof(event));
        }

        if (bytes < 0 && errno != EAGAIN) {
            std::cerr << "Joystick read error: " << std::strerror(errno) << '\n';
            break;
        }

        int xScaled = scaleAxis(axes[JOYSTICK_AXIS_X]);
        int yScaled = -scaleAxis(axes[JOYSTICK_AXIS_Y]);  // Invert so forward stick is positive.

        xCommandRaw = (std::abs(xScaled) < JOYSTICK_DEADZONE) ? 0 : xScaled;
        yCommandRaw = (std::abs(yScaled) < JOYSTICK_DEADZONE) ? 0 : yScaled;

        leftMixCommand = clamp(yCommandRaw + xCommandRaw, -512, 512);
        rightMixCommand = clamp(yCommandRaw - xCommandRaw, -512, 512);

        motorLeft.targetSpeed.store(commandToSpeed(leftMixCommand), std::memory_order_relaxed);
        motorRight.targetSpeed.store(commandToSpeed(rightMixCommand), std::memory_order_relaxed);

        if (LED_GPIO >= 0 && stepIndicatorOn.load(std::memory_order_relaxed)) {
            uint64_t deadline = stepIndicatorDeadlineMs.load(std::memory_order_relaxed);
            if (steadyClockMs() >= deadline) {
                gpioWrite(LED_GPIO, 0);
                stepIndicatorOn.store(false, std::memory_order_relaxed);
            }
        }

        auto now = std::chrono::steady_clock::now();
        if (now >= nextLogTime) {
            std::cout << "JOY X=" << xCommandRaw
                      << " Y=" << yCommandRaw
                      << " MixL=" << leftMixCommand
                      << " MixR=" << rightMixCommand
                      << " SpdL=" << motorLeft.targetSpeed.load(std::memory_order_relaxed)
                      << " SpdR=" << motorRight.targetSpeed.load(std::memory_order_relaxed)
                      << std::endl;
            nextLogTime = now + std::chrono::milliseconds(LOG_INTERVAL_MS);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    running.store(false, std::memory_order_relaxed);
    close(joystickFd);

    if (leftThread.joinable()) {
        leftThread.join();
    }
    if (rightThread.joinable()) {
        rightThread.join();
    }

    gpioTerminate();
    return 0;
}
