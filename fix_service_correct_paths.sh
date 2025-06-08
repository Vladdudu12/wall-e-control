#!/bin/bash
echo "Fixing Wall-E Control Service with correct virtual environment path..."

# Stop the failing service
sudo systemctl stop walle-control.service

# Get correct paths based on your file structure
WALLE_DIR="$HOME/walle-server/wall-e-control"
VENV_PYTHON="$HOME/walle-server/wall-e-control/walle-env/bin/python3"
USERNAME=$(whoami)

echo "Using correct paths:"
echo "  Working Directory: $WALLE_DIR"
echo "  Python Executable: $VENV_PYTHON"
echo "  Username: $USERNAME"

# Verify the paths exist
echo ""
echo "Verifying paths..."

if [ -d "$WALLE_DIR" ]; then
    echo "✓ Working directory exists"
else
    echo "❌ Working directory missing: $WALLE_DIR"
    exit 1
fi

if [ -f "$VENV_PYTHON" ]; then
    echo "✓ Python executable exists"
else
    echo "❌ Python executable missing: $VENV_PYTHON"
    echo "Creating virtual environment..."
    cd "$WALLE_DIR"
    python3 -m venv walle-env
    
    # Install requirements
    echo "Installing requirements..."
    source walle-env/bin/activate
    pip install --upgrade pip
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    else
        pip install flask flask-socketio pygame pyserial
    fi
    deactivate
fi

if [ -f "$WALLE_DIR/app.py" ]; then
    echo "✓ app.py exists"
else
    echo "❌ app.py missing"
    exit 1
fi

# Create the corrected service file
echo ""
echo "Creating service file with correct paths..."

sudo tee /etc/systemd/system/walle-control.service > /dev/null <<EOF
[Unit]
Description=Wall-E Control System
After=multi-user.target network.target sound.target
Wants=network.target

[Service]
Type=simple
WorkingDirectory=$WALLE_DIR
ExecStart=$VENV_PYTHON app.py
KillSignal=SIGINT
Restart=on-failure
RestartSec=5
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=PYTHONPATH=$WALLE_DIR
User=$USERNAME
Group=$USERNAME

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service file created with correct paths"

# Reload systemd and start service
sudo chmod 644 /etc/systemd/system/walle-control.service
sudo systemctl daemon-reload
sudo systemctl enable walle-control.service

echo ""
echo "Starting Wall-E Control Service..."
sudo systemctl start walle-control.service

# Wait a moment for startup
sleep 5

# Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status walle-control.service --no-pager -l

# Check if it's actually running
if systemctl is-active --quiet walle-control.service; then
    echo ""
    echo "🎉 SUCCESS! Wall-E Control System is running!"
    
    # Get IP address
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "Access your Wall-E Control System:"
    echo "  Local:    http://localhost:5000"
    echo "  Network:  http://$IP_ADDRESS:5000"
    echo "  Hostname: http://wall-e.local:5000"
    
    # Check if port 5000 is being used
    echo ""
    echo "Port 5000 status:"
    sudo netstat -tlnp | grep :5000
    
else
    echo ""
    echo "❌ Service failed to start. Recent logs:"
    sudo journalctl -u walle-control.service --no-pager -n 20
fi

echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status walle-control.service"
echo "  View logs:    sudo journalctl -u walle-control.service -f"
echo "  Restart:      sudo systemctl restart walle-control.service"