#!/bin/bash
echo "================================================"
echo "Wall-E Access Point Setup"
echo "Creating standalone WiFi network for Wall-E"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo $0"
    exit 1
fi

# Backup current network configuration
echo "Backing up current network configuration..."
cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup 2>/dev/null || true
cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup 2>/dev/null || true

echo "Installing required packages..."
apt-get update
apt-get install -y hostapd dnsmasq

echo "Stopping services..."
systemctl stop hostapd
systemctl stop dnsmasq

echo "Configuring static IP for wlan0..."

# Configure static IP for the access point
cat >> /etc/dhcpcd.conf << 'EOF'

# Wall-E Access Point Configuration
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF

echo "Configuring DHCP server (dnsmasq)..."

# Configure DHCP server
cat > /etc/dnsmasq.conf << 'EOF'
# Wall-E Access Point DHCP Configuration
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h

# DNS settings
dhcp-option=3,192.168.4.1  # Default gateway
dhcp-option=6,192.168.4.1  # DNS server

# Local domain
local=/walle/
domain=walle
expand-hosts

# Address for wall-e.local
address=/wall-e.local/192.168.4.1
address=/walle.local/192.168.4.1

# Log DHCP requests
log-dhcp
EOF

echo "Creating hostapd configuration..."

# Create hostapd directory if it doesn't exist
mkdir -p /etc/hostapd

# Configure Access Point
cat > /etc/hostapd/hostapd.conf << 'EOF'
# Wall-E Access Point Configuration
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

# Additional settings for better compatibility
country_code=US
ieee80211n=1
ieee80211d=1
beacon_int=100
dtim_period=2
max_num_sta=10
rts_threshold=2347
fragm_threshold=2346
EOF

echo "Configuring hostapd daemon..."

# Tell hostapd where to find the configuration
cat > /etc/default/hostapd << 'EOF'
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF

echo "Enabling IP forwarding..."

# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

# Configure iptables for internet sharing (if eth0 available)
cat > /etc/rc.local << 'EOF'
#!/bin/bash
# Wall-E Access Point startup script

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Configure iptables for internet sharing (optional)
if ip link show eth0 >/dev/null 2>&1; then
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
fi

exit 0
EOF

chmod +x /etc/rc.local

echo "Enabling services..."

# Enable services to start on boot
systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq

echo "================================================"
echo "Wall-E Access Point Configuration Complete!"
echo "================================================"

echo ""
echo "Network Details:"
echo "  SSID: Wall-E-Robot"
echo "  Password: WallE2024"
echo "  Wall-E IP: 192.168.4.1"
echo "  DHCP Range: 192.168.4.10 - 192.168.4.50"
echo ""
echo "ESP32-CAM Configuration:"
echo "  Update your ESP32-CAM code with:"
echo "  const char* ssid = \"Wall-E-Robot\";"
echo "  const char* password = \"WallE2024\";"
echo ""
echo "Access URLs after reboot:"
echo "  http://192.168.4.1:5000 (direct IP)"
echo "  http://wall-e.local:5000 (hostname)"
echo ""

read -p "Do you want to reboot now to activate the access point? (y/n): " reboot_choice

if [[ $reboot_choice =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds..."
    echo "After reboot:"
    echo "1. Connect to 'Wall-E-Robot' WiFi (password: WallE2024)"
    echo "2. Update ESP32-CAM with new WiFi credentials"
    echo "3. Access Wall-E at http://192.168.4.1:5000"
    sleep 5
    reboot
else
    echo ""
    echo "Manual reboot required to activate access point:"
    echo "sudo reboot"
    echo ""
    echo "Don't forget to update your ESP32-CAM WiFi credentials!"
fi