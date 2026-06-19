# Orion Local AI Assistant 🌌

A sleek, offline-first local AI assistant powered by **FastAPI**, **WebSockets**, and **Ollama**. Orion runs 100% locally on your machine, guaranteeing privacy and ultra-low latency diagnostics.

## 🚀 Features

- **Local LLM**: Integrated with Meta's **Llama 3.2 (3B)** running offline via Ollama.
- **WebSocket Communication**: Real-time token streaming and status updates (Standby, Thinking, Speaking).
- **System Diagnostics**: Real-time monitoring of local CPU, RAM, and Disk metrics.
- **Workspace Tool Calling**: The assistant can list and inspect files in your workspace directly.
- **Voice Control**: Integrated web speech recognition support.
- **Zero-Cloud dependency**: Keeps your private data 100% local.

---

## 🛠️ Setup & Installation

### Prerequisites
1. **Python 3.8+** installed.
2. **Ollama** installed on your system. If you haven't installed it yet, download it from [ollama.com](https://ollama.com) (or run the installer executable in this directory if available).

### Step 1: Install Dependencies
Open your terminal in the project directory and run:
```bash
pip install -r requirements.txt
```

### Step 2: Download the LLM Model
Open your terminal and pull the Llama 3.2 model:
```bash
ollama pull llama3.2
```

---

## 🏃 Running the Application

### 1. Start Ollama
Ensure the Ollama service is running on your machine:
```bash
ollama serve
```

### 2. Start the FastAPI Server
Run the FastAPI web backend:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Open the UI
Open your web browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---
<img width="1528" height="731" alt="image" src="https://github.com/user-attachments/assets/5ec94d96-a405-431e-a235-071b76dfbcc8" />


## 📂 Project Structure

- `main.py`: FastAPI server configuration, WebSocket management, and system-level tools.
- `index.html`: Modern, premium glassmorphism user interface.
- `style.css`: Design stylesheets, futuristic animations, and response layouts.
- `app.js`: Frontend logic, WebSocket lifecycle, voice synthesis, and metrics update handler.
- `requirements.txt`: Python package dependencies.
- `.gitignore`: Configured to exclude massive files and folders (like local model configs and installers).
