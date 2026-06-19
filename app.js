// WebSocket & API URL configuration
const API_BASE_URL = window.location.origin === "null" || !window.location.origin ? "http://localhost:8000" : window.location.origin;
const WS_URL = API_BASE_URL.replace(/^http/, "ws") + "/ws";

let socket = null;
let reconnectInterval = 4000;
let metricsInterval = null;

// UI Elements
const wsStatusDot = document.getElementById("ws-status-dot");
const wsStatusText = document.getElementById("ws-status-text");
const sysLogsContainer = document.getElementById("sys-logs-container");
const aiOrb = document.getElementById("ai-orb");
const aiStateLabel = document.getElementById("ai-state-label");
const commsLog = document.getElementById("comms-log");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");

// Progress bars
const cpuVal = document.getElementById("cpu-val");
const cpuBar = document.getElementById("cpu-bar");
const ramVal = document.getElementById("ram-val");
const ramBar = document.getElementById("ram-bar");
const diskVal = document.getElementById("disk-val");
const diskBar = document.getElementById("disk-bar");

// Logger Helper
function logSystemEvent(text, type = "system") {
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    const timestamp = new Date().toTimeString().split(" ")[0];
    entry.innerText = `[${timestamp}] ${text}`;
    sysLogsContainer.appendChild(entry);
    sysLogsContainer.scrollTop = sysLogsContainer.scrollHeight;
}

// Render Messages to Chat Log
function appendMessage(sender, text, isUser = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${isUser ? 'user' : 'system'}`;
    
    const senderSpan = document.createElement("span");
    senderSpan.className = "sender";
    senderSpan.innerText = sender.toUpperCase();
    
    const textP = document.createElement("p");
    textP.className = "text";
    textP.innerText = text;
    
    msgDiv.appendChild(senderSpan);
    msgDiv.appendChild(textP);
    commsLog.appendChild(msgDiv);
    commsLog.scrollTop = commsLog.scrollHeight;
}

// WebSocket Connection Lifecycle
function connectWebSocket() {
    logSystemEvent("Connecting to WebSocket...", "system");
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        logSystemEvent("WebSocket connection established.", "system");
        wsStatusDot.classList.add("active");
        wsStatusText.innerText = "ONLINE";
        wsStatusText.style.color = "var(--neon-green)";
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === "state") {
                updateAIState(data.state);
            } else if (data.type === "response") {
                appendMessage("Orion", data.text, false);
            } else if (data.type === "log") {
                logSystemEvent(data.text, "system");
            } else if (data.type === "error") {
                logSystemEvent(`ERROR: ${data.code} - ${data.message}`, "error");
                appendMessage("System Error", `Fault occurred: [${data.code}] ${data.message}`, false);
            }
        } catch (e) {
            console.error("Error parsing message payload:", e);
        }
    };

    socket.onerror = (error) => {
        logSystemEvent("WebSocket error encountered.", "error");
    };

    socket.onclose = () => {
        logSystemEvent("WebSocket disconnected. Retrying in 4s...", "error");
        wsStatusDot.classList.remove("active");
        wsStatusText.innerText = "OFFLINE";
        wsStatusText.style.color = "var(--text-muted)";
        updateAIState("STANDBY");
        setTimeout(connectWebSocket, reconnectInterval);
    };
}

// Update Orb Visuals
function updateAIState(state) {
    aiOrb.className = "orb"; // reset classes
    aiStateLabel.innerText = state;
    
    switch (state) {
        case "THINKING":
            aiOrb.classList.add("thinking");
            break;
        case "SPEAKING":
            aiOrb.classList.add("speaking");
            break;
        case "STANDBY":
        default:
            aiOrb.classList.add("standby");
            break;
    }
}

// Fetch Metrics API
async function fetchMetrics() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/metrics`);
        if (!response.ok) throw new Error("HTTP error fetching metrics");
        const data = await response.json();
        
        // Update labels
        cpuVal.innerText = `${data.cpu}%`;
        ramVal.innerText = `${data.ram}%`;
        diskVal.innerText = `${data.disk}%`;

        // Update progress bars
        cpuBar.style.width = `${data.cpu}%`;
        ramBar.style.width = `${data.ram}%`;
        diskBar.style.width = `${data.disk}%`;
    } catch (e) {
        console.warn("Could not fetch metrics:", e.message);
    }
}

// Send user instruction
function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        appendMessage("You", text, true);
        socket.send(JSON.stringify({ type: "message", text: text }));
        userInput.value = "";
    } else {
        logSystemEvent("Send failed: Connection offline.", "error");
    }
}

// Input Handlers
sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});

// Speech Recognition setup (Voice input toggle)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isRecording = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    
    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add("recording");
        logSystemEvent("Voice recognition activated.", "system");
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userInput.value = transcript;
        logSystemEvent("Voice converted to input query.", "system");
        sendMessage();
    };
    
    recognition.onerror = (event) => {
        logSystemEvent(`Speech recognition error: ${event.error}`, "error");
        recognition.stop();
    };
    
    recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove("recording");
        logSystemEvent("Voice recognition deactivated.", "system");
    };

    micBtn.addEventListener("click", () => {
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
} else {
    micBtn.style.opacity = "0.5";
    micBtn.title = "Speech recognition not supported in this browser";
    micBtn.addEventListener("click", () => {
        logSystemEvent("Voice input unsupported on this platform.", "error");
    });
}

// Init Setup
connectWebSocket();
fetchMetrics(); // initial call
metricsInterval = setInterval(fetchMetrics, 3000);
