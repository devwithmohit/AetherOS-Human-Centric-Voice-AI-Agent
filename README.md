# AetherOS - Voice-First AI Assistant

![AetherOS](https://img.shields.io/badge/AetherOS-v1.0-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

**Complete voice-controlled AI assistant built with modular microservices architecture.**

## 🚀 Quick Start

### One-Command Startup

**Linux/WSL/Mac:**

```bash
./start.sh
```

**Windows:**

```cmd
start.bat
```

That's it! All 11 backend services + desktop client will start automatically.

## 📖 Full Documentation

- **[SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)** - Step-by-step interactive checklist
- **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)** - Complete setup guide with troubleshooting
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet
- **[DOCKERFILE_TEMPLATES.md](DOCKERFILE_TEMPLATES.md)** - Dockerfile templates for all services

## 🏗️ Architecture

AetherOS consists of 12 modules:

| Module                   | Port | Description                     |
| ------------------------ | ---- | ------------------------------- |
| **M1** Orchestrator      | 8001 | Request coordination & workflow |
| **M2** STT Service       | 8002 | Speech-to-Text (Whisper)        |
| **M3** TTS Service       | 8003 | Text-to-Speech (Piper)          |
| **M4** LLM Service       | 8004 | Local/Cloud LLM inference       |
| **M5** Tool Registry     | 8005 | Function definitions            |
| **M6** Intent Classifier | 8006 | Intent detection                |
| **M7** Function Executor | 8007 | Tool execution engine           |
| **M8** Context Manager   | 8008 | Conversation context            |
| **M9** Prompt Builder    | 8009 | Dynamic prompt construction     |
| **M10** Memory Service   | 8010 | Persistent memory & learning    |
| **M11** API Gateway      | 8000 | Main entry point + WebSocket    |
| **M12** Desktop Client   | 3000 | Electron UI (voice + text)      |

## 📁 Project Structure

```
Jarvis-voice-agent/
├── docker-compose.yml          # All services orchestration
├── .env.example                # Environment configuration
├── start.sh / start.bat        # One-command startup
├── stop.sh / stop.bat          # Shutdown scripts
├── health-check.sh/.bat        # Verify all services
├── test-voice-command.sh/.bat  # Quick test
├── STARTUP_GUIDE.md            # Complete setup guide
│
├── orchestrator/               # M1: Central coordinator
├── stt-service/                # M2: Whisper speech-to-text
├── tts-service/                # M3: Piper text-to-speech
├── llm-service/                # M4: LLM inference
├── tool-registry/              # M5: Function definitions
├── intent-classifier/          # M6: Intent detection
├── function-executor/          # M7: Tool execution
├── context-manager/            # M8: Context tracking
├── prompt-builder/             # M9: Prompt engineering
├── memory-service/             # M10: Persistent storage
├── api-gateway/                # M11: API + WebSocket
└── desktop-client/             # M12: Electron UI
```

## ⚡ Prerequisites

- **Docker Desktop** or Docker Engine
- **Bun** (for frontend)
- **Ollama** (optional, for local LLM)
- 8GB RAM minimum (16GB recommended)

## 🎯 Quick Commands

```bash
# Start everything
./start.sh              # Linux/Mac
start.bat               # Windows

# Check health
./health-check.sh       # Linux/Mac
health-check.bat        # Windows

# Test voice command
./test-voice-command.sh # Linux/Mac
test-voice-command.bat  # Windows

# View logs
docker-compose logs -f [service-name]

# Stop everything
./stop.sh               # Linux/Mac
stop.bat                # Windows
```

## 🖥️ Desktop Client Features

- **Voice Input**: Press `Ctrl + \`` to toggle listening
- **Text Input**: Switch to text mode for typing
- **Real-time Waveform**: Visual feedback during recording
- **Conversation History**: Markdown-rendered messages
- **Memory Viewer**: See what Aether remembers (3 tabs)
- **Settings Panel**: Privacy, models, voice selection
- **Tool Status**: Live function execution feedback

