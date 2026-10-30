# 🧮 MCP-Powered AI Calculator Assistant

A complete, simple, and elegant **Model Context Protocol (MCP)** powered AI Calculator Assistant built in Python. 

The system implements the official Model Context Protocol (MCP) specification over standard input/output (`stdio`), decoupling mathematical computation and tool execution from the conversational AI brain.

---

## 🌟 Highlights & Features

- **Decoupled MCP Architecture**: The server exposes mathematical, financial, statistical, and unit conversion tools via standard MCP JSON-RPC 2.0 (`stdio`).
- **Dual-Mode AI Engine**:
  1. **Built-in Smart Agent (Zero Setup / Offline)**: Intelligent query parser and reasoning agent that runs locally without requiring any API keys.
  2. **Gemini LLM Mode**: Powered by `google-genai` function calling when a `GEMINI_API_KEY` is provided.
- **Full Calculation Toolset**:
  - `calculate`: Safe AST-based mathematical evaluator (arithmetic, brackets, roots, power, trigonometry, logarithms, factorials, constants $\pi, e$).
  - `financial_calculate`: Loan EMI / mortgage repayment, compound interest ($A = P(1+r/n)^{nt}$), and simple interest.
  - `statistics_calculate`: Sample size, sum, mean, median, mode, standard deviation, variance, and range.
  - `unit_convert`: Cross-conversion between length, mass/weight, temperature, digital storage, and time.
  - `get_history` & `clear_history`: Session audit log tracking all server calculations.
- **Dual Interfaces**:
  - 💻 **Terminal CLI**: Styled, interactive terminal assistant with colorized output (`colorama`), tool badges, and command shortcuts (`/tools`, `/history`, `/key`).
  - 🌐 **Modern Web UI**: Responsive dark-themed Flask interface featuring live MCP tool traces, preset chips, and tool inspection.
- **Safety First**: Zero `eval()` or arbitrary code execution; all expressions are parsed with Python's Abstract Syntax Tree (`ast`).
- **Cross-Host Ready**: Can also be used directly as an MCP server with Claude Desktop or any MCP-compliant client.

---

## 🏗️ Architecture Overview

```
+-------------------------------------------------------------+
|                      User Interfaces                        |
|        +--------------------+     +-------------------+     |
|        | Terminal CLI (CLI) |     | Web UI (Flask)    |     |
|        +---------+----------+     +---------+---------+     |
+------------------|--------------------------|---------------+
                   |                          |
                   v                          v
+-------------------------------------------------------------+
|               AI Calculator Assistant Engine                 |
|  - Gemini 2.5 Flash Function Calling (when API key provided)|
|  - Built-in Smart Reasoning Agent (zero-config local mode)  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                       MCP Client                            |
|  - ClientSession over stdio transport                       |
|  - Dynamic tool discovery (tools/list)                      |
|  - Tool execution & validation (tools/call)                 |
+------------------------------+------------------------------+
                               | (JSON-RPC 2.0 stdio)
                               v
+-------------------------------------------------------------+
|                  MCP Calculator Server                      |
|  (mcp.server.mcpserver.MCPServer - Model Context Protocol)  |
|                                                             |
|  Tools:                                                     |
|  * calculate(expression)      - Safe AST math evaluator     |
|  * financial_calculate(...)  - Loan EMI, Compound Interest  |
|  * statistics_calculate(...) - Mean, Median, StdDev, Min/Max|
|  * unit_convert(...)         - Length, Mass, Temp, Storage  |
|  * get_history()             - Session calculation history  |
|  * clear_history()           - Clear history log            |
+-------------------------------------------------------------+
```

---

## 🚀 Quickstart

### 1. Installation
Install the project dependencies:
```bash
pip install -r requirements.txt
```

### 2. Optional: Configure Gemini API Key
To run with Gemini LLM function-calling, copy the environment template:
```bash
copy .env.example .env
```
Add your key inside `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```
*(If omitted, the assistant seamlessly runs in built-in **Smart Agent Mode** with zero dependencies!)*

---

## 💻 Running the Terminal CLI

Launch the interactive terminal assistant:
```bash
python cli.py
```

### Example Commands & Queries in CLI:
```text
calc> /tools
calc> (45 * 12) + sqrt(144) / 4
calc> What is 18% tip on a 145 dollar bill?
calc> Calculate compound interest on $10,000 at 5% for 3 years
calc> Monthly payment for a $350,000 mortgage at 6.8% over 30 years
calc> Convert 100 miles to km
calc> Mean and standard deviation of [12, 18, 25, 30, 42]
calc> /history
calc> /exit
```

---

## 🌐 Running the Web Application

Launch the Flask web server:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Web UI Features:
- **Interactive Chat**: Natural language questions with formatted mathematical markdown.
- **Live MCP Tool Trace**: Inspect the exact tool name, arguments, and raw JSON response returned by the MCP Server.
- **Preset Chips**: One-click quick calculation queries for common financial, scientific, and statistical problems.
- **Sidebar Inspector**: Dynamic tool list and calculation history.
- **Config Dialog**: Toggle between Smart Agent and Gemini LLM mode or supply an API key on the fly.

---

## 🧪 Running Automated Tests

Run the complete test suite verifying AST expression safety, financial calculations, statistics, unit conversions, and MCP tool workflows:
```bash
python -m unittest tests/test_calculator.py
```
Expected output:
```text
Ran 22 tests in ...s
OK
```

---

## 🔌 Connecting to Claude Desktop / Any MCP Host

You can register this MCP Calculator Server directly with **Claude Desktop** by adding it to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "calculator": {
      "command": "python",
      "args": ["f:/ca-2-dl/mcp_server.py"]
    }
  }
}
```

---

## 📁 Project Structure

```
ca-2-dl/
├── mcp_server.py          # MCP Server (MCPServer stdio protocol & tools)
├── mcp_client.py          # MCP Client (ClientSession stdio bridge)
├── assistant.py           # AI Assistant (Dual-Mode: Gemini LLM & Smart Agent)
├── cli.py                 # Interactive Terminal Assistant
├── app.py                 # Flask Web App Server & REST APIs
├── templates/
│   └── index.html         # Modern web frontend template
├── static/
│   ├── style.css          # Glassmorphic dark theme styles
│   └── app.js             # Client-side dynamic interaction script
├── tests/
│   └── test_calculator.py # 22 automated test cases
├── requirements.txt       # Project dependencies
├── .env.example           # Configuration template
└── README.md              # Documentation & guide
```
