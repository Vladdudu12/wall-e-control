#!/bin/bash
# Wall-E Control System Service Manager

SERVICE_NAME="walle-control.service"

show_help() {
    echo "Wall-E Control System Service Manager"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start the Wall-E service"
    echo "  stop      Stop the Wall-E service"
    echo "  restart   Restart the Wall-E service"
    echo "  status    Show service status"
    echo "  logs      Show service logs (live)"
    echo "  enable    Enable auto-start on boot"
    echo "  disable   Disable auto-start on boot"
    echo "  url       Show access URLs"
    echo "  help      Show this help message"
    echo ""
}

show_urls() {
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    echo "Wall-E Control System Access URLs:"
    echo "  Local:    http://localhost:5000"
    echo "  Network:  http://$IP_ADDRESS:5000"
    echo "  Hostname: http://wall-e.local:5000"
}

case "$1" in
    start)
        echo "Starting Wall-E Control System..."
        sudo systemctl start $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager -l
        echo ""
        show_urls
        ;;
    
    stop)
        echo "Stopping Wall-E Control System..."
        sudo systemctl stop $SERVICE_NAME
        echo "✓ Wall-E service stopped"
        ;;
    
    restart)
        echo "Restarting Wall-E Control System..."
        sudo systemctl restart $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager -l
        echo ""
        show_urls
        ;;
    
    status)
        echo "Wall-E Control System Status:"
        sudo systemctl status $SERVICE_NAME --no-pager -l
        echo ""
        if systemctl is-active --quiet $SERVICE_NAME; then
            show_urls
        fi
        ;;
    
    logs)
        echo "Wall-E Control System Logs (Ctrl+C to exit):"
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    
    enable)
        echo "Enabling Wall-E auto-start on boot..."
        sudo systemctl enable $SERVICE_NAME
        echo "✓ Wall-E will now start automatically on boot"
        ;;
    
    disable)
        echo "Disabling Wall-E auto-start on boot..."
        sudo systemctl disable $SERVICE_NAME
        echo "✓ Wall-E auto-start disabled"
        ;;
    
    url)
        show_urls
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        echo "Error: Unknown command '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac