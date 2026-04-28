#!/bin/bash
echo "Stopping all services..."
while read pid; do
    kill "$pid" 2>/dev/null
done < ".services.pids"
rm ".services.pids"
echo "All services stopped."
