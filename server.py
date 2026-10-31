#!/usr/bin/env python3
"""
Gemini Browser Assistant - Secure Backend Server
A zero-dependency HTTP server that proxies Gemini AI requests safely.
Keeps your GEMINI_API_KEY secure and never exposes it to client or browser code.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Load environment variables from .env file without external dependencies
def load_env_file():
    env_paths = [
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env"
    ]
    for p in env_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'").strip('"')
                            if key and key not in os.environ:
                                os.environ[key] = val
                print(f"[Backend] Loaded environment variables from {p}")
                break
            except Exception as e:
                print(f"[Backend] Warning: could not parse {p}: {e}")

load_env_file()

PORT = int(os.environ.get("PORT", 5000))
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

class GeminiRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests with full CORS and Gemini API routing."""

    def _set_cors_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        # Allow requests from Chrome extensions and local origins
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        """Health check endpoint to test connection from the Chrome extension."""
        if self.path in ["/", "/api/health"]:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            has_valid_key = bool(api_key and api_key != "your_gemini_api_key_here")

            response_data = {
                "status": "healthy",
                "service": "Gemini Browser Assistant Backend",
                "model": GEMINI_MODEL,
                "hasApiKey": has_valid_key
            }
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def do_POST(self):
        """Handles analysis and chat prompts."""
        if self.path != "/api/gemini":
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))
            return

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            self._set_cors_headers(400)
            error_msg = (
                "GEMINI_API_KEY is not configured on the backend server. "
                "Please open 'backend/.env' and paste your Gemini API key from https://aistudio.google.com/app/apikey"
            )
            self.wfile.write(json.dumps({"success": False, "error": error_msg}).encode("utf-8"))
            return

        # Read and parse JSON request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(post_data)
        except Exception as err:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"success": False, "error": f"Invalid JSON payload: {err}"}).encode("utf-8"))
            return

        action = body.get("action", "summarize")
        fmt = body.get("format", "detailed")
        title = body.get("title", "")
        url = body.get("url", "")
        content = body.get("content", "")
        question = body.get("question", "")
        history = body.get("history", [])

        # Limit content length safely to prevent payload overflows (up to ~60,000 characters)
        if len(content) > 60000:
            content = content[:60000] + "\n\n[Content truncated by backend for optimal token processing...]"

        # Construct specific system instructions and prompts
        prompt = self._build_prompt(action, fmt, title, url, content, question, history)

        # Call Gemini REST API
        try:
            result_text = self._call_gemini_api(api_key, GEMINI_MODEL, prompt)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"success": True, "result": result_text}).encode("utf-8"))
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore")
            print(f"[Backend Error] Gemini API HTTP {http_err.code}: {error_body}")
            try:
                err_json = json.loads(error_body)
                msg = err_json.get("error", {}).get("message", error_body)
            except Exception:
                msg = error_body
            self._set_cors_headers(http_err.code)
            self.wfile.write(json.dumps({"success": False, "error": f"Gemini API Error: {msg}"}).encode("utf-8"))
        except Exception as err:
            print(f"[Backend Error] Internal server error: {err}")
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"success": False, "error": f"Server Error: {err}"}).encode("utf-8"))

    def _build_prompt(self, action, fmt, title, url, content, question, history):
        """Constructs prompt for Gemini based on user action."""
        context_header = f"Webpage Title: {title}\nWebpage URL: {url}\n\nWebpage Content:\n\"\"\"\n{content}\n\"\"\"\n\n"

        if action == "summarize":
            if fmt == "concise":
                task_instruction = (
                    "Provide a high-impact, concise TL;DR summary in 3-4 clear sentences. "
                    "Capture the core essence and conclusion of the page."
                )
            elif fmt == "executive":
                task_instruction = (
                    "Provide a formal Executive Summary formatted in clean Markdown:\n"
                    "- ## Executive Overview (1 paragraph)\n"
                    "- ## Strategic Takeaways (3-5 bullet points)\n"
                    "- ## Conclusion & Impact"
                )
            else: # detailed
                task_instruction = (
                    "Provide a comprehensive, well-structured summary of the webpage in clean Markdown:\n"
                    "- ## Overview & Context\n"
                    "- ## Core Arguments & Key Findings\n"
                    "- ## Supporting Evidence & Analysis\n"
                    "- ## Final Summary & Outlook"
                )
            return (
                f"You are an expert AI reading assistant. Your task is to analyze the following webpage and create a structured summary.\n\n"
                f"{context_header}"
                f"Instructions:\n{task_instruction}\n\n"
                "Ground your answer strictly in the text provided. Use Markdown formatting (headings, bold, lists)."
            )

        elif action == "key_points":
            if fmt == "actionable":
                task_instruction = (
                    "Extract actionable insights and recommendations from the webpage:\n"
                    "- Format as a bulleted list with bold action verbs\n"
                    "- Explain the 'Why' and 'How' for each point"
                )
            elif fmt == "data":
                task_instruction = (
                    "Extract all important facts, statistics, percentages, dates, and quantitative data:\n"
                    "- Group by thematic categories\n"
                    "- Highlight the significance of each data point"
                )
            else: # standard
                task_instruction = (
                    "Extract the top 5 to 8 most critical key takeaways:\n"
                    "- Use clear, punchy bullet points\n"
                    "- Bold the primary concept of each point\n"
                    "- Keep it focused on high-signal ideas"
                )
            return (
                f"You are an expert analyst. Extract the essential key points from this webpage.\n\n"
                f"{context_header}"
                f"Instructions:\n{task_instruction}\n\n"
                "Use clean Markdown formatting."
            )

        elif action == "study_notes":
            if fmt == "definitions":
                task_instruction = (
                    "Identify and define key terminology, domain-specific concepts, and important vocabulary found in this text:\n"
                    "- Format as a glossary (Term: Clear definition + contextual example from text)"
                )
            elif fmt == "quiz":
                task_instruction = (
                    "Create a self-test review quiz based on the webpage:\n"
                    "- 4 Multiple Choice or Short Answer questions to test comprehension\n"
                    "- Provide the correct answer and a brief explanation for each question in a spoiler or answer section"
                )
            else: # cornell
                task_instruction = (
                    "Generate Cornell-style study notes in Markdown:\n"
                    "- ## 📌 Core Topic & Learning Objectives\n"
                    "- ## 💡 Key Concepts & Explanations (cues on left, notes on right)\n"
                    "- ## 🔍 Detailed Notes & Methodologies\n"
                    "- ## 📝 Summary & Key Takeaways\n"
                    "- ## ❓ 3 Self-Review Questions"
                )
            return (
                f"You are an academic mentor and study guide generator.\n\n"
                f"{context_header}"
                f"Instructions:\n{task_instruction}\n\n"
                "Format beautifully in Markdown for easy studying."
            )

        elif action == "chat":
            history_text = ""
            if history:
                history_text = "Previous conversation:\n"
                for turn in history[-6:]: # keep last 3 turns
                    role = "User" if turn.get("role") == "user" else "Assistant"
                    history_text += f"{role}: {turn.get('content', '')}\n"
                history_text += "\n"

            return (
                f"You are Gemini Browser Assistant, an intelligent conversational AI answering questions about the currently open webpage.\n\n"
                f"{context_header}"
                f"{history_text}"
                f"User Question: \"{question}\"\n\n"
                "Instructions:\n"
                "- Answer the user's question directly and concisely.\n"
                "- Base your answer strictly on the webpage content provided above.\n"
                "- If the page does not contain information to answer the question, clearly state that the webpage does not mention it.\n"
                "- Use clean Markdown formatting with bullet points or bold text where appropriate."
            )

        else:
            return f"{context_header}\n\nPlease analyze the above page content and provide a summary."

    def _call_gemini_api(self, api_key, model, prompt_text):
        """Sends a POST request to Google's Generative Language REST API."""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "topP": 0.95,
                "maxOutputTokens": 2048
            }
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=45) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)

        # Extract generated response text
        candidates = res_json.get("candidates", [])
        if not candidates:
            return "No response generated by Gemini."

        content_obj = candidates[0].get("content", {})
        parts = content_obj.get("parts", [])
        if not parts:
            return "Empty response from Gemini."

        return parts[0].get("text", "")

    def log_message(self, format, *args):
        """Standardized console request logger."""
        print(f"[Backend] {self.address_string()} - {format % args}")

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, GeminiRequestHandler)
    print("=" * 60)
    print("  GEMINI BROWSER ASSISTANT - SECURE BACKEND")
    print("=" * 60)
    print(f" Server running at: http://127.0.0.1:{PORT}")
    print(f" Model:            {GEMINI_MODEL}")
    key_status = "SET" if os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_API_KEY") != "your_gemini_api_key_here" else "NOT SET (Configure backend/.env)"
    print(f" Gemini API Key:   {key_status}")
    print(" Ready to accept requests from the Chrome Extension.")
    print(" Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Backend] Server stopped cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    run_server()
