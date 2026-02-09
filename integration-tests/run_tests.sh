#!/bin/bash
# Run M2 → M10 Integration Tests

set -e

echo "=================================="
echo "M2 → M10 Integration Test Runner"
echo "=================================="
echo ""

# Check if Memory Service is running
echo "1. Checking Memory Service..."
if curl -s http://localhost:8001/health > /dev/null; then
    echo "   ✅ Memory Service is running"
else
    echo "   ❌ Memory Service not running!"
    echo "   Starting Memory Service..."
    cd ../memory-service
    docker-compose up -d
    cd ../integration-tests
    sleep 5
    echo "   ✅ Memory Service started"
fi

echo ""
echo "2. Installing Python dependencies..."
pip install -q -r requirements.txt
echo "   ✅ Dependencies installed"

echo ""
echo "3. Generating test audio samples..."
python generate_test_audio.py
echo "   ✅ Test audio generated"

echo ""
echo "4. Running integration tests..."
echo ""
pytest test_m2_m10_integration.py -v -s --tb=short

echo ""
echo "=================================="
echo "Integration Tests Complete!"
echo "=================================="
