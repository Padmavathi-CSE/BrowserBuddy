/**
 * Gemini Browser Assistant - Background Service Worker (Manifest V3)
 * Handles extension lifecycle, side panel behavior, and context menu actions.
 */

// Configure the side panel to open immediately when the user clicks the toolbar icon
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error("Error enabling side panel on action click:", error));

  // Create context menus for fast access
  chrome.contextMenus.create({
    id: "gemini-open-sidepanel",
    title: "Open Gemini Assistant",
    contexts: ["page", "selection"]
  });

  chrome.contextMenus.create({
    id: "gemini-summarize-page",
    title: "Summarize this page with Gemini",
    contexts: ["page"]
  });

  chrome.contextMenus.create({
    id: "gemini-explain-selection",
    title: "Explain selection with Gemini",
    contexts: ["selection"]
  });

  console.log("Gemini Browser Assistant installed successfully.");
});

// Also ensure panel behavior is set on browser startup
chrome.runtime.onStartup.addListener(() => {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error("Error setting panel behavior on startup:", error));
});

// Handle Context Menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || !tab.id) return;

  // Open the side panel for the current window
  try {
    await chrome.sidePanel.open({ windowId: tab.windowId });
  } catch (error) {
    console.error("Failed to open side panel from context menu:", error);
  }

  // If the user selected text or clicked a quick action, notify the sidepanel via runtime message
  if (info.menuItemId === "gemini-explain-selection" && info.selectionText) {
    // Give side panel a brief moment to initialize if opening fresh
    setTimeout(() => {
      chrome.runtime.sendMessage({
        type: "TRIGGER_SELECTION_QUESTION",
        selectionText: info.selectionText,
        tabId: tab.id
      }).catch(() => {
        // Sidepanel might not be listening yet, which is fine
      });
    }, 400);
  } else if (info.menuItemId === "gemini-summarize-page") {
    setTimeout(() => {
      chrome.runtime.sendMessage({
        type: "TRIGGER_ACTION",
        action: "summarize",
        tabId: tab.id
      }).catch(() => {
        // Sidepanel will pick it up on active tab detection
      });
    }, 400);
  }
});

// Listen for tab switching to notify the sidepanel to refresh tab status if open
chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.runtime.sendMessage({
    type: "TAB_CHANGED",
    tabId: activeInfo.tabId
  }).catch(() => {
    // Normal if sidepanel is closed
  });
});

// Listen for tab updates (navigation completed)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) {
    chrome.runtime.sendMessage({
      type: "TAB_UPDATED",
      tabId: tabId,
      url: tab.url,
      title: tab.title
    }).catch(() => {
      // Normal if sidepanel is closed
    });
  }
});
