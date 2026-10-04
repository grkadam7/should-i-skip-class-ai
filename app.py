from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
import json
import os

app = Flask(__name__)


# =========================================================
# Google AI Studio / Gemma Configuration
# =========================================================

api_key = os.environ.get("GEMINI_API_KEY")

MODEL_NAME = "gemma-4-26b-a4b-it"

client = None

if api_key:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30000
        )
    )


# =========================================================
# System Prompt
# =========================================================

def build_system_prompt():
    return """You are SkipClass AI, a witty and brutally honest college attendance advisor.

Analyze whether a student should skip a class.

Return ONLY valid JSON in exactly this structure:

{
  "verdict": "SKIP" or "ATTEND" or "RISKY SKIP",
  "risk_score": 1-10,
  "short_reason": "one witty sentence",
  "detailed_analysis": "2 short sentences",
  "consequences": ["consequence 1", "consequence 2"],
  "tips": ["tip 1", "tip 2"]
}

Consider:

- Current attendance vs minimum required
- Classes remaining
- Proxy availability
- Teacher strictness
- Course credits
- Class timing
- Full-day schedule and gaps
- Upcoming tests/quizzes
- Subject difficulty
- Current grade situation

Rules:

- If attendance is below the minimum, strongly favor ATTEND.
- If there is an upcoming test/quiz, strongly increase risk.
- 4-credit core subjects matter more than low-credit electives.
- Strict teachers with no proxy increase risk.
- Very early classes have a "sleep tax".
- Large schedule gaps can make skipping more attractive.
- Reliable proxy availability can reduce risk.
- Be realistic and humorous.
- Do not invent information.

Keep the response concise.

OUTPUT JSON ONLY."""


# =========================================================
# Input Sanitization
# =========================================================

def sanitize_input(text):
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


# =========================================================
# User Prompt
# =========================================================

def build_user_prompt(data):

    safe_schedule = sanitize_input(
        data.get("day_schedule", "")
    )

    safe_test = sanitize_input(
        data.get("test_details", "Soon")
    )

    return f"""Student attendance situation:

ATTENDANCE
- Current: {data.get('attendance', 0)}%
- Minimum required: {data.get('min_attendance', 0)}%
- Classes remaining: {data.get('classes_remaining', 0)}

COURSE / TEACHER
- Credits: {sanitize_input(data.get('course_credits', ''))}
- Teacher strictness: {data.get('teacher_strictness', 5)}/10
- Proxy: {sanitize_input(data.get('proxy_status', ''))}

SCHEDULE
- Target class: {sanitize_input(data.get('class_time', ''))}
- Full day: {safe_schedule}

EVALUATION
- Upcoming test: {"Yes - " + safe_test if data.get('has_test') else "No"}

STUDENT
- Class type: {sanitize_input(data.get('class_type', ''))}
- Subject difficulty: {data.get('difficulty', 5)}/10
- Grade situation: {sanitize_input(data.get('grade_situation', ''))}

Question:
Should I skip this class?

Return the JSON verdict only."""


# =========================================================
# Main Page
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# AI Analysis
# =========================================================

@app.route("/api/analyze", methods=["POST"])
def analyze():

    # -----------------------------------------------------
    # Check API configuration
    # -----------------------------------------------------

    if not client:
        return jsonify({
            "error": "Gemma AI is not configured.",
            "details": "GEMINI_API_KEY is missing on the server."
        }), 503

    # -----------------------------------------------------
    # Read request data
    # -----------------------------------------------------

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No input data received."
        }), 400

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(data)

    try:

        # -------------------------------------------------
        # Send request to Gemma
        # -------------------------------------------------

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(

                # System instructions
                system_instruction=system_prompt,

                # More deterministic responses
                temperature=0.2,

                # Small JSON response
                max_output_tokens=300,

                # Force JSON output
                response_mime_type="application/json",

                # Disable thinking so Gemma does not
                # consume the output budget on reasoning
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0
                )
            )
        )

        # -------------------------------------------------
        # Safely retrieve response text
        # -------------------------------------------------

        ai_response = getattr(response, "text", None)

        if not ai_response:

            print("Gemma returned no text.")
            print("Gemma response:", response)

            return jsonify({
                "error": "Gemma returned an empty response.",
                "details": "Please try again."
            }), 502

        ai_response = ai_response.strip()

        print("Gemma response received successfully.")

        # -------------------------------------------------
        # Parse JSON
        # -------------------------------------------------

        try:

            cleaned = ai_response

            # Remove Markdown code fences if present
            if cleaned.startswith("```"):

                parts = cleaned.split("\n", 1)

                if len(parts) > 1:
                    cleaned = parts[1]

                cleaned = cleaned.rsplit("```", 1)[0]

            parsed = json.loads(cleaned.strip())

        except (json.JSONDecodeError, ValueError) as e:

            print("Gemma returned invalid JSON:")
            print(ai_response)
            print("JSON error:", e)

            return jsonify({
                "success": True,
                "analysis": {
                    "verdict": "RISKY SKIP",
                    "risk_score": 5,
                    "short_reason": "Gemma returned an unexpected response.",
                    "detailed_analysis": ai_response,
                    "consequences": [
                        "The AI response could not be formatted correctly."
                    ],
                    "tips": [
                        "Try submitting the request again."
                    ]
                }
            })

        # -------------------------------------------------
        # Validate required fields
        # -------------------------------------------------

        required_fields = [
            "verdict",
            "risk_score",
            "short_reason",
            "detailed_analysis",
            "consequences",
            "tips"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in parsed
        ]

        if missing_fields:

            print("Gemma JSON missing fields:")
            print(missing_fields)
            print("Gemma output:", parsed)

            return jsonify({
                "error": "Gemma returned incomplete analysis.",
                "details": "Please try again."
            }), 502

        # -------------------------------------------------
        # Successful response
        # -------------------------------------------------

        return jsonify({
            "success": True,
            "analysis": parsed
        })

    # =====================================================
    # API / Network / Timeout Error
    # =====================================================

    except Exception as e:

        print(f"Gemma API error: {e}")

        return jsonify({
            "error": "Gemma took too long to respond or encountered an error.",
            "details": "Please try again."
        }), 504


# =========================================================
# Health Check
# =========================================================

@app.route("/api/health", methods=["GET"])
def health():

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


# =========================================================
# Local Development
# =========================================================

if __name__ == "__main__":

    print("")
    print("===================================================")
    print("       ShouldISkipClass AI - v2.0")
    print("       Powered by Gemma")
    print("       Running at http://localhost:5000")
    print("===================================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )