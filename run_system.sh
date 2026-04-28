#!/bin/bash

# image-annotation-system runner
# Orchestrates all microservices and logs output to a central file.

export PYTHONPATH=$PWD

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    set -a
    source .env
    set +a
fi

LOG_FILE="system.log"
PID_FILE=".services.pids"

# Clear previous logs and PID file
> "$LOG_FILE"
> "$PID_FILE"

echo "--- Starting Image Annotation System ---"
echo "Logs will be written to: $LOG_FILE"

# Function to start a service
start_service() {
    local name=$1
    local path=$2
    echo "Starting $name..."
    python3 "$path" >> "$LOG_FILE" 2>&1 &
    echo $! >> "$PID_FILE"
}

# 1. Start core services
start_service "Upload Service" "services/upload/service.py"
start_service "Image Processing" "services/image_processing/service.py"
start_service "Document DB" "services/document_db/service.py"
start_service "Embedding Service" "services/embedding/service.py"
start_service "Vector DB" "services/vector_db/service.py"

echo "----------------------------------------"
echo "All services are running in the background."
echo "You can now use the CLI in this terminal."
echo "Example: python3 services/cli/main.py upload sample_data/dog.jpg"
echo "----------------------------------------"
echo "To stop all services, run: ./stop_services.sh"
echo "To view live logs, run: tail -f $LOG_FILE"

# Make the stop script on the fly for convenience
cat <<EOF > stop_services.sh
#!/bin/bash
echo "Stopping all services..."
while read pid; do
    kill "\$pid" 2>/dev/null
done < "$PID_FILE"
rm "$PID_FILE"
echo "All services stopped."
EOF
chmod +x stop_services.sh
