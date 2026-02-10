# Integration Tests - Phase 2

**Testing: M2 (STT) → M4 (Intent) → M5 (Reasoning) → M6 (Safety)**

Complete end-to-end integration testing for the Agent Brain pipeline.

## Test Coverage

### Pipeline Validation

- ✅ M4 (Intent Classifier) → M5 (Reasoning Engine) integration
- ✅ M5 (Reasoning Engine) → M6 (Safety Validator) integration
- ✅ Complete M4 → M5 → M6 pipeline

### Test Scenarios (20+)

1. **Safe Single-Step Tasks** (5 scenarios)

   - Weather queries
   - Time queries
   - Web searches
   - Calculator operations
   - Help requests

2. **Safe Multi-Step Tasks** (5 scenarios)

   - Open app + search
   - Set timer + reminder
   - Play music + adjust volume
   - Get weather + set reminder
   - Search + open app

3. **Malicious Inputs (Security Testing)** (8 scenarios)

   - SQL injection (DROP TABLE)
   - Command injection (rm -rf)
   - Path traversal (../../etc/passwd)
   - XSS injection (<script>)
   - URL injection (localhost)
   - Buffer overflow (huge strings)
   - Blocked tools (SYSTEM_SHUTDOWN)
   - Rate limiting bypass

4. **High-Risk Actions** (3 scenarios)
   - Send email (requires confirmation)
   - Close application (requires confirmation)
   - System control (requires confirmation)

## Running Tests

```bash
# Install dependencies
cd integration-tests-phase2
pip install -r requirements.txt

# Run all tests
pytest test_integration.py -v

# Run specific test category
pytest test_integration.py::TestSafeTasks -v
pytest test_integration.py::TestMaliciousInputs -v
pytest test_integration.py::TestHighRiskActions -v

# Run with detailed output
pytest test_integration.py -v -s
```

## Expected Results

- **Safe tasks**: Should pass all stages (APPROVED or REQUIRES_CONFIRMATION)
- **Malicious inputs**: Should be BLOCKED by M6
- **High-risk actions**: Should require user CONFIRMATION
- **Rate limiting**: Should block after threshold

## Architecture

```
User Query (Text from M2/STT)
        ↓
M4: Intent Classifier
    - Classify intent (78 types)
    - Extract entities
    - Confidence scoring
        ↓
M5: Reasoning Engine
    - ReAct planning
    - Tool selection
    - Multi-step decomposition
        ↓
M6: Safety Validator
    - Risk scoring
    - Parameter sanitization
    - Whitelist/blacklist check
    - PII detection
        ↓
Result: APPROVED / BLOCKED / REQUIRES_CONFIRMATION
```

## Integration Points Tested

1. **M4 → M5**: Intent + entities → Execution plan
2. **M5 → M6**: Tool calls + parameters → Validation result
3. **Pipeline**: Query → Intent → Plan → Validation → Safe execution
