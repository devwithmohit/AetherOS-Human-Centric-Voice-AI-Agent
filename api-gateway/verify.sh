#!/bin/bash

# Verification script for API Gateway (Module 11)

echo "========================================"
echo "MODULE 11 VERIFICATION - API Gateway"
echo "========================================"
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

# 1. Check directory structure
echo "1. Checking Directory Structure..."
if [ -d "app" ] && [ -f "pyproject.toml" ]; then
    check_pass "Project structure exists"
else
    check_fail "Project structure missing"
fi

# 2. Check required files
echo
echo "2. Checking Required Files..."
REQUIRED_FILES=(
    "app/__init__.py"
    "app/main.py"
    "app/config.py"
    "app/auth.py"
    "app/rate_limiter.py"
    "app/websocket.py"
    "app/grpc_clients/__init__.py"
    "app/routers/__init__.py"
    "app/routers/health_router.py"
    "app/routers/voice_router.py"
    "app/routers/agent_router.py"
    "app/routers/executor_router.py"
    "app/routers/memory_router.py"
    "README.md"
    ".env.example"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file"
    else
        check_fail "$file NOT FOUND"
    fi
done

# 3. Check Python syntax
echo
echo "3. Checking Python Syntax..."
python_error=0
for file in app/*.py app/**/*.py; do
    if [ -f "$file" ]; then
        if python -m py_compile "$file" 2>/dev/null; then
            : # Syntax OK
        else
            check_fail "Syntax error in $file"
            python_error=1
        fi
    fi
done

if [ $python_error -eq 0 ]; then
    check_pass "All Python files have valid syntax"
fi

# 4. Check dependencies
echo
echo "4. Checking Dependencies..."
if command -v uv >/dev/null 2>&1; then
    check_pass "uv package manager installed"
else
    check_fail "uv not installed (recommended)"
fi

if command -v redis-cli >/dev/null 2>&1; then
    check_pass "Redis CLI available"
else
    check_fail "Redis CLI not found"
fi

# 5. Check Redis connection
echo
echo "5. Checking Redis Connection..."
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    check_pass "Redis is running and accessible"
else
    check_fail "Redis connection failed (required for rate limiting)"
fi

# 6. Check environment file
echo
echo "6. Checking Environment Configuration..."
if [ -f ".env" ]; then
    check_pass ".env file exists"

    # Check for critical variables
    if grep -q "JWT_SECRET_KEY" .env; then
        check_pass "JWT_SECRET_KEY configured"
    else
        check_fail "JWT_SECRET_KEY not configured"
    fi

    if grep -q "REDIS_URL" .env; then
        check_pass "REDIS_URL configured"
    else
        check_fail "REDIS_URL not configured"
    fi
else
    check_fail ".env file not found (copy from .env.example)"
fi

# 7. Check imports
echo
echo "7. Checking Module Imports..."
if python -c "from app.main import app" 2>/dev/null; then
    check_pass "Main application imports successfully"
else
    check_fail "Main application import failed"
fi

if python -c "from app.auth import AuthMiddleware" 2>/dev/null; then
    check_pass "Authentication module imports successfully"
else
    check_fail "Authentication module import failed"
fi

if python -c "from app.rate_limiter import RateLimiter" 2>/dev/null; then
    check_pass "Rate limiter module imports successfully"
else
    check_fail "Rate limiter module import failed"
fi

# 8. Check router definitions
echo
echo "8. Checking API Routers..."
routers=(
    "health_router"
    "voice_router"
    "agent_router"
    "executor_router"
    "memory_router"
)

for router in "${routers[@]}"; do
    if grep -q "router = APIRouter()" "app/routers/${router}.py" 2>/dev/null; then
        check_pass "${router} defined"
    else
        check_fail "${router} missing or malformed"
    fi
done

# 9. Check endpoint definitions
echo
echo "9. Checking API Endpoints..."
if grep -q "@app.get(\"/\")" app/main.py 2>/dev/null; then
    check_pass "Root endpoint defined"
else
    check_fail "Root endpoint missing"
fi

if grep -q "@router.get(\"/health\")" app/routers/health_router.py 2>/dev/null; then
    check_pass "Health endpoint defined"
else
    check_fail "Health endpoint missing"
fi

if grep -q "@router.websocket" app/websocket.py 2>/dev/null; then
    check_pass "WebSocket endpoint defined"
else
    check_fail "WebSocket endpoint missing"
fi

# 10. Check middleware configuration
echo
echo "10. Checking Middleware..."
if grep -q "CORSMiddleware" app/main.py 2>/dev/null; then
    check_pass "CORS middleware configured"
else
    check_fail "CORS middleware missing"
fi

if grep -q "GZipMiddleware" app/main.py 2>/dev/null; then
    check_pass "GZip middleware configured"
else
    check_fail "GZip middleware missing"
fi

if grep -q "AuthMiddleware" app/main.py 2>/dev/null; then
    check_pass "Auth middleware configured"
else
    check_fail "Auth middleware missing"
fi

# 11. Check gRPC client configuration
echo
echo "11. Checking gRPC Configuration..."
if grep -q "GRPCClientManager" app/grpc_clients/__init__.py 2>/dev/null; then
    check_pass "gRPC client manager defined"
else
    check_fail "gRPC client manager missing"
fi

service_clients=("stt" "tts" "intent" "planner" "safety" "browser" "os" "search" "memory")
grpc_file="app/grpc_clients/__init__.py"

for service in "${service_clients[@]}"; do
    if grep -q "\"${service}\"" "$grpc_file" 2>/dev/null; then
        : # Service configured
    else
        check_fail "gRPC client for ${service} missing"
    fi
done

if grep -q "\"stt\"" "$grpc_file" 2>/dev/null; then
    check_pass "All gRPC service clients configured"
fi

# 12. Check Prometheus metrics
echo
echo "12. Checking Monitoring..."
if grep -q "prometheus_client" app/main.py 2>/dev/null; then
    check_pass "Prometheus metrics configured"
else
    check_fail "Prometheus metrics missing"
fi

if grep -q "REQUEST_COUNT" app/main.py 2>/dev/null; then
    check_pass "Request counter metric defined"
else
    check_fail "Request metrics missing"
fi

# Summary
echo
echo "========================================"
echo "VERIFICATION SUMMARY"
echo "========================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo
    echo "Next steps:"
    echo "1. Start Redis: redis-server"
    echo "2. Configure .env file"
    echo "3. Run: uvicorn app.main:app --reload"
    echo "4. Test: curl http://localhost:8000/health"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
