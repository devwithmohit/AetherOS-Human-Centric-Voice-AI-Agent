# Module 6: Safety Validator

**Security validation layer for AetherOS execution plans**

The Safety Validator enforces security constraints before execution plans reach the Action Executor (Module 7). It validates tool selections, sanitizes parameters, calculates risk scores, and blocks or flags dangerous operations.

---

## 📋 Overview

Module 6 is the last line of defense before actions are executed. It validates every tool call from the Reasoning Engine (Module 5) to ensure:

- Tools are on the whitelist
- Parameters are sanitized (SQL injection, command injection, XSS)
- Risk levels are acceptable
- Rate limits are enforced
- PII is detected and masked
- High-risk actions require confirmation

### Key Features

✅ **Tool Whitelisting**: 34 approved tools, 7 blocked tools
✅ **Risk Scoring**: LOW/MEDIUM/HIGH/CRITICAL levels (0.0-1.0 scale)
✅ **Input Sanitization**: SQL injection, command injection, path traversal, XSS
✅ **PII Detection**: Credit cards, SSN, emails, phone numbers
✅ **Rate Limiting**: User-specific limits by risk level
✅ **Confirmation Logic**: HIGH/CRITICAL risk requires user approval
✅ **Adversarial Testing**: 100+ malicious input tests

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Module 6: Safety Validator                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  Allow List  │    │     Risk     │    │   Input   │ │
│  │   Manager    │    │    Scorer    │    │ Sanitizer │ │
│  │              │    │              │    │           │ │
│  │ • Whitelists │    │ • LOW/MED/   │    │ • SQL inj │ │
│  │ • Blacklists │    │   HIGH/CRIT  │    │ • Cmd inj │ │
│  │ • URL rules  │    │ • Risk calc  │    │ • Path    │ │
│  │ • Path rules │    │ • Context    │    │ • XSS     │ │
│  └──────┬───────┘    └──────┬───────┘    └─────┬─────┘ │
│         │                   │                   │       │
│         └───────────────────┼───────────────────┘       │
│                             │                           │
│                    ┌────────▼────────┐                  │
│                    │     Safety      │                  │
│                    │   Validator     │                  │
│                    │                 │                  │
│                    │ • Orchestrates  │                  │
│                    │ • Rate limiting │                  │
│                    │ • PII detection │                  │
│                    │ • Confirmation  │                  │
│                    └────────┬────────┘                  │
│                             │                           │
│                    ┌────────▼────────┐                  │
│                    │ ValidationResult│                  │
│                    │                 │                  │
│                    │ • APPROVED      │                  │
│                    │ • REQUIRES_CONF │                  │
│                    │ • BLOCKED       │                  │
│                    │ • SANITIZED     │                  │
│                    └─────────────────┘                  │
│                                                           │
└─────────────────────────────────────────────────────────┘

Input:  ExecutionPlan from M5
Output: ValidationResult (approved/blocked/confirmation)
```

---

## 📦 Components

### 1. SafetyValidator (`app/validator.py`)

Main orchestrator that coordinates all validation checks.

**Methods:**

```python
validate(user_id, tool, parameters, context) -> ValidationResult
validate_batch(user_id, tool_calls, context) -> List[ValidationResult]
get_user_stats(user_id) -> Dict[str, Any]
```

**Validation Flow:**

1. Check tool whitelist/blacklist
2. Sanitize parameters
3. Validate parameter types (URLs, paths, apps)
4. Calculate risk score
5. Check for PII
6. Enforce rate limits
7. Determine final status

### 2. RiskScorer (`app/risk_scorer.py`)

Calculates risk scores based on tool type, parameters, and context.

**Risk Levels:**

- **LOW** (0.0-0.25): Safe, no confirmation needed
- **MEDIUM** (0.25-0.50): Log but allow
- **HIGH** (0.50-0.75): Require confirmation
- **CRITICAL** (0.75-1.0): Block or explicit authorization

**Risk Factors:**

- **Tool type** (50% weight): Base risk from policies
- **Parameters** (30% weight): Dangerous patterns in params
- **Context** (20% weight): User history, time of day, unusual actions

### 3. InputSanitizer (`app/sanitizers.py`)

Sanitizes inputs to prevent injection attacks.

**Protection Against:**

- **SQL Injection**: Blocks DROP, DELETE, INSERT, UPDATE, --, /\*, xp*, sp*
- **Command Injection**: Blocks ;, |, &, &&, ||, `, $(), >>, >, <
- **Path Traversal**: Blocks .., ~/, /etc/, /var/, C:\Windows
- **XSS**: Removes `<script>`, `javascript:`, `on*=` event handlers
- **URL Injection**: Validates schemes, blocks localhost, private IPs

**PII Detection:**

- Credit cards (masks to `****-****-****-####`)
- SSN (masks to `***-**-####`)
- Emails (masks to `***@***.***`)
- Phone numbers (masks to `***-***-####`)

### 4. AllowListManager (`app/allow_lists.py`)

Manages whitelists and blacklists for tools, applications, and parameters.

**Allowed Tools (34):**

