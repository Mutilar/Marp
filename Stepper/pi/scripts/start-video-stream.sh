#!/bin/bash
# start-video-stream.sh
# Streams camera feed to the connected Wi-Fi Direct client.

# Default to the first assigned DHCP address if not specified
CLIENT_IP=${1:-"192.168.4.2"}
PORT=5600

# Cleanup existing camera processes/services to avoid hardware conflicts
cleanup() {
    echo "Stopping video stream..."
    pkill -P $$ # Kill child processes
    kill $PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "Cleaning up existing camera processes..."
systemctl stop video-stream.service 2>/dev/null
pkill -x rpicam-vid 2>/dev/null
pkill -x libcamera-vid 2>/dev/null
# Wait a moment for resources to be released
sleep 1

echo "Starting video stream to $CLIENT_IP:$PORT..."

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
$CMD -t 0 --inline --width 1280 --height 720 --framerate 10 --bitrate 1000000 --g 10 --flush --libav-format mpegts -o - | ffmpeg -i - -c copy -f mpegts -listen 1 http://0.0.0.0:$PORT &

PID=$!
wait $PID

# Old UDP Push method (commented out)
# $CMD -t 0 --inline --width 1280 --height 720 --framerate 30 --bitrate 2000000 --libav-format mpegts -o - | ffmpeg -i - -c copy -f mpegts udp://$CLIENT_IP:$PORT?pkt_size=1316
