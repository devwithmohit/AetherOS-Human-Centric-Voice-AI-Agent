#!/bin/bash

# Verification script for OS Executor (Module 8)

echo "========================================"
echo "MODULE 8 VERIFICATION - OS Executor"
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
if [ -d "src" ] && [ -f "Cargo.toml" ]; then
    check_pass "Project structure exists"
else
    check_fail "Project structure missing"
fi

# 2. Check required files
echo
echo "2. Checking Required Files..."
REQUIRED_FILES=(
    "src/lib.rs"
    "src/executor.rs"
    "src/sandbox.rs"
    "src/whitelist.rs"
    "src/platform.rs"
    "src/main.rs"
    "README.md"
    "Cargo.toml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file"
    else
        check_fail "$file NOT FOUND"
    fi
done

# 3. Check compilation
echo
echo "3. Checking Compilation..."
if cargo check --quiet 2>/dev/null; then
    check_pass "Code compiles successfully"
else
    check_fail "Compilation failed"
fi

# 4. Run tests
echo
echo "4. Running Tests..."
if cargo test --quiet 2>/dev/null; then
    check_pass "All tests pass"
else
    check_fail "Some tests failed"
fi

# 5. Check library exports
echo
echo "5. Checking Library Exports..."
if cargo build --lib --quiet 2>/dev/null; then
    check_pass "Library builds successfully"
else
    check_fail "Library build failed"
fi

# 6. Check binary
echo
echo "6. Checking Binary..."
if cargo build --bin os-executor --quiet 2>/dev/null; then
    check_pass "Binary builds successfully"
else
    check_fail "Binary build failed"
fi

# 7. Test CLI commands
echo
echo "7. Testing CLI Commands..."
if cargo run --quiet -- info > /dev/null 2>&1; then
    check_pass "CLI 'info' command works"
else
    check_fail "CLI 'info' command failed"
fi

if cargo run --quiet -- list > /dev/null 2>&1; then
    check_pass "CLI 'list' command works"
else
    check_fail "CLI 'list' command failed"
fi

# 8. Test command execution
echo
echo "8. Testing Command Execution..."
if cargo run --quiet -- exec echo test 2>&1 | grep -q "test"; then
    check_pass "Command execution works (echo)"
else
    check_fail "Command execution failed"
fi

# 9. Test whitelist
echo
echo "9. Testing Whitelist..."
if cargo run --quiet -- list 2>&1 | grep -q "ls"; then
    check_pass "Whitelist contains safe commands"
else
    check_fail "Whitelist check failed"
fi

# Check dangerous commands are NOT whitelisted
if cargo run --quiet -- list 2>&1 | grep -qE 'rm|shutdown|reboot|dd'; then
    check_fail "Whitelist contains dangerous commands"
else
    check_pass "Dangerous commands properly excluded"
fi

# 10. Test shell injection protection
echo
echo "10. Testing Security..."
# This should fail (command not whitelisted) or succeed safely
if cargo run --quiet -- exec rm -rf / 2>&1 | grep -q "not whitelisted"; then
    check_pass "Dangerous command blocked (rm)"
else
    check_fail "Dangerous command not blocked"
fi

# 11. Check dependencies
echo
echo "11. Checking Dependencies..."
if grep -q "tokio" Cargo.toml && \
   grep -q "thiserror" Cargo.toml && \
   grep -q "serde" Cargo.toml && \
   grep -q "regex" Cargo.toml; then
    check_pass "All required dependencies present"
else
    check_fail "Missing dependencies"
fi

# 12. Check platform support
echo
echo "12. Checking Platform Support..."
if cargo run --quiet -- info 2>&1 | grep -qE 'linux|macos|windows'; then
    check_pass "Platform detection works"
else
    check_fail "Platform detection failed"
fi

# Summary
echo
echo "========================================"
echo "VERIFICATION SUMMARY"
echo "========================================"
echo
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    echo
    echo "Module 8 (OS Executor) is ready!"
    echo
    echo "Next steps:"
    echo "  1. Run: cargo test --release"
    echo "  2. Run: cargo run -- test"
    echo "  3. Integration testing with M6 (Safety Validator)"
    exit 0
else
    echo -e "${RED}⚠️  $FAILED CHECKS FAILED${NC}"
    echo
    echo "Please fix the issues above."
    exit 1
fi
