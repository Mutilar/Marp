#!/bin/bash
# start-video-stream.sh
# Streams camera feed to the connected Wi-Fi Direct client.

PORT=5600

# Cleanup existing camera processes/services to avoid hardware conflicts
cleanup() {
    echo "Stopping video stream..."
    pkill -P $$ # Kill child processes
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "Cleaning up existing camera processes..."
systemctl stop video-stream.service 2>/dev/null
pkill -x rpicam-vid 2>/dev/null
pkill -x libcamera-vid 2>/dev/null
# Wait a moment for resources to be released
sleep 1

# Check for rpicam-vid (Pi 5 / Bullseye+)
if command -v rpicam-vid &> /dev/null; then
    CMD="rpicam-vid"
elif command -v libcamera-vid &> /dev/null; then
    CMD="libcamera-vid"
else
    echo "Error: rpicam-vid or libcamera-vid not found."
    exit 1
fi

# Stream H.264 via HTTP (Hosting)
# -t 0: Run forever
# --inline: Insert SPS/PPS headers for stream recovery
# --width 1280 --height 720: 720p
# --framerate 10: Low framerate to reduce bandwidth/lag
# --bitrate 1000000: 1Mbps
# --g 10: Intra-frame every 10 frames (1 sec) for faster recovery
# --flush: Flush output buffers immediately
# Pipe to ffmpeg to host as HTTP stream for better Unity compatibility
# Unity VideoPlayer prefers HTTP over raw TCP.
# Loop to auto-restart the stream when a client disconnects (ffmpeg exits)
while true; do
    echo "Starting streaming pipeline..."
    $CMD -t 0 --inline --width 1280 --height 800 --framerate 24 --bitrate 1000000 --g 10 --flush --libav-format mpegts -o - | ffmpeg -i - -c copy -f mpegts -listen 1 http://0.0.0.0:$PORT
    echo "Stream ended (client disconnected?). Restarting in 1s..."
    sleep 1
done