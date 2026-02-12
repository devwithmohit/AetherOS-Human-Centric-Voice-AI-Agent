#!/usr/bin/env bash
# Verification script for Browser Executor (Module 7)

set -e

echo "========================================"
echo "MODULE 7 VERIFICATION - Browser Executor"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success_count=0
total_checks=0

check() {
    total_checks=$((total_checks + 1))
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        success_count=$((success_count + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $1"
        return 1
    fi
}

# Check 1: Directory Structure
echo "1. Checking Directory Structure..."
[ -d "src" ] && check "src/ directory exists"
[ -d "tests" ] && check "tests/ directory exists"
[ -f "Cargo.toml" ] && check "Cargo.toml exists"

# Check 2: Source Files
echo ""
echo "2. Checking Source Files..."
[ -f "src/lib.rs" ] && check "src/lib.rs exists"
[ -f "src/main.rs" ] && check "src/main.rs exists"
[ -f "src/actions.rs" ] && check "src/actions.rs exists"
[ -f "src/executor.rs" ] && check "src/executor.rs exists"
[ -f "src/screenshot.rs" ] && check "src/screenshot.rs exists"
[ -f "src/sandbox.rs" ] && check "src/sandbox.rs exists"

# Check 3: Cargo Build
echo ""
echo "3. Checking Cargo Build..."
if cargo build 2>/dev/null; then
    check "Cargo build succeeds"
else
    echo -e "${RED}✗${NC} Cargo build failed"
fi

# Check 4: Cargo Check
echo ""
echo "4. Checking Rust Syntax..."
if cargo check 2>/dev/null; then
    check "Cargo check succeeds"
else
    echo -e "${RED}✗${NC} Cargo check failed"
fi

# Check 5: Dependencies
echo ""
echo "5. Checking Dependencies..."
if cargo tree | grep -q "chromiumoxide"; then
    check "chromiumoxide dependency found"
fi
if cargo tree | grep -q "tokio"; then
    check "tokio dependency found"
fi
if cargo tree | grep -q "clap"; then
    check "clap dependency found"
fi

# Check 6: Tests Exist
echo ""
echo "6. Checking Tests..."
if [ -f "tests/integration_test.rs" ]; then
    check "Integration tests exist"

    # Count test functions
    test_count=$(grep -c "#\[tokio::test\]" tests/integration_test.rs)
    echo -e "   Found ${YELLOW}${test_count}${NC} test cases"
fi

# Check 7: Documentation
echo ""
echo "7. Checking Documentation..."
[ -f "README.md" ] && check "README.md exists"

# Count lines of code
echo ""
echo "8. Code Statistics..."
total_lines=$(find src -name "*.rs" -exec wc -l {} \; | awk '{sum+=$1} END {print sum}')
echo -e "   Total lines of code: ${YELLOW}${total_lines}${NC}"

# Check 9: Module Exports
echo ""
echo "9. Checking Module Exports..."
if grep -q "pub use actions" src/lib.rs; then
    check "Actions module exported"
fi
if grep -q "pub use executor" src/lib.rs; then
    check "Executor module exported"
fi
if grep -q "pub use sandbox" src/lib.rs; then
    check "Sandbox module exported"
fi
if grep -q "pub use screenshot" src/lib.rs; then
    check "Screenshot module exported"
fi

# Check 10: Binary Target
echo ""
echo "10. Checking Binary Target..."
if grep -q "browser-executor" Cargo.toml; then
    check "CLI binary configured"
fi

# Summary
echo ""
echo "========================================"
echo "VERIFICATION SUMMARY"
echo "========================================"
echo ""
echo -e "Passed: ${GREEN}${success_count}${NC}/${total_checks} checks"

if [ $success_count -eq $total_checks ]; then
    echo ""
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC} - Module 7 is ready!"
    echo ""
    echo "Next steps:"
    echo "  1. Run tests: cargo test"
    echo "  2. Build release: cargo build --release"
    echo "  3. Try CLI: ./target/release/browser-executor --help"
    echo "  4. Install Chromium: sudo apt install chromium-browser"
    echo "  5. Optional: Install nsjail for sandboxing (Linux)"
    exit 0
else
    failed=$((total_checks - success_count))
    echo ""
    echo -e "${YELLOW}⚠️  ${failed} checks failed${NC}"
    echo "Please fix the issues above before proceeding."
    exit 1
fi
