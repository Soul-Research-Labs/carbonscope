#!/usr/bin/env bash
# Run CarbonScope validator
set -euo pipefail

NETUID="${NETUID:-1}"
WALLET_NAME="${WALLET_NAME:-validator}"
HOTKEY="${HOTKEY:-default}"
SUBTENSOR_NETWORK="${SUBTENSOR_NETWORK:-test}"
QUERY_INTERVAL="${QUERY_INTERVAL:-60}"
QUERY_TIMEOUT="${QUERY_TIMEOUT:-30}"
EMA_ALPHA="${EMA_ALPHA:-0.1}"

echo "=== Starting CarbonScope Validator ==="
echo "Network:  $SUBTENSOR_NETWORK"
echo "NetUID:   $NETUID"
echo "Interval: ${QUERY_INTERVAL}s  Timeout: ${QUERY_TIMEOUT}s  Alpha: $EMA_ALPHA"

python -m neurons.validator \
    --netuid "$NETUID" \
    --wallet.name "$WALLET_NAME" \
    --wallet.hotkey "$HOTKEY" \
    --subtensor.network "$SUBTENSOR_NETWORK" \
    --query_interval "$QUERY_INTERVAL" \
    --query_timeout "$QUERY_TIMEOUT" \
    --ema_alpha "$EMA_ALPHA" \
    "$@"
