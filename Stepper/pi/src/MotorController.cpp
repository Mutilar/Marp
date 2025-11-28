#include "MotorController.hpp"
#include <pigpio.h>
#include <iostream>
#include <cmath>
#include <chrono>

MotorController::MotorController() {
    // Initialize motor states
    motors.push_back(new MotorState{{Constants::MOTOR_LEFT_ENABLE, Constants::MOTOR_LEFT_DIRECTION, Constants::MOTOR_LEFT_PULSE}});
    motors.push_back(new MotorState{{Constants::MOTOR_RIGHT_ENABLE, Constants::MOTOR_RIGHT_DIRECTION, Constants::MOTOR_RIGHT_PULSE}});
    motors.push_back(new MotorState{{Constants::MOTOR_PAN_ENABLE, Constants::MOTOR_PAN_DIRECTION, Constants::MOTOR_PAN_PULSE}});
    motors.push_back(new MotorState{{Constants::MOTOR_TILT_ENABLE, Constants::MOTOR_TILT_DIRECTION, Constants::MOTOR_TILT_PULSE}});
}

MotorController::~MotorController() {
    stop();
    for (auto m : motors) delete m;
    gpioTerminate();
}

bool MotorController::initialize() {
    if (gpioInitialise() < 0) {
        std::cerr << "pigpio initialisation failed" << '\n';
        return false;
    }

    if (Constants::LED_GPIO >= 0) {
        gpioSetMode(Constants::LED_GPIO, PI_OUTPUT);
        gpioWrite(Constants::LED_GPIO, 0);
    }

    for (auto motor : motors) {
        ensurePinSetup(motor->pins);
        workers.emplace_back(&MotorController::worker, this, motor);
    }
    return true;
}

void MotorController::stop() {
    running.store(false);
    for (auto& t : workers) {
        if (t.joinable()) t.join();
    }
    workers.clear();
}

void MotorController::setSpeed(int motorIndex, int16_t speed) {
    if (motorIndex >= 0 && motorIndex < motors.size()) {
        motors[motorIndex]->targetSpeed.store(speed, std::memory_order_relaxed);
    }
}

void MotorController::ensurePinSetup(const MotorPins& pins) {
    gpioSetMode(pins.enable, PI_OUTPUT);
    gpioSetMode(pins.direction, PI_OUTPUT);
    gpioSetMode(pins.pulse, PI_OUTPUT);
    gpioWrite(pins.enable, Constants::ENABLE_ACTIVE_LEVEL);
    gpioWrite(pins.direction, 1);
    gpioWrite(pins.pulse, !Constants::PULSE_ACTIVE_LEVEL);
}

uint32_t MotorController::tickDiff(uint32_t later, uint32_t earlier) {
    return (later >= earlier) ? (later - earlier)
                              : (0xFFFFFFFFu - earlier + 1u + later);
}

uint64_t MotorController::steadyClockMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

void MotorController::worker(MotorState* motor) {
    uint32_t lastStepTick = gpioTick();
    while (running.load(std::memory_order_relaxed)) {
        int16_t speed = motor->targetSpeed.load(std::memory_order_relaxed);
        if (speed == 0) {
            if (motor->enabled) {
                gpioWrite(motor->pins.enable, !Constants::ENABLE_ACTIVE_LEVEL);
                motor->enabled = false;
            }
            gpioDelay(2000);
            continue;
        }

        if (!motor->enabled) {
            gpioWrite(motor->pins.enable, Constants::ENABLE_ACTIVE_LEVEL);
            motor->enabled = true;
        }

        bool forward = (speed > 0);
        if (motor->directionForward != forward) {
            gpioWrite(motor->pins.direction, forward ? 1 : 0);
            motor->directionForward = forward;
            lastStepTick = gpioTick();
        }

        uint16_t absSpeed = static_cast<uint16_t>(std::abs(speed));
        unsigned long stepInterval = 1000000UL / absSpeed;
        if (stepInterval <= Constants::PULSE_WIDTH_US) {
            stepInterval = Constants::PULSE_WIDTH_US + 1;
        }

        uint32_t nowTick = gpioTick();
        uint32_t elapsed = tickDiff(nowTick, lastStepTick);
        if (elapsed >= stepInterval) {
            gpioWrite(motor->pins.pulse, Constants::PULSE_ACTIVE_LEVEL);
            gpioDelay(Constants::PULSE_WIDTH_US);
            gpioWrite(motor->pins.pulse, !Constants::PULSE_ACTIVE_LEVEL);
            lastStepTick = gpioTick();

            if (Constants::LED_GPIO >= 0) {
                stepIndicatorDeadlineMs.store(steadyClockMs() + Constants::STEP_LED_DURATION_MS,
                                              std::memory_order_relaxed);
                if (!stepIndicatorOn.exchange(true, std::memory_order_relaxed)) {
                    gpioWrite(Constants::LED_GPIO, 1);
                }
            }
            continue;
        }

        // Check LED turn off
        if (Constants::LED_GPIO >= 0 && stepIndicatorOn.load(std::memory_order_relaxed)) {
            uint64_t deadline = stepIndicatorDeadlineMs.load(std::memory_order_relaxed);
            if (steadyClockMs() >= deadline) {
                gpioWrite(Constants::LED_GPIO, 0);
                stepIndicatorOn.store(false, std::memory_order_relaxed);
            }
        }

        uint32_t waitUs = stepInterval - elapsed;
        if (waitUs > 1000) {
            waitUs = 1000;
        }
        gpioDelay(waitUs);
    }

    gpioWrite(motor->pins.pulse, !Constants::PULSE_ACTIVE_LEVEL);
    gpioWrite(motor->pins.enable, !Constants::ENABLE_ACTIVE_LEVEL);
}