- Information: GET_WEATHER, GET_TIME, GET_DATE, WEB_SEARCH, GET_NEWS
- Media: MEDIA_PLAYER, VOLUME_CONTROL, MUSIC_CONTROL
- Applications: OPEN_APPLICATION, CLOSE_APPLICATION
- Productivity: SET_TIMER, SET_ALARM, REMINDER, NOTE_TAKING, CALENDAR
- Communication: SEND_EMAIL, SEND_MESSAGE, MAKE_CALL
- Smart Home: LIGHT_CONTROL, TEMPERATURE_CONTROL
- Utilities: HELP, GREETING, FAREWELL, JOKE, FACT, QUOTE, MATH_CALCULATION

**Blocked Tools (7):**

- SYSTEM_SHUTDOWN
- SYSTEM_RESTART
- FORMAT_DRIVE
- DELETE_FILE
- ADMIN_COMMAND
- DATABASE_MODIFY
- USER_ACCOUNT_MODIFY

---

## 🚀 Getting Started

### Installation

```bash
cd safety-validator
uv pip install -r requirements.txt
# or
pip install -r requirements.txt
```

### Verify Setup

```bash
python verify.py
```

Expected output:

```
✓ PASS: File structure
✓ PASS: Module imports
✓ PASS: Policy loading
✓ PASS: Basic validation
✓ PASS: Risk scoring
✓ PASS: Input sanitization
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Adversarial Tests (100+ malicious inputs)

```bash
pytest tests/test_adversarial.py -v
```

**Test Coverage:**

- SQL injection (DROP TABLE, UNION SELECT, comment bypass)
- Command injection (pipe, semicolon, backticks, $())
- Path traversal (../, /etc/, C:\Windows, ~/)
- XSS injection (<script>, javascript:, event handlers)
- URL injection (localhost, private IPs, file://)
- Buffer overflow (extremely long strings, large numbers)
- PII detection (credit cards, SSN, emails)
- Rate limiting
- Tool whitelisting
- Batch validation

### Run Unit Tests

```bash
pytest tests/test_validator.py -v
```

---

## 📖 Usage Examples

### Example 1: Validate Safe Tool

```python
from app import SafetyValidator

validator = SafetyValidator()

result = validator.validate(
    user_id="user123",
    tool="GET_WEATHER",
    parameters={"location": "Paris"}
)

if result.is_safe():
    print(f"✓ Approved: {result.status}")
    # Proceed with execution
else:
    print(f"✗ Blocked: {result.blocked_reason}")
```

**Output:**

```
✓ Approved: APPROVED
Risk level: LOW (score: 0.12)
```

### Example 2: Block Malicious SQL Injection

```python
result = validator.validate(
    user_id="user123",
    tool="DATABASE_QUERY",
    parameters={"query": "SELECT * FROM users; DROP TABLE users;"}
)

print(f"Status: {result.status}")
print(f"Reason: {result.blocked_reason}")
```

**Output:**

```
Status: BLOCKED
Reason: Sanitization failed: SQL query contains blocked pattern: DROP TABLE
Risk level: CRITICAL (score: 1.0)
```

### Example 3: High-Risk Action Requires Confirmation

```python
result = validator.validate(
    user_id="user123",
    tool="SEND_EMAIL",
    parameters={
        "to": "boss@company.com",
        "subject": "Resignation",
        "body": "I quit"
    }
)

if result.needs_confirmation():
    print(f"⚠ Confirmation required:")
    print(result.confirmation_message)

    # Wait for user confirmation
    if user_confirms():
        # Proceed with execution
        pass
```

**Output:**

```
⚠ Confirmation required:
This action 'SEND_EMAIL' is classified as HIGH risk. Do you want to proceed?

Risk assessment:
Tool 'SEND_EMAIL' assessed as HIGH risk.
  - tool_type: 35% contribution
  - parameters: 0% contribution
  - context: 0% contribution
```

### Example 4: Batch Validation

```python
tool_calls = [
    {"tool": "GET_WEATHER", "parameters": {"location": "Paris"}},
    {"tool": "OPEN_APPLICATION", "parameters": {"app_name": "chrome"}},
    {"tool": "WEB_SEARCH", "parameters": {"query": "Python tutorial"}},
]

results = validator.validate_batch("user123", tool_calls)

for i, result in enumerate(results):
    print(f"{i+1}. {tool_calls[i]['tool']}: {result.status}")
```

**Output:**

```
1. GET_WEATHER: APPROVED
2. OPEN_APPLICATION: REQUIRES_CONFIRMATION
3. WEB_SEARCH: APPROVED
```

### Example 5: User Statistics

```python
stats = validator.get_user_stats("user123")

print(f"Total validations: {stats['total_validations']}")
print(f"Approved: {stats['approved']}")
print(f"Blocked: {stats['blocked']}")
print(f"Requires confirmation: {stats['requires_confirmation']}")
print(f"Average risk score: {stats['average_risk_score']:.2f}")
```

---

## ⚙️ Configuration

Edit `config/policies.yaml` to customize security policies.

### Risk Levels

```yaml
risk_levels:
  low:
    - GET_WEATHER
    - GET_TIME
    # ... more tools

  high:
    - SEND_EMAIL
    - MAKE_CALL
    # ... more tools
