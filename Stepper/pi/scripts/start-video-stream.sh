#!/bin/bash
# start-video-stream.sh
# Streams camera feed to the connected Wi-Fi Direct client.

# Default to the first assigned DHCP address if not specified
CLIENT_IP=${1:-"192.168.4.2"}
PORT=5600

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

# Stream H.264 via UDP
# -t 0: Run forever
# --inline: Insert SPS/PPS headers for stream recovery
# --width 1280 --height 720: 720p for lower latency/bandwidth
# --framerate 30
# --bitrate 2000000: 2Mbps
# Pipe to ffmpeg to wrap in MPEG-TS for Unity VideoPlayer compatibility
$CMD -t 0 --inline --width 1280 --height 720 --framerate 30 --bitrate 2000000 -o - | ffmpeg -i - -c:v copy -f mpegts udp://$CLIENT_IP:$PORT?pkt_size=1316
