#!/bin/bash
# deploy.sh - NASTool Agent one-click deploy
# Run on 192.168.1.123: bash deploy.sh

set -e

echo "============================================"
echo "  NASTool Agent Deployment"
echo "============================================"

# Check Python3
echo "[1/5] Checking Python3..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found!"
    echo "Installing Python3..."
    sudo apt update && sudo apt install -y python3 python3-pip
fi
python3 --version

# Install dependencies
echo ""
echo "[2/5] Installing dependencies..."
pip3 install --user websocket-client requests -q
echo "Done."

# Create agent directory
echo ""
echo "[3/5] Creating agent directory..."
AGENT_DIR="$HOME/nastool-agent"
mkdir -p "$AGENT_DIR"
echo "Agent dir: $AGENT_DIR"

# Copy agent script (if running locally)
# User needs to copy nastool_agent.py and requirements.txt to the target device
echo ""
echo "[4/5] Checking agent files..."
if [ -f "$AGENT_DIR/nastool_agent.py" ]; then
    echo "Agent script found."
else
    echo "WARNING: nastool_agent.py not found in $AGENT_DIR"
    echo "Please copy nastool_agent.py and requirements.txt to $AGENT_DIR"
fi

# Get device info
echo ""
echo "[5/5] Device Information:"
echo "  Hostname: $(hostname)"
echo "  OS: $(uname -s) $(uname -r)"
echo "  Arch: $(uname -m)"
echo "  Python: $(python3 --version 2>&1)"
echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "Next step: Start the agent"
echo ""
echo "  python3 $AGENT_DIR/nastool_agent.py \\"
echo "    --relay http://120.77.249.3:18888 \\"
echo "    --device-id nvidia-123 \\"
echo "    --device-name 'NVIDIA Workstation' \\"
echo "    --device-type nvidia \\"
echo "    --group test"
echo ""
echo "Or test with --once flag:"
echo "  python3 $AGENT_DIR/nastool_agent.py \\"
echo "    --relay http://120.77.249.3:18888 \\"
echo "    --device-id nvidia-123 \\"
echo "    --once"