## 🌐 Service URLs

- **API Gateway**: http://localhost:8000
- **Desktop Client**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs (when running)
- **Health Check**: http://localhost:8000/health

## 🔧 Configuration

Edit `.env` file:

```bash
# LLM Mode
LLM_MODE=local              # local, cloud, or hybrid
DEFAULT_MODEL=llama3.2:3b

# Cloud API Keys (optional)
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key

# Speech Models
WHISPER_MODEL=base          # tiny, base, small, medium, large
PIPER_VOICE=en_US-lessac-medium
```

## 📊 Health Check Output

```
✓ M11 API Gateway (port 8000) - HEALTHY
✓ M1  Orchestrator (port 8001) - HEALTHY
✓ M2  STT Service (port 8002) - HEALTHY
✓ M3  TTS Service (port 8003) - HEALTHY
✓ M4  LLM Service (port 8004) - HEALTHY
✓ M5  Tool Registry (port 8005) - HEALTHY
✓ M6  Intent Classifier (port 8006) - HEALTHY
✓ M7  Function Executor (port 8007) - HEALTHY
✓ M8  Context Manager (port 8008) - HEALTHY
✓ M9  Prompt Builder (port 8009) - HEALTHY
✓ M10 Memory Service (port 8010) - HEALTHY
✓ Desktop Client (port 3000) - RUNNING

All services are healthy! ✓
```

## 🐛 Troubleshooting

**Services not starting?**

```bash
# View logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart [service-name]

# Rebuild
docker-compose build --no-cache
```

**Port conflicts?**

```bash
# Find process using port
lsof -i :8000           # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

**Ollama not connecting?**

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Pull model
ollama pull llama3.2:3b
```

See [STARTUP_GUIDE.md](STARTUP_GUIDE.md) for detailed troubleshooting.

## 🎓 Development

### Module Structure

Each module follows this pattern:

```
module-name/
├── Dockerfile          # Container definition
├── package.json        # Dependencies
├── src/
│   ├── index.ts        # Entry point
│   ├── routes/         # API endpoints
│   ├── services/       # Business logic
│   └── utils/          # Helpers
└── README.md           # Module documentation
```

### Adding a New Tool

1. Define in Tool Registry (M5)
2. Implement in Function Executor (M7)
3. Test with test-voice-command script

### Testing

```bash
# Test specific service
curl http://localhost:8000/health

# Test voice flow
./test-voice-command.sh

# Run unit tests (per module)
cd [module-name]
npm test
```

## 🔐 Security

- Context isolation in Electron
- No eval() or Function() constructors
- IPC whitelist pattern
- Content Security Policy
- Environment variable isolation
- Docker network segmentation

## 📈 Performance

- Parallel service startup
- Health check dependencies
- Efficient Docker networking
- Optimized model sizes
- Resource limits per container

## 🛣️ Roadmap

- [ ] Wake word detection (Porcupine)
- [ ] Voice Activity Detection
- [ ] Multi-user support
- [ ] Cloud sync (optional)
- [ ] Mobile companion app
- [ ] Plugin system
- [ ] Metrics dashboard
- [ ] CI/CD pipeline

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## 🆘 Support

- **Documentation**: [STARTUP_GUIDE.md](STARTUP_GUIDE.md)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## 🎉 Built With

- **Electron** - Desktop framework
- **React** - UI library
- **Docker** - Containerization
- **Node.js/Bun** - Runtime
- **TypeScript** - Type safety
- **Whisper** - Speech recognition
- **Piper** - Voice synthesis
- **Ollama** - Local LLM
- **Zustand** - State management
- **TailwindCSS** - Styling

---

**Made with ❤️ for voice-first AI interaction**

[⭐ Star this repo](https://github.com/your-repo) | [📖 Docs](STARTUP_GUIDE.md) | [🐛 Report Bug](https://github.com/your-repo/issues)
