#!/bin/bash
echo "================================================"
echo "Wall-E Control System - Service Setup"
echo "================================================"

# Stop and disable the old Wall-E service
echo "Stopping old Wall-E service..."
sudo systemctl stop walle.service
sudo systemctl disable walle.service
echo "✓ Old service stopped and disabled"

# Check if port 5000 is still in use
echo "Checking port 5000..."
if sudo netstat -tlnp | grep :5000; then
    echo "Port 5000 is still in use. Finding and killing processes..."
    sudo fuser -k 5000/tcp
    sleep 2
fi

# Remove old service file
if [ -f /etc/systemd/system/walle.service ]; then
    sudo rm /etc/systemd/system/walle.service
    echo "✓ Old service file removed"
fi

echo ""
echo "================================================"
echo "Setting up NEW Wall-E Control System"
echo "================================================"

# Get current directory and username
BASEDIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
USERNAME="$( logname )"

echo "Base directory: $BASEDIR"
echo "Username: $USERNAME"

# Update system packages
echo ""
echo "Updating system packages..."
sudo apt-get update

# Install required system packages
echo ""
echo "Installing system dependencies..."
sudo apt-get install -y espeak espeak-data
sudo apt-get install -y alsa-utils
sudo apt-get install -y python3-pip python3-venv
sudo apt-get install -y git
sudo apt-get install -y i2c-tools

# Create virtual environment if it doesn't exist
if [ ! -d "$BASEDIR/walle-env" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv "$BASEDIR/walle-env"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment and install packages
echo ""
echo "Installing Python packages..."
source "$BASEDIR/walle-env/bin/activate"
pip install --upgrade pip

# Install packages from requirements.txt if it exists
if [ -f "$BASEDIR/wall-e-control/requirements.txt" ]; then
    pip install -r "$BASEDIR/wall-e-control/requirements.txt"
else
    # Install packages manually
    pip install flask==2.3.3
    pip install flask-socketio==5.3.6
    pip install pygame==2.5.2
    pip install pyserial==3.5
    pip install python-socketio==5.8.0
    pip install adafruit-circuitpython-ssd1306==2.12.14
    pip install pillow==10.0.1
    pip install numpy==1.24.3
fi

echo "✓ Python packages installed"

# Create new systemd service file
echo ""
echo "Creating new systemd service..."

sudo tee /etc/systemd/system/walle-control.service > /dev/null <<EOF
[Unit]
Description=Wall-E Control System
After=multi-user.target network.target sound.target
Wants=network.target

[Service]
Type=simple
WorkingDirectory=$BASEDIR/wall-e-control
ExecStart=$BASEDIR/walle-env/bin/python3 app.py
KillSignal=SIGINT
Restart=on-failure
RestartSec=5
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=PYTHONPATH=$BASEDIR/wall-e-control
User=$USERNAME
Group=$USERNAME

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service file created at /etc/systemd/system/walle-control.service"

# Set permissions and enable the service
sudo chmod 644 /etc/systemd/system/walle-control.service
sudo systemctl daemon-reload
sudo systemctl enable walle-control.service

echo ""
echo "================================================"
echo "Testing the new service..."
echo "================================================"

# Start the service
sudo systemctl start walle-control.service

# Wait a moment for it to start
sleep 3

# Check service status
echo "Service status:"
sudo systemctl status walle-control.service --no-pager -l

# Check if port 5000 is now being used by our service
echo ""
echo "Port 5000 status:"
sudo netstat -tlnp | grep :5000

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo "✓ Old Wall-E service stopped and removed"
echo "✓ New Wall-E Control System installed and started"
echo "✓ Service will auto-start on boot"
echo ""
echo "Access your Wall-E Control System:"
echo "  Local:    http://localhost:5000"
echo "  Network:  http://$IP_ADDRESS:5000"
echo "  Hostname: http://wall-e.local:5000"
echo ""
echo "Service management commands:"
echo "  Start:    sudo systemctl start walle-control.service"
echo "  Stop:     sudo systemctl stop walle-control.service"
echo "  Restart:  sudo systemctl restart walle-control.service"
echo "  Status:   sudo systemctl status walle-control.service"
echo "  Logs:     sudo journalctl -u walle-control.service -f"
echo ""
echo "Happy Wall-E controlling! 🤖"