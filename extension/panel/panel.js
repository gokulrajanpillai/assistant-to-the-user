// ATHU Panel UI Logic

const elements = {
  status: document.getElementById("status-indicator"),
  response: document.getElementById("response-text"),
  transcript: document.getElementById("transcript-text"),
  input: document.getElementById("text-input"),
  sendBtn: document.getElementById("send-btn"),
  tradingConfirm: document.getElementById("trading-confirm"),
  tradingConfirmText: document.getElementById("trading-confirm-text"),
  tradingConfirmBtn: document.getElementById("trading-confirm-btn"),
  tradingCancelBtn: document.getElementById("trading-cancel-btn"),
  settingsLink: document.getElementById("settings-link"),
};

let pendingTrade = null;
let tradeClickCount = 0;

// --- Status Management ---

function setStatus(status) {
  elements.status.className = "status-dot";
  if (status === "connected") elements.status.classList.add("status-connected");
  else if (status === "thinking") elements.status.classList.add("status-thinking");
  else elements.status.classList.add("status-disconnected");
  elements.status.title = status.charAt(0).toUpperCase() + status.slice(1);
}

function setResponse(text) {
  elements.response.textContent = text;
}

function setTranscript(text) {
  elements.transcript.textContent = text ? "You said: " + text : "";
}

// --- Sending Messages ---

function sendQuery(text) {
  if (!text.trim()) return;
  setTranscript(text);
  setStatus("thinking");
  setResponse("Processing...");
  chrome.runtime.sendMessage({ type: "query", text }, (response) => {
    if (!response || !response.sent) {
      setResponse("Not connected to ATHU. Is the server running?");
      setStatus("disconnected");
    }
  });
  elements.input.value = "";
}

elements.sendBtn.addEventListener("click", () => {
  sendQuery(elements.input.value);
});

elements.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendQuery(elements.input.value);
});

// --- Receiving Messages from Background ---

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "status") {
    setStatus(message.status);
    if (message.status === "disconnected") setResponse("Disconnected. Reconnecting...");
    else if (message.status === "connected") setResponse("Connected. How can I assist you, Sir?");
  } else if (message.type === "thinking") {
    setStatus("thinking");
    setResponse("...");
  } else if (message.type === "response") {
    setStatus("connected");
    setResponse(message.text || "");
    if (message.text && message.text.toLowerCase().includes("confirm")) {
      showTradingConfirm(message.text);
    }
  }
});

// --- Trading Confirmation (double-click safety) ---

function showTradingConfirm(text) {
  pendingTrade = text;
  tradeClickCount = 0;
  elements.tradingConfirmText.textContent = text;
  elements.tradingConfirm.classList.remove("hidden");
}

function hideTradingConfirm() {
  elements.tradingConfirm.classList.add("hidden");
  pendingTrade = null;
  tradeClickCount = 0;
}

elements.tradingConfirmBtn.addEventListener("dblclick", () => {
  if (pendingTrade) {
    sendQuery("Confirm");
    hideTradingConfirm();
  }
});

elements.tradingCancelBtn.addEventListener("click", () => {
  sendQuery("Cancel trade");
  hideTradingConfirm();
});

// --- Settings ---

elements.settingsLink.addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// --- Init ---

chrome.runtime.sendMessage({ type: "ping" }, (response) => {
  if (response && response.connected) setStatus("connected");
  else setStatus("disconnected");
});
