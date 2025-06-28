#!/bin/bash
#
# Wall-E Dynamic Network Manager
# Switches between WiFi Client mode and Access Point mode
# Author: Wall-E Control System
#

SCRIPT_DIR="$(dirname "$0")"
CONFIG_FILE="/etc/wall-e/network-config"
STATE_FILE="/tmp/wall-e-network-state"
BACKUP_DIR="/etc/wall-e/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}This script must be run as root${NC}"
        echo "Usage: sudo $0"
        exit 1
    fi
}

# Create necessary directories
setup_directories() {
    mkdir -p /etc/wall-e
    mkdir -p "$BACKUP_DIR"
}

# Show colored header
show_header() {
    clear
    echo -e "${CYAN}================================================${NC}"
    echo -e "${CYAN}           🤖 Wall-E Network Manager            ${NC}"
    echo -e "${CYAN}================================================${NC}"
    echo ""
}

# Get current mode
get_current_mode() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "unknown"
    fi
}

# Show current status
show_status() {
    echo -e "${BLUE}Current Network Status:${NC}"
    echo "======================="

    local current_mode=$(get_current_mode)
    echo -e "Mode: ${YELLOW}$current_mode${NC}"

    # Check services
    if systemctl is-active --quiet hostapd; then
        echo -e "Access Point: ${GREEN}Active${NC}"
        echo -e "SSID: ${CYAN}Wall-E-Robot${NC}"
    else
        echo -e "Access Point: ${RED}Inactive${NC}"
    fi

    if systemctl is-active --quiet NetworkManager; then
        echo -e "NetworkManager: ${GREEN}Active${NC}"
    elif systemctl is-active --quiet wpa_supplicant; then
        echo -e "WiFi Client: ${GREEN}Active${NC}"
    else
        echo -e "WiFi Client: ${RED}Inactive${NC}"
    fi

    # Show interface status
    echo ""
    echo -e "${BLUE}Interface Status:${NC}"
    local wlan0_ip=$(ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
    if [ -n "$wlan0_ip" ]; then
        echo -e "wlan0: ${GREEN}$wlan0_ip${NC}"
    else
        echo -e "wlan0: ${RED}No IP${NC}"
    fi

    # Show connected clients (if AP mode)
    if systemctl is-active --quiet hostapd; then
        local clients=$(iw dev wlan0 station dump 2>/dev/null | grep Station | wc -l)
        echo -e "Connected devices: ${CYAN}$clients${NC}"
    fi

    echo ""
}

# Show main menu
show_menu() {
    show_header
    show_status

    echo -e "${PURPLE}Available Actions:${NC}"
    echo "=================="
    echo "1. 📶 Switch to WiFi Client Mode (connect to home WiFi)"
    echo "2. 📡 Switch to Access Point Mode (Wall-E hotspot)"
    echo "3. 📋 Show detailed status"
    echo "4. ⚙️  Configure WiFi credentials"
    echo "5. 🔄 Restart network services"
    echo "6. 🧪 Test current connection"
    echo "7. 🏠 Auto-detect best mode"
    echo "8. 💾 Backup/Restore configurations"
    echo "9. ❌ Exit"
    echo ""
}

# Backup current configuration
backup_config() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/backup_$timestamp"

    echo "Creating backup..."
    mkdir -p "$backup_path"

    # Backup important files
    [ -f /etc/dhcpcd.conf ] && cp /etc/dhcpcd.conf "$backup_path/"
    [ -f /etc/hostapd/hostapd.conf ] && cp /etc/hostapd/hostapd.conf "$backup_path/"
    [ -f /etc/dnsmasq.conf ] && cp /etc/dnsmasq.conf "$backup_path/"
    [ -f /etc/wpa_supplicant/wpa_supplicant.conf ] && cp /etc/wpa_supplicant/wpa_supplicant.conf "$backup_path/"

    echo "✓ Configuration backed up to $backup_path"
}

