/**
 * Gemini Browser Assistant - Node.js Express Backend Alternative
 * Provides an identical secure proxy to server.py for Node.js environments.
 */

const express = require("express");
const cors = require("cors");
const dotenv = require("dotenv");
const path = require("path");

dotenv.config({ path: path.join(__dirname, ".env") });

const app = express();
const PORT = process.env.PORT || 5000;
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-1.5-flash";
const API_KEY = process.env.GEMINI_API_KEY;

app.use(cors());
app.use(express.json({ limit: "10mb" }));

// Health Check Endpoint
app.get(["/", "/api/health"], (req, res) => {
  const hasValidKey = Boolean(API_KEY && API_KEY !== "your_gemini_api_key_here");
  res.json({
    status: "healthy",
    service: "Gemini Browser Assistant Backend (Node.js)",
    model: GEMINI_MODEL,
    hasApiKey: hasValidKey
  });
});

// Gemini Analysis & Chat Endpoint
app.post("/api/gemini", async (req, res) => {
  if (!API_KEY || API_KEY === "your_gemini_api_key_here") {
    return res.status(400).json({
      success: false,
      error: "GEMINI_API_KEY is not configured in backend/.env. Please add your API key."
    });
  }

  const { action, format: fmt, title, url, content, question, history } = req.body;

  let truncatedContent = content || "";
  if (truncatedContent.length > 60000) {
    truncatedContent = truncatedContent.substring(0, 60000) + "\n\n[Content truncated for token safety...]";
  }

  const prompt = buildPrompt(action, fmt, title, url, truncatedContent, question, history);

  try {
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${API_KEY}`;
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.4,
          topP: 0.95,
          maxOutputTokens: 2048
        }
      })
    });

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = data.error?.message || "Failed to communicate with Gemini API";
      return res.status(response.status).json({ success: false, error: errorMsg });
    }

    const candidate = data.candidates?.[0];
    const text = candidate?.content?.parts?.[0]?.text || "No response generated.";

    return res.json({ success: true, result: text });
  } catch (err) {
    console.error("Backend error:", err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

function buildPrompt(action, fmt, title, url, content, question, history) {
  const context = `Webpage Title: ${title}\nWebpage URL: ${url}\n\nWebpage Content:\n"""\n${content}\n"""\n\n`;

  if (action === "summarize") {
    if (fmt === "concise") {
      return `You are an AI assistant. Provide a 3-4 sentence TL;DR summary.\n\n${context}`;
    } else if (fmt === "executive") {
      return `You are an AI assistant. Provide an Executive Summary with Overview, Strategic Takeaways, and Impact.\n\n${context}`;
    }
    return `You are an AI assistant. Provide a structured summary with Overview, Key Arguments, Evidence, and Conclusion.\n\n${context}`;
  } else if (action === "key_points") {
    return `You are an analyst. Extract top key takeaways with bolded points and bullet points.\n\n${context}`;
  } else if (action === "study_notes") {
    return `You are an academic mentor. Generate structured Cornell study notes with core concepts, definitions, and 3 review questions.\n\n${context}`;
  } else if (action === "chat") {
    return `You are Gemini Browser Assistant. Answer this question based on the webpage:\n\n${context}\nQuestion: "${question}"`;
  }
  return `${context}\nSummarize the above page.`;
}

app.listen(PORT, () => {
  console.log(`[Node.js Backend] Running on http://127.0.0.1:${PORT}`);
});
