#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# JurisOne — Qdrant via Podman (Fedora / rootless)
# Named volume stores data in ~/.local/share/containers (native Linux FS)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONTAINER_NAME="qdrant-jurisone"
VOLUME_NAME="qdrant-jurisone-data"
QDRANT_IMAGE="docker.io/qdrant/qdrant:latest"
REST_PORT=6333
GRPC_PORT=6334

usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|remove|pull}"
    echo ""
    echo "  start    — Create volume + start Qdrant container (idempotent)"
    echo "  stop     — Stop the container"
    echo "  restart  — Stop + start"
    echo "  status   — Show container status and health"
    echo "  logs     — Tail container logs"
    echo "  remove   — Stop + remove container (keeps data volume)"
    echo "  pull     — Pull latest qdrant image"
    exit 1
}

cmd_pull() {
    echo "⬇  Pulling $QDRANT_IMAGE ..."
    podman pull "$QDRANT_IMAGE"
    echo "✅ Pull complete."
}

cmd_start() {
    # Create named volume if it doesn't exist
    if ! podman volume exists "$VOLUME_NAME" 2>/dev/null; then
        echo "📦 Creating Podman named volume: $VOLUME_NAME"
        podman volume create "$VOLUME_NAME"
    else
        echo "📦 Volume $VOLUME_NAME already exists — reusing."
    fi

    # Check if container already running
    if podman container exists "$CONTAINER_NAME" 2>/dev/null; then
        state=$(podman inspect --format '{{.State.Status}}' "$CONTAINER_NAME")
        if [ "$state" = "running" ]; then
            echo "✅ $CONTAINER_NAME is already running."
            echo "   REST API → http://localhost:$REST_PORT"
            echo "   Dashboard → http://localhost:$REST_PORT/dashboard"
            return
        else
            echo "🔄 Container exists but not running (state: $state). Restarting..."
            podman start "$CONTAINER_NAME"
            echo "✅ Started."
            return
        fi
    fi

    echo "🚀 Starting Qdrant container..."
    podman run -d \
        --name "$CONTAINER_NAME" \
        -p "127.0.0.1:${REST_PORT}:6333" \
        -p "127.0.0.1:${GRPC_PORT}:6334" \
        -v "${VOLUME_NAME}:/qdrant/storage:z" \
        --restart=unless-stopped \
        "$QDRANT_IMAGE"

    echo ""
    echo "✅ Qdrant is running!"
    echo "   REST API  → http://localhost:$REST_PORT"
    echo "   gRPC      → localhost:$GRPC_PORT"
    echo "   Dashboard → http://localhost:$REST_PORT/dashboard"
    echo ""
    echo "⏳ Waiting for Qdrant to be ready..."
    for i in {1..15}; do
        if curl -sf "http://localhost:$REST_PORT/healthz" > /dev/null 2>&1; then
            echo "✅ Qdrant is healthy!"
            break
        fi
        sleep 1
        echo "   ... attempt $i/15"
    done
}

cmd_stop() {
    if podman container exists "$CONTAINER_NAME" 2>/dev/null; then
        echo "🛑 Stopping $CONTAINER_NAME..."
        podman stop "$CONTAINER_NAME"
        echo "✅ Stopped."
    else
        echo "Container $CONTAINER_NAME does not exist."
    fi
}

cmd_restart() {
    cmd_stop
    cmd_start
}

cmd_status() {
    echo "=== Podman Container Status ==="
    podman ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "=== Qdrant Health ==="
    if curl -sf "http://localhost:$REST_PORT/healthz" > /dev/null 2>&1; then
        echo "✅ Qdrant REST API is healthy at http://localhost:$REST_PORT"
        curl -s "http://localhost:$REST_PORT/collections" | python3 -m json.tool 2>/dev/null || true
    else
        echo "❌ Qdrant is not responding on port $REST_PORT"
    fi
    echo ""
    echo "=== Volume Info ==="
    podman volume inspect "$VOLUME_NAME" 2>/dev/null || echo "Volume $VOLUME_NAME not found."
}

cmd_logs() {
    echo "📋 Logs for $CONTAINER_NAME (Ctrl+C to exit)..."
    podman logs -f "$CONTAINER_NAME"
}

cmd_remove() {
    cmd_stop || true
    if podman container exists "$CONTAINER_NAME" 2>/dev/null; then
        podman rm "$CONTAINER_NAME"
        echo "🗑  Container removed. Data volume '$VOLUME_NAME' is preserved."
    fi
}

# ── Entry point ───────────────────────────────────────────────────────────────
case "${1:-}" in
    start)    cmd_start   ;;
    stop)     cmd_stop    ;;
    restart)  cmd_restart ;;
    status)   cmd_status  ;;
    logs)     cmd_logs    ;;
    remove)   cmd_remove  ;;
    pull)     cmd_pull    ;;
    *)        usage        ;;
esac