# Switch to WiFi Client Mode
switch_to_client_mode() {
    echo -e "${YELLOW}Switching to WiFi Client Mode...${NC}"

    # Backup current config
    backup_config

    # Stop AP services
    echo "Stopping Access Point services..."
    systemctl stop hostapd 2>/dev/null
    systemctl stop dnsmasq 2>/dev/null
    systemctl disable hostapd 2>/dev/null
    systemctl disable dnsmasq 2>/dev/null

    # Reset interface
    echo "Resetting network interface..."
    ip addr flush dev wlan0
    ip link set wlan0 down
    sleep 2
    ip link set wlan0 up

    # Remove static IP configuration
    if [ -f /etc/dhcpcd.conf ]; then
        sed -i '/# Wall-E Access Point/,/nohook wpa_supplicant/d' /etc/dhcpcd.conf
    fi

    # Configure for client mode
    if systemctl is-available NetworkManager >/dev/null 2>&1; then
        echo "Using NetworkManager..."

        # Remove any ignore rules
        rm -f /etc/NetworkManager/conf.d/99-unmanaged-devices.conf

        # Restart NetworkManager
        systemctl restart NetworkManager
        sleep 5

        # Check for saved connections
        if nmcli connection show | grep -q wifi; then
            echo "Found saved WiFi connections, attempting to connect..."
            nmcli device wifi connect "$(nmcli connection show | grep wifi | head -1 | awk '{print $1}')" 2>/dev/null
        fi

    else
        echo "Using wpa_supplicant..."

        # Unmask and enable wpa_supplicant
        systemctl unmask wpa_supplicant 2>/dev/null
        systemctl enable wpa_supplicant 2>/dev/null

        # Start services
        if systemctl is-available dhcpcd >/dev/null 2>&1; then
            systemctl restart dhcpcd
        elif systemctl is-available dhcpcd5 >/dev/null 2>&1; then
            systemctl restart dhcpcd5
        fi

        systemctl restart wpa_supplicant
    fi

    # Save state
    echo "client" > "$STATE_FILE"

    echo -e "${GREEN}✓ Switched to WiFi Client Mode${NC}"
    echo ""
    echo "Waiting for connection..."
    sleep 10

    # Check if connected
    if ip route | grep -q default; then
        local ip=$(hostname -I | awk '{print $1}')
        echo -e "${GREEN}✓ Connected! IP: $ip${NC}"
        echo -e "Access Wall-E at: ${CYAN}http://$ip:5000${NC}"
    else
        echo -e "${YELLOW}⚠ Not connected yet. You may need to configure WiFi credentials.${NC}"
        echo "Run option 4 to configure WiFi or use: sudo raspi-config"
    fi
}

# Switch to Access Point Mode
switch_to_ap_mode() {
    echo -e "${YELLOW}Switching to Access Point Mode...${NC}"

    # Backup current config
    backup_config

    # Stop client services
    echo "Stopping WiFi client services..."
    systemctl stop NetworkManager 2>/dev/null
    systemctl stop wpa_supplicant 2>/dev/null

    # Install required packages if missing
    if ! command -v hostapd >/dev/null 2>&1; then
        echo "Installing hostapd and dnsmasq..."
        apt-get update
        apt-get install -y hostapd dnsmasq
    fi

    # Configure hostapd
    echo "Configuring Access Point..."
    mkdir -p /etc/hostapd

    cat > /etc/hostapd/hostapd.conf << 'EOF'
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
wpa_pairwise=CCMP
rsn_pairwise=CCMP
country_code=US
ieee80211n=1
ieee80211d=1
EOF

    # Configure dnsmasq
    cat > /etc/dnsmasq.conf << 'EOF'
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
local=/walle/
domain=walle
address=/wall-e.local/192.168.4.1
EOF

    # Configure static IP
    if ! grep -q "# Wall-E Access Point" /etc/dhcpcd.conf 2>/dev/null; then
        cat >> /etc/dhcpcd.conf << 'EOF'

# Wall-E Access Point Configuration
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF
    fi

    # Set hostapd configuration path
    echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > /etc/default/hostapd

    # Reset interface and configure
    ip addr flush dev wlan0
    ip link set wlan0 down
    sleep 2
    ip addr add 192.168.4.1/24 dev wlan0
    ip link set wlan0 up

    # Enable and start services
    systemctl enable hostapd
    systemctl enable dnsmasq
    systemctl start hostapd
    systemctl start dnsmasq

    # Save state
    echo "access_point" > "$STATE_FILE"

    sleep 5

    # Check if AP is working
    if systemctl is-active --quiet hostapd; then
        echo -e "${GREEN}✓ Access Point Mode Active${NC}"
        echo ""
        echo -e "${CYAN}Network Details:${NC}"
        echo "  SSID: Wall-E-Robot"
        echo "  Password: WallE2024"
        echo "  Pi IP: 192.168.4.1"
        echo "  Web Interface: http://192.168.4.1:5000"
        echo ""
        echo -e "${YELLOW}Connect your devices to 'Wall-E-Robot' network${NC}"
    else
        echo -e "${RED}✗ Failed to start Access Point${NC}"
        echo "Check logs: sudo journalctl -u hostapd"
    fi
}

