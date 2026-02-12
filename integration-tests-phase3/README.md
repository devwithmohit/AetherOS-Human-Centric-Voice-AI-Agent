# Phase 3 Integration Tests

Comprehensive integration tests for the Phase 3 Execution Layer, validating the complete pipeline from planning (M5) through validation (M6) to execution (M7/M8/M9).

## Overview

This test suite verifies:

- **M6 → M9**: Safety Validator → Search Executor integration
- **M6 → M7**: Safety Validator → Browser Executor integration
- **M6 → M8**: Safety Validator → OS Executor integration
- **M5 → M6 → M7/M8/M9**: Complete end-to-end pipeline

## Test Structure

```
integration-tests-phase3/
├── test_m6_to_m9.py          # M6 → Search Executor (6 tests)
├── test_m6_to_m8.py          # M6 → OS Executor (8 tests)
├── test_m6_to_m7.py          # M6 → Browser Executor (10 tests)
├── test_full_pipeline.py     # Full pipeline (8 tests)
├── run_all_tests.py          # Master test runner
├── README.md                 # This file
└── test_report.json          # Generated test report
```

## Quick Start

### Run All Tests

```bash
cd integration-tests-phase3
python run_all_tests.py
```

### Run Individual Test Suites

```bash
# M6 → M9 (Search) integration
python test_m6_to_m9.py

# M6 → M8 (OS) integration
python test_m6_to_m8.py

# M6 → M7 (Browser) integration
python test_m6_to_m7.py

# Full pipeline tests
python test_full_pipeline.py
```

## Test Suites

### 1. M6 → M9 Integration (test_m6_to_m9.py)

Tests the Safety Validator → Search Executor integration.

**Tests (6 total)**:

1. ✓ Approved query execution
2. ✓ Blocked query rejection
3. ✓ Prompt injection detection
4. ✓ Query modification (parameter limits)
5. ✓ Validation logging
6. ✓ Error handling for invalid parameters

**Key Validations**:

- Malicious queries blocked ("hack", "illegal")
- Prompt injection attempts detected ("ignore previous")
- Max results capped at 50
- All validations logged

**Example**:

```python
# Approved query
query = "Python asyncio best practices"
validation = await validator.validate_search_query(query, max_results=5)
# → approved: True, executes via M9

# Blocked query
query = "how to hack systems"
validation = await validator.validate_search_query(query, max_results=10)
# → approved: False, reason: "Query contains blocked content: hack"
```

---

### 2. M6 → M8 Integration (test_m6_to_m8.py)

Tests the Safety Validator → OS Executor integration.

**Tests (8 total)**:

1. ✓ Approved command execution
2. ✓ Dangerous command blocked (rm, sudo, shutdown)
3. ✓ Shell injection blocked (`;`, `&`, `|`)
4. ✓ Path traversal blocked (/etc, /root)
5. ✓ Safe file operations allowed
6. ✓ Command whitelisting
7. ✓ Validation logging
8. ✓ Timeout handling

**Key Validations**:

