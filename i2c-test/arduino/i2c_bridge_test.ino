#include <Wire.h>

namespace {
constexpr uint8_t kI2cAddress = 0x08;  // 7-bit address for Arduino as slave

constexpr uint8_t kCmdPing = 0x01;
constexpr uint8_t kCmdGetTelemetry = 0x02;
constexpr uint8_t kCmdSetLed = 0x10;

constexpr uint8_t kFlagPanLimit = 0x01;
constexpr uint8_t kFlagShutterLimit = 0x02;
constexpr uint8_t kFlagHeartbeat = 0x80;  // Mirrors built-in LED state.

constexpr uint8_t kPinPanLimit = 6;
constexpr uint8_t kPinShutterLimit = 7;
constexpr uint8_t kPinStatusLed = LED_BUILTIN;

struct TelemetryPacket {
  uint8_t majorVersion;
  uint8_t minorVersion;
  uint16_t uptimeSeconds;
  uint8_t statusFlags;
  uint8_t heartbeat;
} __attribute__((packed));
static_assert(sizeof(TelemetryPacket) == 6, "TelemetryPacket size mismatch");

volatile uint8_t gLastCommand = kCmdPing;
volatile bool gLedOverride = false;
volatile uint8_t gLedLevel = LOW;
volatile bool gTelemetryDirty = true;
TelemetryPacket gTelemetry = {
    .majorVersion = 1,
    .minorVersion = 0,
    .uptimeSeconds = 0,
    .statusFlags = 0,
    .heartbeat = 0,
};
unsigned long gLastHeartbeatMillis = 0;

void updateTelemetryFromHardware();
void onI2cReceive(int byteCount);
void onI2cRequest();
}  // namespace

void setup() {
  pinMode(kPinStatusLed, OUTPUT);
  pinMode(kPinPanLimit, INPUT_PULLUP);
  pinMode(kPinShutterLimit, INPUT_PULLUP);

  Wire.begin(kI2cAddress);
  Wire.onReceive(onI2cReceive);
  Wire.onRequest(onI2cRequest);
}

void loop() {
  const unsigned long now = millis();
  if (now - gLastHeartbeatMillis >= 1000) {
    gLastHeartbeatMillis = now;
    gTelemetry.heartbeat++;
    gTelemetry.uptimeSeconds = static_cast<uint16_t>(now / 1000UL);
    updateTelemetryFromHardware();
    gTelemetryDirty = true;

    if (!gLedOverride) {
      gLedLevel = (gLedLevel == LOW) ? HIGH : LOW;
      digitalWrite(kPinStatusLed, gLedLevel);
    }
  }
}

namespace {
void updateTelemetryFromHardware() {
  uint8_t flags = 0;
  if (digitalRead(kPinPanLimit) == LOW) {
    flags |= kFlagPanLimit;
  }
  if (digitalRead(kPinShutterLimit) == LOW) {
    flags |= kFlagShutterLimit;
  }
  if (gLedLevel == HIGH) {
    flags |= kFlagHeartbeat;
  }
  gTelemetry.statusFlags = flags;
}

void onI2cReceive(int byteCount) {
  if (byteCount <= 0) {
    return;
  }

  const uint8_t command = static_cast<uint8_t>(Wire.read());
  gLastCommand = command;
  byteCount--;

  switch (command) {
    case kCmdPing:
      // No payload expected; response handled in onRequest.
      break;
    case kCmdGetTelemetry:
      updateTelemetryFromHardware();
      gTelemetryDirty = true;
      break;
    case kCmdSetLed:
      if (byteCount > 0) {
        const uint8_t mode = static_cast<uint8_t>(Wire.read());
        if (mode == 0) {
          gLedOverride = false;
        } else {
          gLedOverride = true;
          gLedLevel = (mode == 1) ? LOW : HIGH;
          digitalWrite(kPinStatusLed, gLedLevel);
        }
      }
      break;
    default:
      // Unknown command; fall back to telemetry response.
      break;
  }
}

void onI2cRequest() {
  switch (gLastCommand) {
    case kCmdPing: {
      static const uint8_t kResponse[] = {'O', 'K'};
      Wire.write(kResponse, sizeof(kResponse));
      break;
    }
    case kCmdGetTelemetry:
    default:
      if (gTelemetryDirty) {
        updateTelemetryFromHardware();
        gTelemetryDirty = false;
      }
      Wire.write(reinterpret_cast<uint8_t*>(&gTelemetry), sizeof(gTelemetry));
      break;
  }
}
}  // namespace