# Configure WiFi credentials
configure_wifi() {
    echo -e "${YELLOW}WiFi Configuration${NC}"
    echo "=================="

    if systemctl is-available NetworkManager >/dev/null 2>&1; then
        echo "Using NetworkManager interface..."
        nmtui
    else
        echo "Manual WiFi configuration:"
        echo ""
        read -p "Enter WiFi SSID: " wifi_ssid
        read -s -p "Enter WiFi Password: " wifi_password
        echo ""

        # Create wpa_supplicant config
        cat > /etc/wpa_supplicant/wpa_supplicant.conf << EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$wifi_ssid"
    psk="$wifi_password"
    key_mgmt=WPA-PSK
}
EOF

        chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf
        echo -e "${GREEN}✓ WiFi credentials saved${NC}"
    fi
}

# Show detailed status
show_detailed_status() {
    echo -e "${BLUE}Detailed Network Status${NC}"
    echo "======================"
    echo ""

    # Interface details
    echo -e "${YELLOW}Interface Information:${NC}"
    ip addr show wlan0
    echo ""

    # Service status
    echo -e "${YELLOW}Service Status:${NC}"
    services=("hostapd" "dnsmasq" "NetworkManager" "wpa_supplicant" "dhcpcd" "dhcpcd5")
    for service in "${services[@]}"; do
        if systemctl is-available "$service" >/dev/null 2>&1; then
            status=$(systemctl is-active "$service")
            case $status in
                "active") color=$GREEN ;;
                "inactive") color=$YELLOW ;;
                *) color=$RED ;;
            esac
            printf "  %-15s: ${color}%s${NC}\n" "$service" "$status"
        fi
    done
    echo ""

    # Routing information
    echo -e "${YELLOW}Routing Table:${NC}"
    ip route show
    echo ""

    # WiFi scan (if in client mode)
    if [ "$(get_current_mode)" = "client" ]; then
        echo -e "${YELLOW}Available WiFi Networks:${NC}"
        if systemctl is-active --quiet NetworkManager; then
            nmcli device wifi list 2>/dev/null || echo "No networks found"
        else
            iwlist wlan0 scan 2>/dev/null | grep ESSID | head -10 || echo "Scan not available"
        fi
    fi
}

# Test current connection
test_connection() {
    echo -e "${YELLOW}Testing Connection...${NC}"
    echo "===================="

    local mode=$(get_current_mode)
    echo "Current mode: $mode"
    echo ""

    if [ "$mode" = "access_point" ]; then
        echo "Testing Access Point..."
        if systemctl is-active --quiet hostapd; then
            echo -e "${GREEN}✓ hostapd is running${NC}"
        else
            echo -e "${RED}✗ hostapd is not running${NC}"
        fi

        if systemctl is-active --quiet dnsmasq; then
            echo -e "${GREEN}✓ dnsmasq is running${NC}"
        else
            echo -e "${RED}✗ dnsmasq is not running${NC}"
        fi

        if ip addr show wlan0 | grep -q "192.168.4.1"; then
            echo -e "${GREEN}✓ AP IP configured${NC}"
        else
            echo -e "${RED}✗ AP IP not configured${NC}"
        fi

    elif [ "$mode" = "client" ]; then
        echo "Testing WiFi Client..."

        if ip route | grep -q default; then
            echo -e "${GREEN}✓ Default route exists${NC}"
        else
            echo -e "${RED}✗ No default route${NC}"
        fi

        echo "Testing internet connectivity..."
        if ping -c 3 8.8.8.8 >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Internet connection working${NC}"
        else
            echo -e "${RED}✗ No internet connection${NC}"
        fi

        local ip=$(hostname -I | awk '{print $1}')
        if [ -n "$ip" ]; then
            echo -e "${GREEN}✓ IP address: $ip${NC}"
        else
            echo -e "${RED}✗ No IP address${NC}"
        fi
    fi

    # Test Wall-E service
    echo ""
    echo "Testing Wall-E service..."
    if systemctl is-active --quiet walle-control; then
        echo -e "${GREEN}✓ Wall-E service is running${NC}"
        local port_check=$(netstat -tlnp 2>/dev/null | grep :5000 || ss -tlnp 2>/dev/null | grep :5000)
        if [ -n "$port_check" ]; then
            echo -e "${GREEN}✓ Port 5000 is listening${NC}"
        else
            echo -e "${YELLOW}⚠ Port 5000 not detected${NC}"
        fi
    else
        echo -e "${RED}✗ Wall-E service not running${NC}"
    fi
}

