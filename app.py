from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "gemma3:4b"


def build_system_prompt():
    """Build the system prompt for Gemma to act as an attendance advisor."""
    return """You are "SkipClass AI", a witty, realistic, and brutally honest college attendance advisor. Your mission is to give students realistic advice on whether to bunk/skip a class based on their schedule and circumstances.

You MUST analyze the student's situation and respond in this EXACT JSON format (no markdown, no code block wrappers, no text outside JSON):
{
    "verdict": "SKIP" or "ATTEND" or "RISKY SKIP",
    "risk_score": <number from 1-10>,
    "short_reason": "<witty/funny one-liner summary>",
    "detailed_analysis": "<2-3 sentences explaining the trade-offs>",
    "consequences": ["<consequence 1>", "<consequence 2>"],
    "tips": ["<practical tip 1>", "<practical tip 2>"]
}

Decision Logic & Factors:
1. PROXY AVAILABILITY: If they have a reliable friend to mark proxy attendance, risk score drops significantly!
2. DAY SCHEDULE / GAPS: If this is their ONLY class of the day, skipping lets them stay home all day (high skip motivation). If there is a massive 3-hour gap after/before, skipping saves useless waiting time on campus.
3. CLASS TIMING: 8:00 AM early morning classes have a built-in sleep tax!
4. COURSE CREDITS: 4-credit core subjects are way more important than 1-2 credit electives/labs.
5. SAFE SKIP ("SKIP"): High attendance buffer (>5%), no upcoming tests, proxy available OR huge schedule gap.
6. MUST ATTEND ("ATTEND"): Attendance below minimum threshold, OR upcoming test/quiz, OR 4-credit subject with strict teacher and NO proxy.

Be humorous, relatable, and use college slangs naturally (bunk, proxy, sleep tax, mass bunk, attendance short, etc.).
OUTPUT VALID JSON ONLY."""


def sanitize_input(text):
    """Basic sanitization to prevent prompt injection and limit length."""
    if not isinstance(text, str):
        return str(text)
    forbidden = ["ignore previous", "system prompt", "instruction", "forget", "bypass", "jailbreak"]
    text_lower = text.lower()
    for word in forbidden:
        if word in text_lower:
            return "[REDACTED - INVALID INPUT]"
    return text[:1000]  # Cap length to prevent context flooding


def build_user_prompt(data):
    """Build the user prompt from form data with sanitized inputs."""
    safe_schedule = sanitize_input(data.get('day_schedule', ''))
    safe_test = sanitize_input(data.get('test_details', 'Soon'))
    
    return f"""Here is my detailed class & day schedule context:

📊 ATTENDANCE STATUS:
- Current attendance: {data.get('attendance', 0)}%
- Minimum required: {data.get('min_attendance', 0)}%
- Classes remaining this semester: {data.get('classes_remaining', 0)}

🎓 COURSE & TEACHER INTEL:
- Course Credits: {sanitize_input(data.get('course_credits', ''))} Credits (1-2 = Low weight, 3-4 = Core Heavy)
- Teacher Strictness: {data.get('teacher_strictness', 5)}/10
- Proxy Friend Available?: {sanitize_input(data.get('proxy_status', ''))}

⏰ SCHEDULE & TIMING CONTEXT:
- Class Time: {sanitize_input(data.get('class_time', ''))}
- Day Schedule Context: {safe_schedule}

📝 UPCOMING EVALUATIONS:
- Test/Quiz coming up: {"Yes - " + safe_test if data.get('has_test') else "No"}

📚 CLASS TYPE & PERFORMANCE:
- Class type: {sanitize_input(data.get('class_type', ''))}
- Subject difficulty (for me): {data.get('difficulty', 5)}/10
- My current grade situation: {sanitize_input(data.get('grade_situation', ''))}

Should I skip this class? Analyze all the factors and give me your verdict."""


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze whether the student should skip class using Gemma."""
    data = request.json

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(data)

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1024
                }
            },
            timeout=120
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Ollama is not responding. Make sure Ollama is running with Gemma model.",
                "details": f"Status code: {response.status_code}"
            }), 503

        result = response.json()
        ai_response = result.get('message', {}).get('content', '')

        # Parse JSON
        try:
            cleaned = ai_response.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('\n', 1)[1]
                cleaned = cleaned.rsplit('```', 1)[0]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            return jsonify({
                "success": True,
                "analysis": parsed
            })
        except (json.JSONDecodeError, ValueError):
            return jsonify({
                "success": True,
                "analysis": {
                    "verdict": "RISKY SKIP",
                    "risk_score": 5,
                    "short_reason": "AI couldn't format properly, but here's the take:",
                    "detailed_analysis": ai_response,
                    "consequences": ["Check the detailed analysis above"],
                    "tips": ["Try asking again for a cleaner response"]
                }
            })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Cannot connect to Ollama. Please make sure Ollama is running.",
            "help": "Run 'ollama serve' in a terminal, then 'ollama pull gemma3:4b'"
        }), 503
    except Exception as e:
        return jsonify({
            "error": f"Unexpected error: {str(e)}"
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Check if Ollama is running and Gemma model is available."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            gemma_available = any('gemma' in name.lower() for name in model_names)
            return jsonify({
                "ollama_running": True,
                "gemma_available": gemma_available,
                "models": model_names
            })
        return jsonify({"ollama_running": False, "gemma_available": False}), 503
    except Exception:
        return jsonify({"ollama_running": False, "gemma_available": False}), 503


if __name__ == '__main__':
    print("")
    print("  ===================================================")
    print("       ShouldISkipClass AI - v2.0                    ")
    print("       Powered by Gemma (Open Source)                ")
    print("       Running at http://localhost:5000              ")
    print("  ===================================================")
    print("")
    app.run(debug=True, port=5000)
