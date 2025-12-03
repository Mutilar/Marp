#!/bin/bash
# start-video-stream.sh
# Unified video streaming with hot-swappable sources.
#
# This script starts the Video Multiplexer which provides:
#   - Single persistent MJPEG stream on port 5600
#   - Web viewer at http://<ip>:5600/
#   - Hot-swap between: kinect_rgb, kinect_ir, kinect_depth, picam
#   - TCP control on port 5603

SCRIPT_DIR="$(dirname "$0")"
PORT=5600

# Cleanup function
cleanup() {
    echo "Stopping video stream..."
    pkill -P $$ 2>/dev/null
    pkill -f video_multiplexer.py 2>/dev/null
    pkill -f kinect_stream.py 2>/dev/null
    pkill -x rpicam-vid 2>/dev/null
    pkill -x libcamera-vid 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Clean up any existing processes
echo "Cleaning up existing processes..."
systemctl stop video-stream.service 2>/dev/null
pkill -f video_multiplexer.py 2>/dev/null
pkill -f kinect_stream.py 2>/dev/null
pkill -x rpicam-vid 2>/dev/null
pkill -x libcamera-vid 2>/dev/null
pkill -x ffmpeg 2>/dev/null
sleep 1

# Parse arguments
DEBUG=""
SOURCE="kinect_rgb"

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --source)
            SOURCE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "=============================================="
echo "Starting Video Multiplexer"
echo "=============================================="
echo "  Web Viewer: http://localhost:$PORT/"
echo "  Stream:     http://localhost:$PORT/stream.mjpg"
echo "  Control:    TCP port 5603"
echo "  Source:     $SOURCE"
echo "=============================================="

# Start the unified video multiplexer
exec python3 "$SCRIPT_DIR/video_multiplexer.py" --port $PORT --source "$SOURCE" $DEBUG