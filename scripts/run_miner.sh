#!/usr/bin/env bash
# Run CarbonScope miner
set -euo pipefail

NETUID="${NETUID:-1}"
WALLET_NAME="${WALLET_NAME:-miner}"
HOTKEY="${HOTKEY:-default}"
SUBTENSOR_NETWORK="${SUBTENSOR_NETWORK:-test}"
AXON_PORT="${AXON_PORT:-8091}"
RATE_LIMIT_MAX="${RATE_LIMIT_MAX:-60}"
RATE_LIMIT_WINDOW="${RATE_LIMIT_WINDOW:-60}"

echo "=== Starting CarbonScope Miner ==="
echo "Network:  $SUBTENSOR_NETWORK"
echo "NetUID:   $NETUID"
echo "Port:     $AXON_PORT"
echo "Rate:     ${RATE_LIMIT_MAX}/${RATE_LIMIT_WINDOW}s"

export MINER_RATE_LIMIT_MAX="$RATE_LIMIT_MAX"
export MINER_RATE_LIMIT_WINDOW="$RATE_LIMIT_WINDOW"

python -m neurons.miner \
    --netuid "$NETUID" \
    --wallet.name "$WALLET_NAME" \
    --wallet.hotkey "$HOTKEY" \
    --subtensor.network "$SUBTENSOR_NETWORK" \
    --axon.port "$AXON_PORT" \
    "$@"
