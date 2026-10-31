/**
 * Gemini Browser Assistant - Content Script
 * Extracts readable, clean text and metadata from the active webpage,
 * stripping boilerplate navigation, ads, headers, and footers.
 */

(() => {
  // Prevent duplicate declaration if reinjected
  if (window.__geminiContentScriptLoaded) {
    return;
  }
  window.__geminiContentScriptLoaded = true;

  /**
   * Cleans and extracts main body text from DOM
   */
  function extractPageText() {
    // Check for user-selected text first
    const selection = window.getSelection() ? window.getSelection().toString().trim() : "";

    // Candidate containers for primary content
    const selectors = [
      "article",
      "main",
      "[role='main']",
      ".post-content",
      ".article-content",
      ".entry-content",
      "#content",
      ".content",
      ".markdown-body", // GitHub and docs
      "body"
    ];

    let targetElement = null;
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el && el.innerText && el.innerText.trim().length > 200) {
        targetElement = el;
        break;
      }
    }

    if (!targetElement) {
      targetElement = document.body || document.documentElement;
    }

    // Clone element to safely sanitize without altering live webpage
    const clone = targetElement.cloneNode(true);

    // Tags and selectors to eliminate (scripts, styles, navigation, ads, footers, etc.)
    const removeSelectors = [
      "script",
      "style",
      "noscript",
      "iframe",
      "svg",
      "canvas",
      "nav",
      "header",
      "footer",
      "aside",
      "[role='banner']",
      "[role='navigation']",
      "[role='complementary']",
      ".ad",
      ".ads",
      ".advertisement",
      ".cookie-banner",
      ".consent-banner",
      ".share-buttons",
      ".social-share",
      ".comments",
      "#comments",
      ".popup",
      ".modal"
    ];

    removeSelectors.forEach((sel) => {
      const matched = clone.querySelectorAll(sel);
      matched.forEach((node) => node.remove());
    });

    // Extract text with clean paragraph and heading separation
    let cleanedText = "";
    if (clone.innerText) {
      cleanedText = clone.innerText;
    } else if (clone.textContent) {
      cleanedText = clone.textContent;
    }

    // Clean multiple line breaks and excessive whitespace
    cleanedText = cleanedText
      .replace(/\r\n/g, "\n")
      .replace(/\t/g, " ")
      .replace(/[ ]{2,}/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();

    // Collect Meta information
    const title = document.title || "";
    const metaDescription =
      document.querySelector('meta[name="description"]')?.getAttribute("content") ||
      document.querySelector('meta[property="og:description"]')?.getAttribute("content") ||
      "";

    // Estimate word count
    const words = cleanedText ? cleanedText.split(/\s+/).filter(Boolean).length : 0;

    return {
      title: title.trim(),
      url: window.location.href,
      description: metaDescription.trim(),
      content: cleanedText,
      selectedText: selection,
      wordCount: words
    };
  }

  // Make globally accessible if invoked directly via chrome.scripting.executeScript
  window.__geminiExtractPageData = extractPageText;

  // Listen for messages from Side Panel or Background Script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "GET_PAGE_DATA") {
      try {
        const pageData = extractPageText();
        sendResponse({ success: true, data: pageData });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
      return true; // Keep message channel open for async response
    }
  });
})();
