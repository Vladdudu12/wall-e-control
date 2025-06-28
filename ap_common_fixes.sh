#!/bin/bash
echo "Common Access Point Fixes for Wall-E"

# Fix 1: Disable conflicting services
echo "1. Disabling conflicting services..."
sudo systemctl disable wpa_supplicant
sudo systemctl stop wpa_supplicant
sudo systemctl mask wpa_supplicant

# Fix 2: Ensure NetworkManager doesn't interfere
if systemctl is-active --quiet NetworkManager; then
    echo "2. Configuring NetworkManager to ignore wlan0..."
    sudo tee /etc/NetworkManager/conf.d/99-unmanaged-devices.conf > /dev/null <<EOF
[keyfile]
unmanaged-devices=interface-name:wlan0
EOF
    sudo systemctl restart NetworkManager
fi

# Fix 3: Check and fix dhcpcd configuration
echo "3. Fixing dhcpcd configuration..."
sudo tee -a /etc/dhcpcd.conf > /dev/null <<EOF

# Wall-E Access Point - Interface wlan0
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF

# Fix 4: Create proper hostapd configuration
echo "4. Creating corrected hostapd configuration..."
sudo tee /etc/hostapd/hostapd.conf > /dev/null <<EOF
interface=wlan0
driver=nl80211
ssid=Wall-E-Robot
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=WallE2024
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
country_code=US
EOF

# Fix 5: Ensure hostapd daemon configuration
echo "5. Configuring hostapd daemon..."
sudo tee /etc/default/hostapd > /dev/null <<EOF
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF

# Fix 6: Fix dnsmasq configuration
echo "6. Fixing dnsmasq configuration..."
sudo tee /etc/dnsmasq.conf > /dev/null <<EOF
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=8.8.8.8
log-queries
log-dhcp
local=/walle/
domain=walle
address=/wall-e.local/192.168.4.1
EOF

# Fix 7: Enable IP forwarding
echo "7. Enabling IP forwarding..."
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf

# Fix 8: Restart services in correct order
echo "8. Restarting services..."
sudo systemctl daemon-reload
sudo systemctl restart dhcpcd
sleep 5
sudo systemctl restart hostapd
sleep 3
sudo systemctl restart dnsmasq

# Fix 9: Check status
echo "9. Checking service status..."
echo "=== HOSTAPD STATUS ==="
sudo systemctl status hostapd --no-pager -l

echo "=== DNSMASQ STATUS ==="
sudo systemctl status dnsmasq --no-pager -l

echo "=== WLAN0 INTERFACE ==="
ip addr show wlan0

echo "=== RFKILL STATUS ==="
sudo rfkill list

# Fix 10: Manual start if needed
echo "10. If services failed, trying manual start..."
if ! systemctl is-active --quiet hostapd; then
    echo "Starting hostapd manually..."
    sudo hostapd /etc/hostapd/hostapd.conf &
    sleep 5
fi

echo ""
echo "=== FINAL STATUS ==="
echo "WiFi networks should now be visible. Check with:"
echo "sudo iwlist wlan0 scan | grep ESSID"
echo ""
echo "If still not working, check logs:"
echo "sudo journalctl -u hostapd -n 20"
echo "sudo journalctl -u dnsmasq -n 20"