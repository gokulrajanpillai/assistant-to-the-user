// ATHU Chrome Extension - Background Service Worker (Manifest V3)
// Manages WebSocket connection to ATHU FastAPI server.

const ATHU_WS_URL = "ws://127.0.0.1:8080/ws";
const RECONNECT_DELAY_MS = 3000;

let ws = null;
let isConnected = false;

function connect() {
  try {
    ws = new WebSocket(ATHU_WS_URL);

    ws.onopen = () => {
      isConnected = true;
      console.log("[ATHU] WebSocket connected.");
      broadcastToPopup({ type: "status", status: "connected" });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        broadcastToPopup(data);
        if (data.type === "response" && data.text) {
          // Show browser notification for important responses
          showNotification(data.text);
        }
      } catch (e) {
        console.error("[ATHU] Parse error:", e);
      }
    };

    ws.onclose = () => {
      isConnected = false;
      broadcastToPopup({ type: "status", status: "disconnected" });
      console.log("[ATHU] Disconnected. Reconnecting in " + RECONNECT_DELAY_MS + "ms...");
      setTimeout(connect, RECONNECT_DELAY_MS);
    };

    ws.onerror = (err) => {
      console.error("[ATHU] WebSocket error:", err);
    };
  } catch (e) {
    console.error("[ATHU] Failed to connect:", e);
    setTimeout(connect, RECONNECT_DELAY_MS);
  }
}

function sendQuery(text) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "query", text }));
    return true;
  }
  return false;
}

function broadcastToPopup(data) {
  chrome.runtime.sendMessage(data).catch(() => {});
}

function showNotification(text) {
  chrome.notifications && chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: "ATHU",
    message: text.substring(0, 200),
  });
}

// Listen for messages from popup/content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "query") {
    const sent = sendQuery(message.text);
    sendResponse({ sent, connected: isConnected });
  } else if (message.type === "ping") {
    sendResponse({ connected: isConnected });
  }
  return true;
});

// Start connection
connect();
