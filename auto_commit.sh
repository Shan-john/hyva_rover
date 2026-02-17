#!/bin/bash

# Configuration
INTERVAL=30 # Seconds between checks
BRANCH="main"

echo "Starting auto-commit script for branch: $BRANCH"

while true; do
    # Check for changes
    if [[ -n $(git status --porcelain) ]]; then
        echo "Changes detected. Committing and pushing..."
        
        git add .
        
        # Current timestamp
        TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
        
        git commit -m "Auto-commit: $TIMESTAMP"
        
        git push origin "$BRANCH"
        
        echo "Done for now."
    else
        echo "No changes detected."
    fi
    
    sleep $INTERVAL
done