- Dangerous commands blocked (rm, sudo, shutdown, kill, etc.)
- Shell metacharacters detected (`;`, `&`, `|`, `>`, `<`, `` ` ``, `$`)
- Sensitive paths blocked (/etc/, /root/)
- Defense in depth (both M6 and M8 validate)

**Example**:

```python
# Safe command
command = "echo"
args = ["Hello from integration test"]
validation = await validator.validate_os_command(command, args)
# → approved: True, executes via M8

# Dangerous command
command = "rm"
args = ["-rf", "/"]
validation = await validator.validate_os_command(command, args)
# → approved: False, reason: "Command 'rm' is not allowed"

# Shell injection
command = "echo"
args = ["test; rm -rf /"]
validation = await validator.validate_os_command(command, args)
# → approved: False, reason: "Argument contains shell metacharacter: ;"
```

---

### 3. M6 → M7 Integration (test_m6_to_m7.py)

Tests the Safety Validator → Browser Executor integration.

**Tests (10 total)**:

1. ✓ Approved navigation
2. ✓ Blocked domain rejection
3. ✓ Non-HTTPS URLs blocked
4. ✓ Localhost HTTP allowed
5. ✓ Sensitive input blocked
6. ✓ Safe input allowed
7. ✓ Malicious selector blocked
8. ✓ Screenshot action approved
9. ✓ Invalid action blocked
10. ✓ Validation logging

**Key Validations**:

- Malicious domains blocked
- Only HTTPS allowed (except localhost)
- Sensitive data patterns blocked ("password", "credit card", "ssn")
- XSS attempts in selectors blocked (`<script>`, `eval`)
- Only allowed actions: navigate, click, type, screenshot, get_content, wait, evaluate

**Example**:

```python
# Safe navigation
action = "navigate"
url = "https://example.com"
validation = await validator.validate_browser_action(action, url=url)
# → approved: True, executes via M7

# Blocked domain
action = "navigate"
url = "https://malicious.com/page"
validation = await validator.validate_browser_action(action, url=url)
# → approved: False, reason: "Domain blocked for safety: malicious.com"

# Sensitive input
action = "type"
value = "Enter your password: secret123"
validation = await validator.validate_browser_action(action, value=value)
# → approved: False, reason: "Input contains sensitive pattern: password"
```

---

### 4. Full Pipeline Integration (test_full_pipeline.py)

Tests the complete M5 → M6 → M7/M8/M9 pipeline.

**Tests (8 total)**:

1. ✓ Search pipeline (M5 → M6 → M9)
2. ✓ Browser pipeline (M5 → M6 → M7)
3. ✓ OS command pipeline (M5 → M6 → M8)
4. ✓ Blocked plan doesn't execute
5. ✓ Dangerous OS commands blocked
6. ✓ Error handling in pipeline
7. ✓ Results flow back through pipeline
8. ✓ Logging and audit trail

**Pipeline Flow**:

```
User Task
    ↓
M5 Planner (creates execution plan)
    ↓
M6 Safety Validator (validates plan)
    ↓
    ├─→ M9 Search Executor (if search)
    ├─→ M7 Browser Executor (if browser)
    └─→ M8 OS Executor (if OS command)
    ↓
Result returned to user
```

**Example**:

```python
# Complete search pipeline
task = "search for Python best practices"

# Step 1: M5 creates plan
plan = await planner.create_plan(task)
# → executor_type: "search", steps: [{action: "search", query: "Python best practices"}]

# Step 2: M6 validates plan
validation = await validator.validate_plan(plan)
# → approved: True

# Step 3: Execute via appropriate executor (M9)
result = await executor_manager.execute_plan(validation["plan"])
# → success: True, results: [...]
```

---

## Test Coverage

### Security Features Tested

| Feature                     | M6→M9 | M6→M8 | M6→M7 | Pipeline |
| --------------------------- | ----- | ----- | ----- | -------- |
| Malicious content detection | ✓     | ✓     | ✓     | ✓        |
| Prompt injection protection | ✓     | -     | -     | ✓        |
| Shell injection protection  | -     | ✓     | -     | ✓        |
| XSS protection              | -     | -     | ✓     | -        |
| Command whitelisting        | -     | ✓     | -     | ✓        |
| Domain whitelisting         | -     | -     | ✓     | -        |
| HTTPS enforcement           | -     | -     | ✓     | -        |
| Path traversal protection   | -     | ✓     | -     | ✓        |
| Sensitive data detection    | ✓     | -     | ✓     | -        |
| Resource limits             | ✓     | ✓     | -     | -        |
| Audit logging               | ✓     | ✓     | ✓     | ✓        |

### Error Handling Tested

| Scenario           | Tested | Status                |
| ------------------ | ------ | --------------------- |
| Network failures   | ✓      | Graceful degradation  |
| Timeout handling   | ✓      | Proper error messages |
| Invalid parameters | ✓      | Validation errors     |
| Malicious input    | ✓      | Blocked with reason   |
| Empty/null data    | ✓      | Handled gracefully    |
| Execution failures | ✓      | Error returned        |

---

## Test Results

### Expected Output

```
================================================================================
PHASE 3 INTEGRATION TEST SUITE
================================================================================
Start time: 2026-02-12 05:45:00
================================================================================

================================================================================
Running: test_m6_to_m9.py
================================================================================
M6 → M9 INTEGRATION TESTS
...
Passed: 6 ✓
Failed: 0 ✗

================================================================================
Running: test_m6_to_m8.py
================================================================================
M6 → M8 INTEGRATION TESTS
...
Passed: 8 ✓
Failed: 0 ✗

================================================================================
Running: test_m6_to_m7.py
================================================================================
M6 → M7 INTEGRATION TESTS
...
Passed: 10 ✓
Failed: 0 ✗

================================================================================
Running: test_full_pipeline.py
================================================================================
FULL PIPELINE INTEGRATION TESTS
...
Passed: 8 ✓
Failed: 0 ✗

================================================================================
OVERALL TOTALS
================================================================================
Test Suites: 4
Total Tests: 32
Passed:      32 ✓
Failed:      0 ✗
Errors:      0 ⚠
Pass Rate:   100.0%
================================================================================

✓ ALL TESTS PASSED!
```

---

## Mock Components

Since M5 (Planner) and M6 (Safety Validator) are not yet implemented, the tests use mock components that simulate their behavior.

### MockSafetyValidator (M6)

**Features**:

- Query validation (search)
- Command validation (OS)
- Action validation (browser)
- Blocking rules for dangerous content
- Validation logging

**Blocked Content**:

- **Search**: "hack", "illegal", "malicious"
- **OS**: rm, sudo, shutdown, kill, chmod, etc.
- **Browser**: malicious.com, non-HTTPS (except localhost)

### MockPlanner (M5)

**Features**:

- Task parsing
- Executor type detection
- Step generation
- Priority assignment

**Detection**:

- Search tasks: "search", "find", "look up"
- Browser tasks: "browse", "open", "navigate", "screenshot"
- OS tasks: "run", "execute", "command", "list files"

### MockExecutorManager

**Features**:

- Routes plans to appropriate executor
- Simulates M7/M8/M9 execution
- Returns mock results

---

## Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Phase 3 Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          cd search-executor
          pip install -r requirements.txt

      - name: Run integration tests
        run: |
          cd integration-tests-phase3
          python run_all_tests.py

      - name: Upload test report
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: integration-tests-phase3/test_report.json
```

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'search_executor'`

```bash
# Solution: Install search-executor dependencies
cd ../search-executor
pip install -r requirements.txt
```

**Issue**: `cargo: command not found` (for M8 tests)

```bash
# Solution: Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Issue**: Tests timeout

```bash
# Solution: Increase timeout in test files
# Edit test files and increase timeout values:
timeout=60  # Increase from 30 to 60 seconds
```

**Issue**: M8 tests fail (OS Executor)

```bash
# Solution: Build os-executor first
cd ../os-executor
cargo build --release
cd ../integration-tests-phase3
python test_m6_to_m8.py
```

---

## Test Maintenance

### Adding New Tests

1. Create new test file: `test_new_feature.py`
2. Implement test class with `run_all_tests()` method
3. Add to `run_all_tests.py` test list
4. Update this README with test documentation

### Updating Mock Components

As M5 and M6 are implemented:

1. Replace mock classes with real implementations
2. Update import statements
3. Adjust test expectations if needed
4. Run full test suite to verify

---

## Performance Benchmarks

| Test Suite    | Tests  | Avg Duration                 |
| ------------- | ------ | ---------------------------- |
| M6 → M9       | 6      | ~0.5s                        |
| M6 → M8       | 8      | ~12s (includes cargo builds) |
| M6 → M7       | 10     | ~0.3s                        |
| Full Pipeline | 8      | ~0.4s                        |
| **Total**     | **32** | **~13s**                     |

---

## Future Enhancements

1. **Load Testing**: Test concurrent executions
2. **Stress Testing**: Test resource limits under load
3. **Chaos Engineering**: Test failure scenarios
4. **Performance Profiling**: Identify bottlenecks
5. **Integration with Real M5/M6**: Replace mocks with actual implementations
6. **Browser Automation**: Add actual browser tests with Playwright/Selenium
7. **Network Simulation**: Test with simulated network conditions
8. **Security Fuzzing**: Automated vulnerability testing

---

## Contributing

To contribute new tests:

1. Follow existing test patterns
2. Include docstrings explaining test purpose
3. Add assertions for expected behavior
4. Update this README with new test documentation
5. Ensure all tests pass before submitting PR

---

## License

Part of the Jarvis Voice Agent project.

---

## Contact

For questions or issues, see the main project README.

---

**Last Updated**: February 12, 2026
**Test Suite Version**: 1.0.0
**Test Coverage**: 32 tests across 4 suites
