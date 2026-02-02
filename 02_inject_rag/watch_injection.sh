#!/bin/bash

# Colors
GREEN='\033[32m'
RESET='\033[0m'

# Calculate total documents to inject from JSONL files
TOTAL=$(cat 01_clean/02_structured/*.jsonl 2>/dev/null | wc -l)

if [ "$TOTAL" -eq 0 ]; then
    echo "No documents found in 01_clean/02_structured/*.jsonl"
    exit 1
fi

# Store start timestamp and initial count
START_TIME=$(date +%s)
INITIAL_COUNT=$(curl -X POST http://localhost:6333/collections/law_library/points/count \
    -H 'Content-Type: application/json' \
    -d '{}' -s | jq -r '.result.count // 0')

echo "Total documents to inject: $TOTAL"
echo "Already indexed: $INITIAL_COUNT"
echo "Started at: $(date)"
echo ""

while true; do
    # Get current count from Qdrant
    COUNT=$(curl -X POST http://localhost:6333/collections/law_library/points/count \
        -H 'Content-Type: application/json' \
        -d '{}' -s | jq -r '.result.count // 0')

    # Calculate metrics
    NOW=$(date +%s)
    ELAPSED=$((NOW - START_TIME))
    MINS=$((ELAPSED / 60))
    SECS=$((ELAPSED % 60))

    # Documents indexed since script started
    INDEXED_SINCE_START=$((COUNT - INITIAL_COUNT))

    # Calculate percentage and progress bar
    if [ "$TOTAL" -gt 0 ]; then
        PERC=$((COUNT * 100 / TOTAL))
        FILLED=$((COUNT * 20 / TOTAL))
    else
        PERC=0
        FILLED=0
    fi
    [ "$PERC" -gt 100 ] && PERC=100
    [ "$FILLED" -gt 20 ] && FILLED=20

    # Build progress bar
    BAR=$(printf '%0.s#' $(seq 1 $FILLED 2>/dev/null))
    EMPTY=$(printf '%0.s-' $(seq 1 $((20 - FILLED)) 2>/dev/null))

    # Calculate speed and ETA based on documents indexed since script started
    if [ "$ELAPSED" -gt 0 ] && [ "$INDEXED_SINCE_START" -gt 0 ]; then
        SPEED=$((INDEXED_SINCE_START / ELAPSED))
        if [ "$SPEED" -gt 0 ] && [ "$COUNT" -lt "$TOTAL" ]; then
            ETA_MINS=$(( (TOTAL - COUNT) / SPEED / 60 ))
        else
            ETA_MINS=0
        fi
    else
        SPEED=0
        ETA_MINS=0
    fi

    # Status
    if [ "$PERC" -ge 100 ]; then
        STATUS="COMPLETE"
    else
        STATUS="INDEXING"
    fi

    # Clear and display
    clear
    echo -e "${GREEN}Status: [${STATUS}]"
    echo "Count:  ${COUNT} / ${TOTAL} (+${INDEXED_SINCE_START} this session)"
    echo "[${BAR}${EMPTY}] ${PERC}%"
    echo ""
    echo "Elapsed: ${MINS}m ${SECS}s"
    echo "Speed:   ${SPEED} docs/sec"
    echo -e "ETA:     ~${ETA_MINS} min${RESET}"

    sleep 5
done
