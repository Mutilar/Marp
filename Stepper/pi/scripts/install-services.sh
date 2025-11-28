#!/bin/bash
# Installs systemd services with correct paths

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
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

# List of services
SERVICES=("wifi-direct.service" "stepper-controller.service" "video-stream.service")

for SERVICE in "${SERVICES[@]}"; do
    echo "Installing $SERVICE..."
    
    # Read file, replace WORKING_DIR with actual path, write to /etc/systemd/system
    sed "s|WORKING_DIR|$PROJECT_DIR|g" "$SERVICE_DIR/$SERVICE" > "$SYSTEMD_DIR/$SERVICE"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "$SERVICE"
    echo "$SERVICE enabled."
done

echo "All services installed. They will start on next boot."
echo "To start immediately, run: systemctl start wifi-direct stepper-controller video-stream"
