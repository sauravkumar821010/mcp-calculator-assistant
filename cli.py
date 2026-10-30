"""
Interactive CLI for the MCP-Powered AI Calculator Assistant
Run with: python cli.py
"""

import sys
import os
import json
from colorama import init, Fore, Style

# Ensure stdout and stderr handle utf-8 safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from assistant import CalculatorAssistant

# Initialize colorama for cross-platform color support
init(autoreset=True)


def banner():
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.GREEN + Style.BRIGHT + "       MCP-POWERED AI CALCULATOR ASSISTANT")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.WHITE + " Connected to Model Context Protocol (MCP) Server")
    print(Fore.YELLOW + " Type a math query or command (type '/help' for commands)")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65 + "\n")


def print_help():
    print(Fore.YELLOW + Style.BRIGHT + "\nCommands:")
    print(Fore.WHITE + "  /help         - Show this help message")
    print(Fore.WHITE + "  /tools        - List tools exposed by the MCP Calculator Server")
    print(Fore.WHITE + "  /history      - View calculation history on MCP server")
    print(Fore.WHITE + "  /clear        - Clear MCP server calculation history")
    print(Fore.WHITE + "  /mode         - Show current active engine mode (Smart Agent / LLM)")
    print(Fore.WHITE + "  /key <API_KEY>- Set Gemini API key for live LLM mode")
    print(Fore.WHITE + "  /exit, /quit  - Exit the assistant\n")
    print(Fore.YELLOW + Style.BRIGHT + "Example Queries:")
    print(Fore.CYAN + "  * (45 * 12) + sqrt(144) / 4")
    print(Fore.CYAN + "  * What is 18% tip on a 145 dollar bill?")
    print(Fore.CYAN + "  * Calculate compound interest on $15,000 at 6.5% for 4 years")
    print(Fore.CYAN + "  * Monthly payment for a $350,000 mortgage at 6.8% over 30 years")
    print(Fore.CYAN + "  * Convert 75 miles to km")
    print(Fore.CYAN + "  * Convert 98.6 fahrenheit to celsius")
    print(Fore.CYAN + "  * Mean, median and standard deviation of [14, 22, 28, 35, 42]\n")


def print_tool_card(tool_name: str, args: dict, result: dict):
    print(Fore.MAGENTA + Style.BRIGHT + "  +-- [MCP Tool Call] " + "-" * 38 + "+")
    print(Fore.MAGENTA + "  | Tool: " + Fore.WHITE + Style.BRIGHT + f"{tool_name}")
    args_str = json.dumps(args, ensure_ascii=False)
    if len(args_str) > 55:
        args_str = args_str[:52] + "..."
    print(Fore.MAGENTA + "  | Args: " + Fore.CYAN + f"{args_str}")
    
    # Format output preview
    res_str = json.dumps(result, ensure_ascii=False)
    if len(res_str) > 55:
        res_str = res_str[:52] + "..."
    print(Fore.MAGENTA + "  | Output: " + Fore.GREEN + f"{res_str}")
    print(Fore.MAGENTA + Style.BRIGHT + "  +" + "-" * 58 + "+")


def main():
    banner()
    assistant = CalculatorAssistant()
    
    mode = assistant.get_mode()
    mode_color = Fore.GREEN if mode == "gemini-llm" else Fore.BLUE
    print(f"Active Mode: {mode_color}{mode.upper()}{Style.RESET_ALL}\n")

    while True:
        try:
            prompt_str = Fore.GREEN + Style.BRIGHT + "calc> " + Style.RESET_ALL
            user_input = input(prompt_str).strip()
            
            if not user_input:
                continue

            # Command handling
            cmd = user_input.lower()
            if cmd in ("/exit", "/quit", "exit", "quit"):
                print(Fore.YELLOW + "Goodbye! Happy calculating!")
                break
                
            elif cmd in ("/help", "help"):
                print_help()
                continue
                
            elif cmd in ("/mode", "mode"):
                cur_mode = assistant.get_mode()
                print(Fore.CYAN + f"Current active mode: {cur_mode}")
                continue
                
            elif cmd.startswith("/key"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_key = parts[1].strip()
                    assistant.set_api_key(new_key)
                    print(Fore.GREEN + f"API Key set! Mode is now: {assistant.get_mode()}")
                else:
                    print(Fore.RED + "Usage: /key <YOUR_GEMINI_API_KEY>")
                continue
                
            elif cmd in ("/tools", "tools"):
                print(Fore.CYAN + "\nQuerying MCP Server tools over stdio...")
                tools = assistant.mcp_client.list_tools()
                print(Fore.GREEN + f"Discovered {len(tools)} MCP Tools:")
                for t in tools:
                    print(Fore.YELLOW + f" * {t['name']}")
                    desc_first_line = t['description'].strip().split('\n')[0]
                    print(Fore.WHITE + f"   {desc_first_line}")
                print()
                continue
                
            elif cmd in ("/history", "history"):
                res = assistant.mcp_client.call_tool("get_history", {"limit": 10})
                entries = res.get("history", [])
                if not entries:
                    print(Fore.YELLOW + "MCP calculation history is empty.\n")
                else:
                    print(Fore.CYAN + f"\nRecent MCP Calculations ({len(entries)}):")
                    for i, e in enumerate(entries, 1):
                        print(Fore.WHITE + f" {i}. [{e['operation']}] {json.dumps(e['inputs'])} -> {e['result']}")
                    print()
                continue
                
            elif cmd in ("/clear", "clear"):
                res = assistant.mcp_client.call_tool("clear_history", {})
                print(Fore.GREEN + res.get("message", "History cleared.") + "\n")
                continue

            # Process AI Assistant query
            print(Fore.WHITE + Style.DIM + "Analyzing & dispatching to MCP Server...")
            result = assistant.ask(user_input)

            # Display MCP tool calls if any were made
            if result.get("tool_calls"):
                print()
                for tc in result["tool_calls"]:
                    print_tool_card(tc.get("tool", "tool"), tc.get("args", {}), tc.get("result", {}))
                print()

            # Display final answer
            print(Fore.WHITE + Style.BRIGHT + result["answer"])
            print("-" * 65 + "\n")

        except (KeyboardInterrupt, EOFError):
            print(Fore.YELLOW + "\nSession closed. Goodbye!")
            break
        except Exception as err:
            print(Fore.RED + f"Error: {err}\n")


if __name__ == "__main__":
    main()
