#!/bin/bash
# Installs systemd services with correct paths

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root" >&2
  exit 1
fi

# Get the directory where this script is located (scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Get the project root (pi/)
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Project Directory: $PROJECT_DIR"

# Service files source
SERVICE_DIR="$PROJECT_DIR/systemd"

# Destination
SYSTEMD_DIR="/etc/systemd/system"

# Verify source directory exists
if [ ! -d "$SERVICE_DIR" ]; then
    echo "Error: Service directory not found: $SERVICE_DIR" >&2
    exit 1
fi

# List of services
SERVICES=("softap.service" "stepper-controller.service" "video-stream.service")

for SERVICE in "${SERVICES[@]}"; do
    SOURCE_FILE="$SERVICE_DIR/$SERVICE"
    
    if [ ! -f "$SOURCE_FILE" ]; then
        echo "Warning: Service file not found, skipping: $SOURCE_FILE" >&2
        continue
    fi
    
    echo "Installing $SERVICE..."
    
    # Read file, replace WORKING_DIR with actual path, write to /etc/systemd/system
    sed "s|WORKING_DIR|$PROJECT_DIR|g" "$SOURCE_FILE" > "$SYSTEMD_DIR/$SERVICE"
    
    # Enable service
    systemctl enable "$SERVICE"
    echo "$SERVICE enabled."
done

# Reload systemd once after all services are installed
systemctl daemon-reload

echo ""
echo "All services installed. They will start on next boot."
echo "To start immediately, run:"
echo "  systemctl start softap stepper-controller video-stream"
