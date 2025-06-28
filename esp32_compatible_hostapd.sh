#!/bin/bash
echo "Updating hostapd configuration for ESP32 compatibility..."

# Stop hostapd
sudo systemctl stop hostapd

# Create ESP32-compatible hostapd configuration
sudo tee /etc/hostapd/hostapd.conf > /dev/null <<'EOF'
# ESP32-Compatible Access Point Configuration
interface=wlan0
driver=nl80211
ssid=Wall-E-Robot
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0

# WPA2 settings compatible with ESP32
wpa=2
wpa_passphrase=WallE2024
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP

# ESP32 compatibility settings
ieee80211n=1
ieee80211d=1
country_code=US
beacon_int=100
dtim_period=2

# Security and performance
max_num_sta=10
rts_threshold=2347
fragm_threshold=2346

# Additional ESP32 compatibility
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
EOF

echo "✓ Updated hostapd configuration"

# Restart hostapd
sudo systemctl restart hostapd

# Check status
echo "Checking hostapd status..."
sudo systemctl status hostapd --no-pager -l

echo ""
echo "Try connecting ESP32-CAM again!"