# Integration Point 5: Full Flow Testing

**Purpose:** End-to-end integration testing of all 11 modules working together to accomplish real user tasks.

## Architecture

```
User Voice Input
       ↓
   M1: Wake Word Detection (Porcupine)
       ↓
   M2: Speech-to-Text (Whisper)
       ↓
   M4: Intent Recognition (NLP)
       ↓
   M10: Memory Recall (Context retrieval)
       ↓
   M5: Action Planning (Multi-step execution plan)
       ↓
   M6: Safety Validation (Risk assessment)
       ↓
   M7/M8/M9: Executors (Browser/OS/Search)
       ↓
   M3: Text-to-Speech (Response)
       ↓
   M10: Memory Storage (Episodic memory)
```

## Test Scenarios

### 1. Play YouTube Video

**User:** "Hey Aether, play a YouTube video about Rust"

- **M1:** Detects "Hey Aether" wake word
- **M2:** Transcribes → "play a youtube video about rust"
- **M4:** Recognizes intent = `PLAY_MEDIA`
- **M10:** Recalls user preferences (English, 10min+ videos)
- **M5:** Generates multi-step plan:
  1. `web_search("rust programming youtube")`
  2. `browser_open(<best_result>)`
  3. `browser_click("play button")`
- **M6:** Validates plan (all steps marked LOW risk)
- **M9:** Executes search → Returns ranked results
- **M5:** Selects best result based on preferences
- **M7:** Opens browser and clicks play
- **M3:** Speaks → "Playing Rust programming tutorial"
- **M10:** Stores episodic memory

### 2. Weather and Email

**User:** "Check the weather and send the report to John"

- Multi-step plan with search + OS command execution
- Demonstrates chained actions

### 3. Code Assistant

**User:** "Find Python async examples and open the best one in VS Code"

- Search → filter → OS command execution
- Demonstrates preference-based selection

## Components

### Core Integration Files

- `integration_test.py` - Main test orchestrator
- `scenarios/` - Individual test scenarios
- `mock_services/` - Mock implementations for testing
- `config/` - Integration configuration

### Mock Services

For development/testing without real services:

- `mock_m1_wakeword.py` - Simulates wake word detection
- `mock_m2_stt.py` - Returns predefined transcriptions
- `mock_m3_tts.py` - Logs TTS requests
- `mock_m4_intent.py` - Pattern-based intent recognition
- `mock_m5_planner.py` - Rule-based planning
- `mock_m6_safety.py` - Always returns "safe" for testing
- `mock_m7_browser.py` - Simulates browser actions
- `mock_m8_os.py` - Safe OS command simulation
- `mock_m9_search.py` - Returns fake search results
- `mock_m10_memory.py` - In-memory storage

## Running Integration Tests

### With Mock Services (Testing)

```bash
cd integration
python integration_test.py --scenario youtube
```

### With Real Services (Production)

```bash
# Start all services first
./scripts/start_all_services.sh

# Run integration test
python integration_test.py --scenario youtube --use-real-services
```

### All Scenarios

```bash
python integration_test.py --all-scenarios
```

## Prerequisites

1. **API Gateway Running:** Port 8000
2. **Redis Running:** Port 6379
3. **All gRPC Services:** Ports 50051-50059
4. **Python Environment:** 3.10+

## Success Criteria

✅ All modules communicate successfully
✅ Data flows correctly between services
✅ Error handling works at each step
✅ Safety validation blocks dangerous commands
✅ Memory is persisted and recalled
✅ Response time < 5 seconds per request

## Monitoring

- Logs: `integration/logs/`
- Metrics: Prometheus at `http://localhost:8000/metrics`
- Traces: Each test includes request correlation ID

## Known Limitations

1. Wake word detection requires microphone access
2. Browser automation requires display server (X11/Wayland)
3. Search executor requires internet connection
4. TTS playback requires audio output

## Next Steps

1. ✅ Module 11 (API Gateway) - Complete
2. ⏳ Integration Point 5 - In Progress
3. ⏳ Performance Testing - Pending
4. ⏳ Production Deployment - Pending