# Auto-detect best mode
auto_detect_mode() {
    echo -e "${YELLOW}Auto-detecting best network mode...${NC}"
    echo ""

    # Check if we can connect to saved WiFi
    if systemctl is-available NetworkManager >/dev/null 2>&1; then
        echo "Checking saved WiFi connections..."
        if nmcli connection show | grep -q wifi; then
            echo "Found saved WiFi connections, trying client mode..."
            switch_to_client_mode
            sleep 15

            if ip route | grep -q default; then
                echo -e "${GREEN}✓ Successfully connected to WiFi${NC}"
                return
            fi
        fi
    fi

    echo "No WiFi connection available, switching to Access Point mode..."
    switch_to_ap_mode
}

# Restart network services
restart_services() {
    echo -e "${YELLOW}Restarting network services...${NC}"

    local mode=$(get_current_mode)

    if [ "$mode" = "access_point" ]; then
        systemctl restart hostapd
        systemctl restart dnsmasq
        echo -e "${GREEN}✓ Access Point services restarted${NC}"
    elif [ "$mode" = "client" ]; then
        if systemctl is-available NetworkManager >/dev/null 2>&1; then
            systemctl restart NetworkManager
            echo -e "${GREEN}✓ NetworkManager restarted${NC}"
        else
            systemctl restart wpa_supplicant
            systemctl restart dhcpcd 2>/dev/null || systemctl restart dhcpcd5 2>/dev/null
            echo -e "${GREEN}✓ WiFi client services restarted${NC}"
        fi
    fi

    # Always restart Wall-E service
    if systemctl is-available walle-control >/dev/null 2>&1; then
        systemctl restart walle-control
        echo -e "${GREEN}✓ Wall-E service restarted${NC}"
    fi
}

# Backup and restore menu
backup_restore_menu() {
    echo -e "${YELLOW}Backup & Restore${NC}"
    echo "==============="
    echo ""
    echo "1. Create backup"
    echo "2. List backups"
    echo "3. Restore from backup"
    echo "4. Return to main menu"
    echo ""

    read -p "Choose option: " backup_choice

    case $backup_choice in
        1)
            backup_config
            ;;
        2)
            echo "Available backups:"
            ls -la "$BACKUP_DIR/" 2>/dev/null || echo "No backups found"
            ;;
        3)
            echo "Available backups:"
            local backups=($(ls "$BACKUP_DIR/" 2>/dev/null))
            if [ ${#backups[@]} -eq 0 ]; then
                echo "No backups found"
                return
            fi

            for i in "${!backups[@]}"; do
                echo "$((i+1)). ${backups[i]}"
            done

            read -p "Select backup to restore (number): " backup_num
            if [[ "$backup_num" =~ ^[0-9]+$ ]] && [ "$backup_num" -ge 1 ] && [ "$backup_num" -le ${#backups[@]} ]; then
                local selected_backup="${backups[$((backup_num-1))]}"
                echo "Restoring from $selected_backup..."

                # Restore files
                [ -f "$BACKUP_DIR/$selected_backup/dhcpcd.conf" ] && cp "$BACKUP_DIR/$selected_backup/dhcpcd.conf" /etc/
                [ -f "$BACKUP_DIR/$selected_backup/hostapd.conf" ] && cp "$BACKUP_DIR/$selected_backup/hostapd.conf" /etc/hostapd/
                [ -f "$BACKUP_DIR/$selected_backup/dnsmasq.conf" ] && cp "$BACKUP_DIR/$selected_backup/dnsmasq.conf" /etc/
                [ -f "$BACKUP_DIR/$selected_backup/wpa_supplicant.conf" ] && cp "$BACKUP_DIR/$selected_backup/wpa_supplicant.conf" /etc/wpa_supplicant/

                echo -e "${GREEN}✓ Configuration restored${NC}"
                echo "Restart required: sudo reboot"
            else
                echo "Invalid selection"
            fi
            ;;
        4)
            return
            ;;
        *)
            echo "Invalid option"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
}

# Main function
main() {
    check_root
    setup_directories

    while true; do
        show_menu
        read -p "Choose an option (1-9): " choice
        echo ""

        case $choice in
            1)
                switch_to_client_mode
                ;;
            2)
                switch_to_ap_mode
                ;;
            3)
                show_detailed_status
                ;;
            4)
                configure_wifi
                ;;
            5)
                restart_services
                ;;
            6)
                test_connection
                ;;
            7)
                auto_detect_mode
                ;;
            8)
                backup_restore_menu
                ;;
            9)
                echo -e "${GREEN}Goodbye! 🤖${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Please choose 1-9.${NC}"
                ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main "$@"