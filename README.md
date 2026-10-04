# 🎓 ShouldISkipClass.ai

**An open-source AI-powered college attendance advisor that runs 100% locally.**

Built with **Gemma** (Google's open-weight model) via **Ollama** — your academic data never leaves your machine.

![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python)
![Gemma](https://img.shields.io/badge/AI-Gemma%203-orange?logo=google)
![Ollama](https://img.shields.io/badge/Inference-Ollama-black)
![License](https://img.shields.io/badge/License-MIT-green)

## 🤔 What Does It Do?

Tell it your attendance percentage, teacher strictness, upcoming tests, and more — and it uses **Gemma** (running locally via Ollama) to analyze whether you can safely skip your next class.

**Features:**
- 📊 Attendance tracking with visual bar
- 👨‍🏫 Teacher strictness rating (1-10)
- 📝 Upcoming test/assignment awareness
- 🤝 Proxy availability consideration
- ⏰ Full day timetable context (gap & packed day analysis)
- 🧪 Lecture vs Lab vs Tutorial differentiation
- 📈 Subject difficulty & grade situation analysis
- 🎯 Risk score (1-10) with detailed reasoning
- 💡 Witty, relatable advice from the AI

## 🔒 Why Open Source AI?

| Closed API | Our Approach |
|---|---|
| Your grades sent to corporate servers | **Everything stays on YOUR laptop** |
| $20/month API costs | **100% free to run** |
| Can't customize for your college | **Tune the prompts for your rules** |
| Needs internet | **Works offline after model download** |
| Model changes without notice | **You control which model runs** |

**Your attendance data, grades, and academic struggles are personal.** No student wants that data on someone else's server. With Gemma + Ollama, the AI runs entirely on your machine — no cloud, no tracking, no data collection.

## 🚀 Quick Start

### Prerequisites
1. **Python 3.7+** installed
2. **Ollama** installed — [Download here](https://ollama.com/download)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/grkadam7/should-i-skip-class-ai.git
cd should-i-skip-class-ai

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Pull the Gemma model (one-time, ~3GB download)
ollama pull gemma3:4b

# 4. Start Ollama (if not already running)
ollama serve

# 5. Run the app (in a new terminal)
python app.py
```

Open **http://localhost:5000** in your browser and start analyzing! 🎉

## 🛠️ Tech Stack

- **AI Model:** [Gemma 3 4B](https://ai.google.dev/gemma) — Google's open-weight model
- **Local Inference:** [Ollama](https://ollama.com/) — run LLMs locally
- **Backend:** Python + Flask
- **Frontend:** HTML + CSS + Vanilla JS
- **Data Storage:** None — we don't store anything!
- **Testing:** Pytest (automated prompt and sanitization coverage)
- **Security:** Built-in prompt injection sanitization against malicious inputs

## 📸 Screenshots

*Coming soon!*

## 🏗️ How It Works

1. You fill in your class details (attendance, teacher info, tests, etc.)
2. Flask sends the data to Gemma via Ollama's local REST API
3. Gemma analyzes everything and returns structured advice
4. The frontend displays the verdict with a risk score and reasoning

```
[Your Browser] → [Flask Server] → [Ollama (Local)] → [Gemma Model]
     ↑                                                      |
     └──────────────── Response with Verdict ←──────────────┘
```

**Everything happens on localhost. Zero external API calls.**

## 📄 License

MIT License — do whatever you want with it!

---

*Built for Hacktoberfest 2026 — "Build for a Friend" Weekend Challenge* 🎃
