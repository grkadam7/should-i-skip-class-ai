from flask import Flask, render_template, request, jsonify
from google import genai
import json
import os

app = Flask(__name__)

# Google AI Studio API key
api_key = os.environ.get("GEMINI_API_KEY")

# Gemma model available through the Gemini API
MODEL_NAME = "gemma-4-26b-a4b-it"

# Initialize Gemini client
client = genai.Client(api_key=api_key) if api_key else None


def build_system_prompt():
    """Build the system prompt for Gemma to act as an attendance advisor."""
    return """You are "SkipClass AI", a witty, realistic, and brutally honest college attendance advisor.

Your mission is to give students realistic advice on whether to bunk/skip a class based on their schedule and circumstances.

You MUST analyze the student's situation and respond in this EXACT JSON format:

{
    "verdict": "SKIP" or "ATTEND" or "RISKY SKIP",
    "risk_score": <number from 1-10>,
    "short_reason": "<witty/funny one-liner summary>",
    "detailed_analysis": "<2-3 sentences explaining the trade-offs>",
    "consequences": ["<consequence 1>", "<consequence 2>"],
    "tips": ["<practical tip 1>", "<practical tip 2>"]
}

Decision Logic & Factors:

1. PROXY AVAILABILITY:
If they have a reliable friend to mark proxy attendance, risk score drops significantly.

2. DAY SCHEDULE / GAPS:
If this is their ONLY class of the day, skipping lets them stay home all day.
If there is a massive 3-hour gap before or after the class, skipping may save useless waiting time on campus.

3. CLASS TIMING:
8:00 AM early morning classes have a built-in sleep tax.

4. COURSE CREDITS:
4-credit core subjects are more important than 1-2 credit electives/labs.

5. SAFE SKIP:
High attendance buffer (>5%), no upcoming tests, proxy available OR huge schedule gap.

6. MUST ATTEND:
Attendance below minimum threshold, OR upcoming test/quiz, OR 4-credit subject with strict teacher and NO proxy.

Be humorous, relatable, and use college slang naturally:
bunk, proxy, sleep tax, mass bunk, attendance short, etc.

OUTPUT VALID JSON ONLY."""


def sanitize_input(text):
    """Basic sanitization to prevent prompt injection and limit length."""
    if not isinstance(text, str):
        return str(text)

    forbidden = [
        "ignore previous",
        "system prompt",
        "instruction",
        "forget",
        "bypass",
        "jailbreak"
    ]

    text_lower = text.lower()

    for word in forbidden:
        if word in text_lower:
            return "[REDACTED - INVALID INPUT]"

    return text[:1000]


def build_user_prompt(data):
    """Build the user prompt from form data."""

    safe_schedule = sanitize_input(
        data.get("day_schedule", "")
    )

    safe_test = sanitize_input(
        data.get("test_details", "Soon")
    )

    return f"""Here is my detailed class & day schedule context:

📊 ATTENDANCE STATUS:
- Current attendance: {data.get('attendance', 0)}%
- Minimum required: {data.get('min_attendance', 0)}%
- Classes remaining this semester: {data.get('classes_remaining', 0)}

🎓 COURSE & TEACHER INTEL:
- Course Credits: {sanitize_input(data.get('course_credits', ''))} Credits
  (1-2 = Low weight, 3-4 = Core Heavy)
- Teacher Strictness: {data.get('teacher_strictness', 5)}/10
- Proxy Friend Available?: {sanitize_input(data.get('proxy_status', ''))}

⏰ SCHEDULE & TIMING CONTEXT:
- Class Time: {sanitize_input(data.get('class_time', ''))}
- Day Schedule Context: {safe_schedule}

📝 UPCOMING EVALUATIONS:
- Test/Quiz coming up:
  {"Yes - " + safe_test if data.get('has_test') else "No"}

📚 CLASS TYPE & PERFORMANCE:
- Class type: {sanitize_input(data.get('class_type', ''))}
- Subject difficulty (for me): {data.get('difficulty', 5)}/10
- My current grade situation: {sanitize_input(data.get('grade_situation', ''))}

Should I skip this class?

Analyze ALL the factors and give me your verdict."""


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Analyze whether the student should skip class using Gemma."""

    if not client:
        return jsonify({
            "error": "Gemma API is not configured.",
            "details": "GEMINI_API_KEY is missing."
        }), 503

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No input data received."
        }), 400

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(data)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.7,
                "response_mime_type": "application/json"
            }
        )

        ai_response = response.text.strip()

        # Parse Gemma's JSON response
        try:
            cleaned = ai_response

            # Remove markdown wrapper if model still adds one
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]

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
                    "short_reason": "AI couldn't format the response properly.",
                    "detailed_analysis": ai_response,
                    "consequences": [
                        "The AI response could not be parsed."
                    ],
                    "tips": [
                        "Try submitting the request again."
                    ]
                }
            })

    except Exception as e:
        print(f"Gemma API error: {e}")

        return jsonify({
            "error": "Unable to get a response from Gemma.",
            "details": str(e)
        }), 503


@app.route("/api/health", methods=["GET"])
def health():
    """Check whether the Gemma API is configured."""

    if client:
        return jsonify({
            "api_configured": True,
            "gemma_available": True,
            "model": MODEL_NAME
        })

    return jsonify({
        "api_configured": False,
        "gemma_available": False,
        "model": MODEL_NAME
    }), 503


if __name__ == "__main__":
    print("")
    print("  ===================================================")
    print("       ShouldISkipClass AI - v2.0")
    print("       Powered by Gemma")
    print("       Running at http://localhost:5000")
    print("  ===================================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )