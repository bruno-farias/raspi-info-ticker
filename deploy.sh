#!/bin/bash
# Deploy script for Raspberry Pi Info Ticker

PI_USER="bruno"
PI_HOST="zero.local"
PI_PATH="~/raspi-info-ticker"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
DEPLOY_CONFIG=false
CONFIG_ONLY=false
RESTART=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-config)
            DEPLOY_CONFIG=true
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            DEPLOY_CONFIG=true
            shift
            ;;
        --no-restart)
            RESTART=false
            shift
            ;;
        -h|--help)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-config    Also deploy config.yaml (includes API keys)"
            echo "  --config-only    Deploy only config.yaml (no source/assets)"
            echo "  --no-restart     Don't restart the display service after deployment"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Starting deployment to $PI_USER@$PI_HOST${NC}"

# Deploy source code (skip if config-only)
if [ "$CONFIG_ONLY" = false ]; then
    echo -e "${YELLOW}Deploying source files...${NC}"
    rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
        src/ $PI_USER@$PI_HOST:$PI_PATH/src/

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to deploy source files${NC}"
        exit 1
    fi

    # Deploy assets
    echo -e "${YELLOW}Deploying assets...${NC}"
    rsync -av assets/ $PI_USER@$PI_HOST:$PI_PATH/assets/

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to deploy assets${NC}"
        exit 1
    fi
fi

# Deploy config if requested
if [ "$DEPLOY_CONFIG" = true ]; then
    echo -e "${YELLOW}Deploying config.yaml (with API keys)...${NC}"
    scp config/config.yaml $PI_USER@$PI_HOST:$PI_PATH/config/
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to deploy config.yaml${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Skipping config.yaml (use --with-config to deploy)${NC}"
fi

# Restart display service
if [ "$RESTART" = true ]; then
    echo -e "${YELLOW}Restarting display service...${NC}"
    ssh $PI_USER@$PI_HOST "sudo pkill -f 'python.*main_v2'"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Display service restarted${NC}"
    else
        echo -e "${YELLOW}No running display service found (this is OK)${NC}"
    fi
fi

echo -e "${GREEN}Deployment complete!${NC}"