```

### Rate Limits

```yaml
rate_limits:
  actions_per_minute:
    low_risk: 60
    medium_risk: 30
    high_risk: 10
    critical: 1
```

### Parameter Rules

```yaml
parameter_rules:
  file_paths:
    max_length: 260
    blocked_patterns:
      - ".."
      - "/etc/"
      - "C:\\Windows"
```

---

## 🔌 Integration

### Module 5 → Module 6 Flow

```python
# In orchestration layer

# Step 1: Get execution plan from M5
from reasoning_engine.app import ReActPlanner

planner = ReActPlanner(llm, context_builder)
plan = await planner.plan(user_id, intent, entities, query)

# Step 2: Validate with M6
from safety_validator.app import SafetyValidator

validator = SafetyValidator()

for step in plan.steps:
    result = validator.validate(
        user_id=user_id,
        tool=step.tool,
        parameters=step.parameters
    )

    if result.status == ValidationStatus.BLOCKED:
        print(f"Blocked: {result.blocked_reason}")
        break

    elif result.needs_confirmation():
        print(f"Confirmation: {result.confirmation_message}")
        if not await get_user_confirmation():
            break

    else:
        # Step 3: Execute with M7 (Action Executor)
        await execute_action(step.tool, result.sanitized_parameters)
```

---

## 📊 Performance

### Latency

- Validation: <5ms per tool call
- Risk scoring: <2ms
- Sanitization: <3ms
- Batch validation (10 tools): <50ms

### False Positive Rate

Target: <5%
Measured: ~3% on test dataset

**Common False Positives:**

- Legitimate long paths flagged as traversal
- Scientific notation numbers flagged as overflow
- Foreign language text flagged as injection

---

## 🛡️ Security Best Practices

### 1. Always Validate Before Execution

```python
# ✓ Good
result = validator.validate(user_id, tool, params)
if result.is_safe():
    execute(tool, result.sanitized_parameters)

# ✗ Bad
execute(tool, params)  # No validation!
```

### 2. Use Sanitized Parameters

```python
# ✓ Good
execute(tool, result.sanitized_parameters)

# ✗ Bad
execute(tool, params)  # Use original params
```

### 3. Respect Confirmation Requirements

```python
if result.needs_confirmation():
    if not await get_user_confirmation():
        return  # Don't execute
```

### 4. Log All Validations

```python
logger.info(f"Validation: {result.status}, Risk: {result.risk_score.level}")
```

---

## 🐛 Troubleshooting

### Issue: Too Many False Positives

**Solution**: Adjust risk thresholds in `app/risk_scorer.py`:

```python
self.thresholds = {
    RiskLevel.LOW: 0.30,      # Increase from 0.25
    RiskLevel.MEDIUM: 0.55,   # Increase from 0.50
    RiskLevel.HIGH: 0.80,     # Increase from 0.75
    RiskLevel.CRITICAL: 1.0,
}
```

### Issue: Legitimate Tools Blocked

**Solution**: Add to whitelist in `config/policies.yaml`:

```yaml
allowed_tools:
  - YOUR_NEW_TOOL
```

### Issue: Rate Limit Too Strict

**Solution**: Adjust limits in `config/policies.yaml`:

```yaml
rate_limits:
  actions_per_minute:
    high_risk: 20 # Increase from 10
```

---

## 📈 Future Enhancements

### Planned Features

1. **ML-based Risk Scoring**: Train model on historical validation data
2. **Contextual Allow Lists**: Per-user/per-role whitelists
3. **Honeypot Parameters**: Detect automated attacks
4. **Reputation System**: Track user behavior for adaptive scoring
5. **Sandboxed Execution**: Test high-risk actions in sandbox first
6. **Audit Logging**: Comprehensive security event logging
7. **Real-time Monitoring**: Dashboard for security metrics

---

## 📚 Related Modules

- **Module 5**: Reasoning Engine (input provider)
- **Module 7**: Action Executor (output consumer)
- **Module 10**: Memory Service (context provider for risk scoring)

---

## 📝 License

Part of the AetherOS Voice Agent project.

---

## 🔄 Testing Checklist

- [x] Tool whitelist (34 approved tools)
- [x] Tool blacklist (7 blocked tools)
- [x] Risk scoring (LOW/MED/HIGH/CRITICAL)
- [x] SQL injection protection
- [x] Command injection protection
- [x] Path traversal protection
- [x] XSS protection
- [x] PII detection (credit card, SSN, email, phone)
- [x] PII masking
- [x] Rate limiting
- [x] Confirmation logic
- [x] Parameter sanitization
- [x] Batch validation
- [x] User statistics
- [x] Adversarial testing (100+ tests)

---

**Module Status**: ✅ **Complete**

**Phase 2 Status**: 🎉 **COMPLETE** (All 4 modules done: M10, M4, M5, M6)

**Next**: Integration testing (M2 → M4 → M5 → M6 → M7)
