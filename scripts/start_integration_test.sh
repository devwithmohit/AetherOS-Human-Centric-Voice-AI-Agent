#!/bin/bash
# Start Integration Point 5 Testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INTEGRATION_DIR="$PROJECT_ROOT/integration"

echo "🚀 Jarvis Integration Point 5 - Full Flow Testing"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

# Check if API Gateway is running
echo "📡 Checking API Gateway..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ API Gateway not running. Starting..."
    cd "$PROJECT_ROOT/api-gateway"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    GATEWAY_PID=$!
    echo "✅ API Gateway started (PID: $GATEWAY_PID)"
    sleep 5
else
    echo "✅ API Gateway is running"
fi

# Check Redis
echo "📦 Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not running. Please start Redis first:"
    echo "   redis-server"
    exit 1
else
    echo "✅ Redis is running"
fi

# Install integration test dependencies
echo "📚 Installing integration test dependencies..."
cd "$INTEGRATION_DIR"
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Create logs directory
mkdir -p "$INTEGRATION_DIR/logs"

# Parse arguments
SCENARIO="${1:-youtube}"
USE_REAL_SERVICES="${2:-}"

echo ""
echo "🎯 Running Integration Test"
echo "   Scenario: $SCENARIO"
echo "   Mode: $([ -n "$USE_REAL_SERVICES" ] && echo 'Real Services' || echo 'Mock Services')"
echo ""

# Run integration test
if [ -n "$USE_REAL_SERVICES" ]; then
    python integration_test.py --scenario "$SCENARIO" --use-real-services
else
    python integration_test.py --scenario "$SCENARIO"
fi

TEST_EXIT_CODE=$?

echo ""
echo "=================================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Integration test completed successfully!"
else
    echo "❌ Integration test failed (exit code: $TEST_EXIT_CODE)"
fi
echo "=================================================="

# Cleanup
if [ -n "$GATEWAY_PID" ]; then
    echo "🧹 Cleaning up... (killing API Gateway PID: $GATEWAY_PID)"
    kill $GATEWAY_PID 2>/dev/null || true
fi

exit $TEST_EXIT_CODE
