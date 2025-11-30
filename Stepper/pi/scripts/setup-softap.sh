#!/bin/bash
# setup-softap.sh
# Configures Raspberry Pi 5 as a SoftAP (Access Point) using NetworkManager.
# Unlike the Wi-Fi Direct script, this uses the standard NetworkManager service,
# which helps preserve other network functionality (like Ethernet connectivity).

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

# Configuration Variables
SSID="MARP-Robot-AP"
PASSWORD="marprobot"
IFACE="wlan0"
CON_NAME="MARP-Hotspot"

echo "Restoring NetworkManager if needed..."
# The wifi-direct script stops these, so we ensure they are back
systemctl unmask NetworkManager 2>/dev/null || true
systemctl start NetworkManager || true
# Wait for NM to be ready
echo "Waiting for NetworkManager..."
nm-online -q -t 15 || echo "NetworkManager taking a while..."

echo "Configuring SoftAP..."

# Remove old connection if exists
if nmcli connection show "$CON_NAME" >/dev/null 2>&1; then
    echo "Removing existing connection profile..."
    nmcli connection delete "$CON_NAME"
fi

echo "Creating new Hotspot profile..."
# Create the connection
nmcli con add type wifi ifname "$IFACE" con-name "$CON_NAME" autoconnect yes ssid "$SSID"

# Configure as Access Point
nmcli con modify "$CON_NAME" 802-11-wireless.mode ap
nmcli con modify "$CON_NAME" 802-11-wireless.band bg
nmcli con modify "$CON_NAME" wifi-sec.key-mgmt wpa-psk
nmcli con modify "$CON_NAME" wifi-sec.psk "$PASSWORD"

# Set IP settings
# 'shared' method provides DHCP and NAT (internet sharing from eth0)
# We set a static IP for the AP itself to be consistent with the robot setup
nmcli con modify "$CON_NAME" ipv4.method shared
nmcli con modify "$CON_NAME" ipv4.addresses 192.168.4.1/24

echo "Starting Hotspot..."
nmcli con up "$CON_NAME"

echo "----------------------------------------"
echo "SoftAP is running."
echo "SSID: $SSID"
echo "Pass: $PASSWORD"
echo "IP:   192.168.4.1"
echo "----------------------------------------"
