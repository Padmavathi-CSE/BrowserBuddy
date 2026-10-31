# ✦ Gemini Browser Assistant

A modern Chrome Browser Extension built with **Manifest V3** that uses **Google Gemini AI** to understand, summarize, extract key points, create Cornell-style study notes, and chat about any currently open webpage in real time.

---

## 🏗️ Architecture Overview

The system is separated into two secure tiers:
1. **Frontend Chrome Extension (Manifest V3)**:
   - Uses the modern **Chrome Side Panel API** (`chrome.sidePanel`) for an unobtrusive side-by-side workflow.
   - Cleans and extracts readable article text via `content.js` (strips ads, navigation, headers, footers, scripts).
   - Renders formatted responses with client-side Markdown, copy-to-clipboard, and markdown file export.
   - **Zero Secrets**: The frontend never holds or transmits the Google Gemini API key.
2. **Secure Local Backend Proxy**:
   - A lightweight backend (`server.py` using Python 3 standard library with **zero external dependencies**, or Node.js `server.js`).
   - Safely reads `GEMINI_API_KEY` from a local `.env` file.
   - Handles CORS preflight and routes structured prompts to Google's Generative Language REST API (`gemini-1.5-flash`).

---

## 📁 Project Structure

```
d:\GeminiBrowserAssistant\
├── backend\
│   ├── .env.example          # Environment variable template
│   ├── .env                  # Your private environment configuration
│   ├── server.py             # Zero-dependency secure Python HTTP server
│   ├── server.js             # Optional Node.js Express server alternative
│   ├── package.json          # Node.js dependencies (for server.js)
│   └── requirements.txt      # Python dependencies reference
├── extension\
│   ├── manifest.json         # Chrome Manifest V3 configuration
│   ├── background.js         # Service worker handling side panel lifecycle
│   ├── content.js            # Injected script extracting clean page text
│   ├── icons\
│   │   ├── icon16.png        # 16x16 toolbar icon
│   │   ├── icon48.png        # 48x48 extension manager icon
│   │   ├── icon128.png       # 128x128 Chrome Web Store icon
│   │   └── icon.svg          # High-resolution vector source
│   └── sidepanel\
│       ├── sidepanel.html    # Modern side panel UI layout
│       ├── sidepanel.css     # Clean, modern styles (Gemini theme)
│       └── sidepanel.js      # Extraction, UI states, Markdown & API logic
└── README.md                 # Complete documentation & quickstart guide
```

---

## 🚀 Quickstart Guide

### Step 1: Configure Your Gemini API Key

1. Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Open `backend/.env` in any text editor and paste your key:
   ```env
   GEMINI_API_KEY=AIzaSy...YourKeyHere
   PORT=5000
   GEMINI_MODEL=gemini-1.5-flash
   ```

### Step 2: Start the Secure Backend

Open a terminal or PowerShell in the project directory:

```powershell
cd d:\GeminiBrowserAssistant\backend
python server.py
```

*Output:*
```
============================================================
  GEMINI BROWSER ASSISTANT - SECURE BACKEND
============================================================
 Server running at: http://127.0.0.1:5000
 Model:            gemini-1.5-flash
 Gemini API Key:   SET
 Ready to accept requests from the Chrome Extension.
============================================================
```

> **Note**: If you prefer Node.js, you can alternatively run:
> ```bash
> cd backend
> npm install
> npm start
> ```

---

### Step 3: Load the Extension in Google Chrome

1. Open **Google Chrome** and navigate to:
   ```
   chrome://extensions
   ```
2. Toggle on **Developer mode** in the top-right corner.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `extension` folder located at:
   ```
   d:\GeminiBrowserAssistant\extension
   ```
5. You will see **Gemini Browser Assistant** appear in your extensions list.
6. Click the extension puzzle icon in the Chrome toolbar and pin **Gemini Browser Assistant**.

---

## 🎯 How to Use

1. Navigate to any webpage (e.g., a news article, blog post, Wikipedia page, or documentation).
2. Click the **Gemini Browser Assistant** icon in the Chrome toolbar.
3. The Chrome side panel opens alongside your active tab:
   - **Active Tab Card**: Automatically detects the webpage title, domain, and estimated word count.
   - **Summary Tab**:
     - Choose from *Quick TL;DR*, *Comprehensive Summary*, or *Executive Overview*.
     - Click **Summarize Page**.
   - **Key Points Tab**:
     - Extract *Top Takeaways*, *Action Items & Insights*, or *Facts & Key Statistics*.
     - Click **Extract Points**.
   - **Study Notes Tab**:
     - Generate *Cornell Structured Notes*, *Definitions & Terminology*, or a *Self-Review Quiz*.
     - Click **Generate Notes**.
   - **Ask / Chat Tab**:
     - Ask custom questions about the page content or click prompt chips like *"Main message?"* or *"Explain simply"*.
4. **Export Tools**:
   - Use the **Copy** button on any card to copy the markdown response to your clipboard.
   - Use the **Export** button to download the notes as a `.md` file.
   - Click the **Settings (gear)** icon to verify backend connection status or change the backend URL.
