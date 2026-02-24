#!/bin/bash
# Monitor download progress in real-time

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOWNLOAD_DIR="$SCRIPT_DIR/data/downloads"
STATE_FILE="$SCRIPT_DIR/data/state.json"

while true; do
    clear
    echo "============================================"
    echo "  Apple Schematic Downloader - Live Stats"
    echo "============================================"
    echo ""

    # Process status
    SCRAPER_PID=$(pgrep -f "tg_schematic_downloader.py" | head -n 1)
    if [ -n "$SCRAPER_PID" ]; then
        echo "✅ Status: RUNNING (PID $SCRAPER_PID)"
        ps -p "$SCRAPER_PID" -o etime,%cpu,%mem | tail -1 | awk '{print "   Runtime: " $1 "  |  CPU: " $2 "%  |  MEM: " $3 "%"}'
    else
        echo "❌ Status: STOPPED"
    fi

    echo ""
    echo "📊 Download Statistics:"
    echo "   Total Files: $(find "$DOWNLOAD_DIR" -type f | wc -l | xargs)"
    echo "   Total Size:  $(du -sh "$DOWNLOAD_DIR" | awk '{print $1}')"
    echo ""

    echo "📁 Files by Channel:"
    for dir in "$DOWNLOAD_DIR"/*/ ; do
        if [ -d "$dir" ]; then
            name=$(basename "$dir")
            count=$(find "$dir" -type f | wc -l | xargs)
            size=$(du -sh "$dir" 2>/dev/null | awk '{print $1}')
            if [ "$count" -gt 0 ]; then
                printf "   %-30s %4s files  %8s\n" "$name" "$count" "$size"
            fi
        fi
    done

    echo ""
    echo "🆕 Latest 5 downloads:"
    find "$DOWNLOAD_DIR" -type f -print0 \
      | xargs -0 stat -f "%m %N" 2>/dev/null \
      | sort -rn | head -5 \
      | while IFS= read -r line; do
            ts=${line%% *}
            file=${line#* }
            echo "   $(basename "$file")"
        done

    echo ""
    echo "Press Ctrl+C to exit monitoring"
    echo "Last update: $(date '+%H:%M:%S')"

    sleep 5
done
