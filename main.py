import os
import json
import asyncio
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import AsyncOpenAI

app = FastAPI(title="Orion Local AI Assistant")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama local endpoint configuration
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL_NAME = "llama3.2"

# Initialize Async OpenAI client pointing to Ollama
client = AsyncOpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"  # placeholder key for local execution
)

# System status tool definition
def get_system_status():
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu": cpu_percent,
        "ram": memory.percent,
        "disk": disk.percent,
        "ram_used_gb": round(memory.used / (1024**3), 2),
        "ram_total_gb": round(memory.total / (1024**3), 2)
    }

# File listing tool
def list_workspace_files():
    try:
        files = os.listdir(".")
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}

# File reading tool
def read_workspace_file(filename: str):
    # Basic path traversal protection
    safe_name = os.path.basename(filename)
    if not os.path.exists(safe_name):
        return {"error": f"File '{safe_name}' not found."}
    try:
        with open(safe_name, "r", encoding="utf-8") as f:
            content = f.read(1000)  # Read first 1000 characters
            if len(content) >= 1000:
                content += "\n[Truncated...]"
            return {"content": content}
    except Exception as e:
        return {"error": str(e)}

# Available tools map
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get the current system resource usage metrics like CPU, RAM, and Disk percentage.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_workspace_files",
            "description": "List the files and directories inside the active workspace.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_workspace_file",
            "description": "Read the contents of a specific file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the file to read."
                    }
                },
                "required": ["filename"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are Orion, a sleek, highly intellectual, and slightly sarcastic futuristic artificial intelligence.
You run 100% locally and offline.
Your tone is intelligent, witty, and coolly professional, occasionally teasing the user but always remaining helpful and highly competent.
You have access to local system diagnostics and workspace tools. Use them when requested or when appropriate."""

@app.get("/api/metrics")
async def get_metrics():
    return get_system_status()

# Serve frontend directly if files exist in the same directory
@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/style.css")
async def read_css():
    return FileResponse("style.css")

@app.get("/app.js")
async def read_js():
    return FileResponse("app.js")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established.")
    
    # Keep track of conversation history for this socket session
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "message":
                user_msg = payload.get("text", "")
                messages.append({"role": "user", "content": user_msg})
                
                # Notify UI we are thinking
                await websocket.send_json({"type": "state", "state": "THINKING"})
                
                try:
                    # Request completion from local Ollama model
                    response = await client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto"
                    )
                    
                    response_message = response.choices[0].message
                    
                    # Handle tool calls if any
                    if response_message.tool_calls:
                        messages.append(response_message)
                        
                        for tool_call in response_message.tool_calls:
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            
                            # Execute local function
                            await websocket.send_json({
                                "type": "log", 
                                "text": f"SYSTEM: Running tool '{function_name}' with args {function_args}..."
                            })
                            
                            if function_name == "get_system_status":
                                result = get_system_status()
                            elif function_name == "list_workspace_files":
                                result = list_workspace_files()
                            elif function_name == "read_workspace_file":
                                result = read_workspace_file(function_args.get("filename", ""))
                            else:
                                result = {"error": "Unknown tool"}
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": function_name,
                                "content": json.dumps(result)
                            })
                        
                        # Request final completion after tool output
                        await websocket.send_json({"type": "state", "state": "THINKING"})
                        second_response = await client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=messages
                        )
                        assistant_response = second_response.choices[0].message.content
                    else:
                        assistant_response = response_message.content
                    
                    # Store response in history
                    messages.append({"role": "assistant", "content": assistant_response})
                    
                except Exception as e:
                    # Fallback to local mock engine if Ollama is not running/reachable
                    print(f"Ollama error: {e}")
                    await websocket.send_json({
                        "type": "log",
                        "text": f"Ollama connection error ({type(e).__name__}: {str(e)}). Falling back to local offline mock engine..."
                    })
                    
                    # Process query using simple mock response generator
                    user_query = user_msg.lower()
                    
                    if "status" in user_query or "metric" in user_query or "cpu" in user_query or "ram" in user_query:
                        stats = get_system_status()
                        assistant_response = f"Ah, diagnostics. Let's see... CPU is at {stats['cpu']}%, RAM is at {stats['ram']}% usage, and your Disk is {stats['disk']}% full. Pretty standard, nothing is on fire yet."
                    elif "file" in user_query or "list" in user_query or "workspace" in user_query:
                        files = list_workspace_files().get("files", [])
                        assistant_response = f"Scanning directory. I found: {', '.join(files) if files else 'absolutely nothing'}. Dynamic local storage is fully operational."
                    else:
                        assistant_response = f"Greetings. I am Orion, functioning in offline mode since your local Ollama server is currently unreachable. You asked: '{user_msg}'. Once you run Ollama, I will unleash my full cognitive capabilities."
                    
                    messages.append({"role": "assistant", "content": assistant_response})
                
                # Send response back to UI
                await websocket.send_json({"type": "state", "state": "SPEAKING"})
                await websocket.send_json({"type": "response", "text": assistant_response})
                
                # Wait briefly then reset state to STANDBY
                await asyncio.sleep(1)
                await websocket.send_json({"type": "state", "state": "STANDBY"})
                    
    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    except Exception as e:
        print(f"WS error: {e}")
