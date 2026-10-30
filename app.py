"""
Flask Web Application for the MCP-Powered AI Calculator Assistant
Run with: python app.py
"""

import os
from flask import Flask, render_template, request, jsonify
from assistant import CalculatorAssistant

app = Flask(__name__)

# Initialize single assistant instance
assistant = CalculatorAssistant()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Return assistant status and active mode."""
    return jsonify({
        "status": "online",
        "mode": assistant.get_mode(),
        "has_api_key": bool(assistant.api_key),
        "server_name": "calculator-server"
    })


@app.route("/api/tools", methods=["GET"])
def get_tools():
    """Return available tools on the MCP server."""
    try:
        tools = assistant.mcp_client.list_tools()
        return jsonify({"status": "success", "tools": tools})
    except Exception as err:
        return jsonify({"status": "error", "error": str(err)}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    """Retrieve history from the MCP server."""
    try:
        limit = request.args.get("limit", default=20, type=int)
        res = assistant.mcp_client.call_tool("get_history", {"limit": limit})
        return jsonify(res)
    except Exception as err:
        return jsonify({"status": "error", "error": str(err)}), 500


@app.route("/api/clear", methods=["POST"])
def clear_history():
    """Clear calculation history on the MCP server."""
    try:
        res = assistant.mcp_client.call_tool("clear_history", {})
        return jsonify(res)
    except Exception as err:
        return jsonify({"status": "error", "error": str(err)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Process a user query through the MCP-powered AI assistant."""
    data = request.get_json(force=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"status": "error", "error": "Query cannot be empty."}), 400

    # Optional dynamic API key override from request
    api_key_override = data.get("api_key")
    if api_key_override is not None:
        if api_key_override != assistant.api_key:
            assistant.set_api_key(api_key_override)

    try:
        response_payload = assistant.ask(query)
        return jsonify({
            "status": "success",
            **response_payload
        })
    except Exception as err:
        return jsonify({
            "status": "error",
            "error": str(err),
            "query": query,
            "answer": f"An error occurred: {str(err)}",
            "tool_calls": [],
            "mode": assistant.get_mode()
        }), 500


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update API key and configuration."""
    data = request.get_json(force=True) or {}
    api_key = data.get("api_key", "").strip()
    assistant.set_api_key(api_key)
    return jsonify({
        "status": "success",
        "mode": assistant.get_mode(),
        "has_api_key": bool(assistant.api_key)
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==================================================")
    print(f"  MCP-Powered AI Calculator Web UI")
    print(f"  Serving on: http://127.0.0.1:{port}")
    print(f"  Active Mode: {assistant.get_mode().upper()}")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
