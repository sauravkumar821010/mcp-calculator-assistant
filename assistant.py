"""
AI Calculator Assistant Engine
Bridges natural language user queries with the MCP Calculator Server.
Supports both:
  1. Live Gemini LLM mode (via google-genai function calling) when GEMINI_API_KEY is available.
  2. Built-in Smart Reasoning Agent mode (runs 100% locally with zero dependencies or API keys).
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

from mcp_client import MCPCalculatorClient

load_dotenv()


class CalculatorAssistant:
    """
    AI Assistant that translates natural language math requests into
    MCP tool calls, executes them via the MCP client, and explains the results.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.mcp_client = MCPCalculatorClient()
        self.gemini_client = None
        self._init_gemini()

    def _init_gemini(self) -> None:
        """Initialize Gemini client if API key is present."""
        if self.api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Failed to initialize Gemini client: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None

    def set_api_key(self, api_key: str) -> None:
        """Dynamically update the API key."""
        self.api_key = api_key.strip()
        self._init_gemini()

    def get_mode(self) -> str:
        """Return currently active mode."""
        return "gemini-llm" if self.gemini_client else "smart-agent"

    def ask(self, query: str) -> Dict[str, Any]:
        """
        Process a user question, route through MCP tools, and return answer with execution trace.
        """
        query_clean = query.strip()
        if not query_clean:
            return {
                "query": query,
                "answer": "Please ask a calculation or math question!",
                "tool_calls": [],
                "mode": self.get_mode()
            }

        # If Gemini LLM is active, attempt LLM function-calling
        if self.gemini_client:
            try:
                return self._ask_gemini(query_clean)
            except Exception as err:
                # Graceful fallback to smart agent if API key is invalid or rate limited
                res = self._ask_smart_agent(query_clean)
                res["llm_fallback_notice"] = f"LLM error ({err}). Used built-in Smart Agent fallback."
                return res

        # Otherwise use the Built-in Smart Reasoning Agent
        return self._ask_smart_agent(query_clean)

    # ------------------------------------------------------------------------
    # Gemini LLM Mode with MCP Tool Integration
    # ------------------------------------------------------------------------

    def _ask_gemini(self, query: str) -> Dict[str, Any]:
        """Query Gemini with MCP tools as callable functions."""
        from google.genai import types

        recorded_tool_calls: List[Dict[str, Any]] = []

        # Tool wrappers that invoke the MCP server over stdio
        def calculate(expression: str) -> str:
            """Safely evaluate a mathematical expression."""
            res = self.mcp_client.call_tool("calculate", {"expression": expression})
            recorded_tool_calls.append({"tool": "calculate", "args": {"expression": expression}, "result": res})
            return str(res)

        def financial_calculate(calc_type: str, principal: float, rate_pct: float, time_years: float, compounding_freq: int = 12) -> str:
            """Perform compound interest, simple interest, or loan EMI mortgage calculations."""
            args = {
                "calc_type": calc_type,
                "principal": principal,
                "rate_pct": rate_pct,
                "time_years": time_years,
                "compounding_freq": compounding_freq
            }
            res = self.mcp_client.call_tool("financial_calculate", args)
            recorded_tool_calls.append({"tool": "financial_calculate", "args": args, "result": res})
            return str(res)

        def statistics_calculate(numbers: List[float]) -> str:
            """Compute mean, median, mode, standard deviation, variance, min, max, sum."""
            args = {"numbers": numbers}
            res = self.mcp_client.call_tool("statistics_calculate", args)
            recorded_tool_calls.append({"tool": "statistics_calculate", "args": args, "result": res})
            return str(res)

        def unit_convert(value: float, from_unit: str, to_unit: str) -> str:
            """Convert values between measurement units (length, weight, temp, storage, time)."""
            args = {"value": value, "from_unit": from_unit, "to_unit": to_unit}
            res = self.mcp_client.call_tool("unit_convert", args)
            recorded_tool_calls.append({"tool": "unit_convert", "args": args, "result": res})
            return str(res)

        def get_history(limit: int = 10) -> str:
            """Get recent calculation history from the MCP server."""
            args = {"limit": limit}
            res = self.mcp_client.call_tool("get_history", args)
            recorded_tool_calls.append({"tool": "get_history", "args": args, "result": res})
            return str(res)

        def clear_history() -> str:
            """Clear the MCP server calculation history."""
            res = self.mcp_client.call_tool("clear_history", {})
            recorded_tool_calls.append({"tool": "clear_history", "args": {}, "result": res})
            return str(res)

        tools_list = [calculate, financial_calculate, statistics_calculate, unit_convert, get_history, clear_history]

        system_instruction = (
            "You are an expert AI Calculator Assistant powered by the Model Context Protocol (MCP).\n"
            "Whenever mathematical calculation, financial formulas, statistical analysis, or unit conversions "
            "are needed, YOU MUST ALWAYS call the provided MCP tools rather than doing mental math. "
            "Provide clear, elegant, step-by-step mathematical explanations based on the verified MCP tool output."
        )

        response = self.gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_list,
                temperature=0.1
            )
        )

        answer_text = response.text or "Calculation completed successfully."

        return {
            "query": query,
            "answer": answer_text,
            "tool_calls": recorded_tool_calls,
            "mode": "gemini-llm"
        }

    # ------------------------------------------------------------------------
    # Built-in Smart Reasoning Agent Mode (Zero-Config / Offline)
    # ------------------------------------------------------------------------

    def _ask_smart_agent(self, query: str) -> Dict[str, Any]:
        """
        Intelligently parses user requests, routes to MCP tools, and
        formats a friendly, step-by-step educational breakdown.
        """
        q = query.strip()
        lower = q.lower()
        tool_calls: List[Dict[str, Any]] = []

        # 1. History Check
        if any(h in lower for h in ["clear history", "reset history", "wipe history"]):
            res = self.mcp_client.call_tool("clear_history", {})
            tool_calls.append({"tool": "clear_history", "args": {}, "result": res})
            return {
                "query": query,
                "answer": "Calculation history on the MCP server has been successfully cleared.",
                "tool_calls": tool_calls,
                "mode": "smart-agent"
            }

        if any(h in lower for h in ["history", "past calculations", "previous calculations", "what did i calculate"]):
            res = self.mcp_client.call_tool("get_history", {"limit": 10})
            tool_calls.append({"tool": "get_history", "args": {"limit": 10}, "result": res})
            entries = res.get("history", [])
            if not entries:
                answer = "Your calculation history on the MCP server is currently empty."
            else:
                lines = ["### Recent MCP Server Calculations\n"]
                for i, item in enumerate(reversed(entries), 1):
                    lines.append(f"{i}. **{item['operation']}**: `{json_summary(item['inputs'])}` -> **{item['result']}**")
                answer = "\n".join(lines)
            return {
                "query": query,
                "answer": answer,
                "tool_calls": tool_calls,
                "mode": "smart-agent"
            }

        # 2. Financial Intent: Compound Interest, Simple Interest, Loan EMI
        is_financial, fin_args = self._parse_financial(lower)
        if is_financial:
            res = self.mcp_client.call_tool("financial_calculate", fin_args)
            tool_calls.append({"tool": "financial_calculate", "args": fin_args, "result": res})
            answer = self._format_financial_response(fin_args, res)
            return {
                "query": query,
                "answer": answer,
                "tool_calls": tool_calls,
                "mode": "smart-agent"
            }

        # 3. Unit Conversion Intent
        is_unit, unit_args = self._parse_unit_conversion(lower)
        if is_unit:
            res = self.mcp_client.call_tool("unit_convert", unit_args)
            tool_calls.append({"tool": "unit_convert", "args": unit_args, "result": res})
            if res.get("status") == "success":
                answer = (
                    f"### Unit Conversion Result\n\n"
                    f"**{unit_args['value']} {unit_args['from_unit']}** = "
                    f"**{res['converted_value']} {unit_args['to_unit']}**\n\n"
                    f"- **Category:** {res.get('category', 'general').capitalize()}\n"
                    f"- *Computed securely via the MCP `unit_convert` tool.*"
                )
            else:
                answer = f"Error during unit conversion: {res.get('error', 'Unknown conversion error')}"
            return {
                "query": query,
                "answer": answer,
                "tool_calls": tool_calls,
                "mode": "smart-agent"
            }

        # 4. Statistical Intent: Mean, Median, StdDev, etc.
        is_stat, numbers = self._parse_statistics(lower)
        if is_stat:
            args = {"numbers": numbers}
            res = self.mcp_client.call_tool("statistics_calculate", args)
            tool_calls.append({"tool": "statistics_calculate", "args": args, "result": res})
            if res.get("status") == "success":
                s = res["statistics"]
                answer = (
                    f"### Statistical Analysis Summary\n\n"
                    f"- **Sample Size (Count):** `{s['count']}`\n"
                    f"- **Sum:** `{s['sum']}`\n"
                    f"- **Mean (Average):** `{s['mean']}`\n"
                    f"- **Median:** `{s['median']}`\n"
                    f"- **Mode:** `{s['mode']}`\n"
                    f"- **Standard Deviation:** `{s['standard_deviation']}`\n"
                    f"- **Variance:** `{s['variance']}`\n"
                    f"- **Range:** `{s['range']}` (Min: `{s['min']}`, Max: `{s['max']}`)\n\n"
                    f"*Dataset analyzed via MCP `statistics_calculate` tool.*"
                )
            else:
                answer = f"Error computing statistics: {res.get('error')}"
            return {
                "query": query,
                "answer": answer,
                "tool_calls": tool_calls,
                "mode": "smart-agent"
            }

        # 5. General Math Expression Intent
        expression = self._extract_math_expression(q)
        args = {"expression": expression}
        res = self.mcp_client.call_tool("calculate", args)
        tool_calls.append({"tool": "calculate", "args": args, "result": res})

        if res.get("status") == "success":
            val = res["result"]
            answer = (
                f"### Mathematical Result\n\n"
                f"$$\\mathbf{{{res['expression']} = {val}}}$$\n\n"
                f"- **Parsed Expression:** `{res['expression']}`\n"
                f"- **Result:** **{val}**\n\n"
                f"*Evaluated safely with AST on the MCP Calculator Server.*"
            )
        else:
            answer = (
                f"Could not evaluate expression `{expression}`.\n"
                f"**MCP Server Error:** {res.get('error')}\n\n"
                f"Tip: Try queries like `(45 * 12) + sqrt(144)`, `compound interest on 10000 at 5% for 10 years`, "
                f"`convert 50 miles to km`, or `average of [10, 20, 35, 50]`."
            )

        return {
            "query": query,
            "answer": answer,
            "tool_calls": tool_calls,
            "mode": "smart-agent"
        }

    # ------------------------------------------------------------------------
    # Natural Language Parsing Helpers
    # ------------------------------------------------------------------------

    def _parse_financial(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Extract financial parameters from text."""
        # Detect financial keywords
        is_compound = "compound" in text
        is_emi = any(w in text for w in ["emi", "loan", "mortgage", "monthly payment"])
        is_simple = "simple interest" in text

        if not (is_compound or is_emi or is_simple):
            return False, {}

        calc_type = "compound_interest" if is_compound else ("loan_emi" if is_emi else "simple_interest")

        # Find principal (e.g. $10,000 or 10000 or loan of 500000)
        p_match = re.search(r'\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.\d+)?)\s*(?:dollars|usd|loan|principal)?', text)
        principal = 10000.0
        # More targeted principal regex
        p_patterns = [
            r'(?:principal|loan|borrowed|amount|of|balance)?\s*[\$]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:dollars|\$)?\s*(?:at|with|over|for)',
            r'[\$]\s*([0-9,]+(?:\.[0-9]+)?)',
            r'\b([0-9]{4,}(?:\.[0-9]+)?)\b'
        ]
        for pat in p_patterns:
            m = re.search(pat, text)
            if m:
                try:
                    val_str = m.group(1).replace(",", "")
                    if float(val_str) > 0:
                        principal = float(val_str)
                        break
                except ValueError:
                    pass

        # Find rate percentage (e.g. 5% or 5.5 percent)
        rate_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent)', text)
        rate_pct = float(rate_match.group(1)) if rate_match else 5.0

        # Find time in years or months (e.g. 10 years or 30 yr or 24 months)
        time_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:year|years|yr|yrs)', text)
        month_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:month|months|mo)', text)

        if time_match:
            time_years = float(time_match.group(1))
        elif month_match:
            time_years = float(month_match.group(1)) / 12.0
        else:
            time_years = 5.0

        # Compounding frequency
        freq = 12
        if "daily" in text:
            freq = 365
        elif "monthly" in text:
            freq = 12
        elif "quarterly" in text:
            freq = 4
        elif "annual" in text or "yearly" in text:
            freq = 1

        return True, {
            "calc_type": calc_type,
            "principal": principal,
            "rate_pct": rate_pct,
            "time_years": time_years,
            "compounding_freq": freq
        }

    def _format_financial_response(self, args: Dict[str, Any], res: Dict[str, Any]) -> str:
        """Format financial calculation results nicely in Markdown."""
        if res.get("status") != "success":
            return f"Error calculating financial figures: {res.get('error')}"

        d = res.get("details", {})
        calc_type = res.get("calculation")

        if calc_type == "compound_interest":
            return (
                f"### Compound Interest Calculation\n\n"
                f"- **Principal Amount:** `${d['principal']:,.2f}`\n"
                f"- **Annual Interest Rate:** `{d['annual_rate_percent']}%`\n"
                f"- **Duration:** `{d['time_years']} years` ({d['compounding_frequency']}x / year compounding)\n\n"
                f"**Results:**\n"
                f"- **Future Value (Total):** **`${d['total_future_value']:,.2f}`**\n"
                f"- **Total Interest Earned:** **`${d['total_interest_earned']:,.2f}`**\n\n"
                f"*Formula: $A = P \\left(1 + \\frac{{r}}{{n}}\\right)^{{nt}}$ calculated via MCP Server.*"
            )

        elif calc_type == "loan_emi":
            return (
                f"### Loan EMI & Mortgage Summary\n\n"
                f"- **Loan Principal:** `${d['principal_loan_amount']:,.2f}`\n"
                f"- **Annual Interest Rate:** `{d['annual_interest_rate_percent']}%`\n"
                f"- **Term Duration:** `{d['term_years']} years` ({d['total_months']} payments)\n\n"
                f"**Repayment Details:**\n"
                f"- **Monthly Payment (EMI):** **`${d['monthly_payment_emi']:,.2f}`** / month\n"
                f"- **Total Repayment:** `${d['total_repayment']:,.2f}`\n"
                f"- **Total Interest Payable:** `${d['total_interest_payable']:,.2f}`\n\n"
                f"*Formula: $EMI = \\frac{{P \\cdot r \\cdot (1+r)^n}}{{(1+r)^n - 1}}$ verified on MCP Server.*"
            )

        else:
            return (
                f"### Simple Interest Calculation\n\n"
                f"- **Principal:** `${d['principal']:,.2f}`\n"
                f"- **Rate:** `{d['annual_rate_percent']}%`\n"
                f"- **Time:** `{d['time_years']} years`\n"
                f"- **Interest Earned:** **`${d['total_interest_earned']:,.2f}`**\n"
                f"- **Total Maturity Value:** **`${d['total_future_value']:,.2f}`**"
            )

    def _parse_unit_conversion(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Detect and parse unit conversion requests."""
        # Patterns like: "convert 100 miles to km", "50 kg in lbs", "98.6 f to c"
        patterns = [
            r'convert\s+([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z°]+)\s+(?:to|into|in)\s+([a-zA-Z°]+)',
            r'([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z°]+)\s+(?:to|into|in)\s+([a-zA-Z°]+)',
            r'how\s+many\s+([a-zA-Z]+)\s+(?:are\s+in|in)\s+([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)'
        ]

        for p in patterns:
            m = re.search(p, text)
            if m:
                if "how many" in text:
                    to_unit = m.group(1).replace("°", "")
                    val = float(m.group(2))
                    from_unit = m.group(3).replace("°", "")
                else:
                    val = float(m.group(1))
                    from_unit = m.group(2).replace("°", "")
                    to_unit = m.group(3).replace("°", "")

                # Ignore false positives like "5 + 3 to 10"
                if len(from_unit) <= 15 and len(to_unit) <= 15:
                    return True, {"value": val, "from_unit": from_unit, "to_unit": to_unit}

        return False, {}

    def _parse_statistics(self, text: str) -> Tuple[bool, List[float]]:
        """Detect and extract numbers for statistical analysis."""
        stat_keywords = ["mean", "median", "mode", "standard deviation", "variance", "average", "stats", "statistics"]
        if not any(k in text for k in stat_keywords):
            return False, []

        # Find bracketed list e.g. [1, 2, 3, 4, 5] or comma-separated numbers
        list_match = re.search(r'\[([0-9\s,.\-]+)\]', text)
        if list_match:
            raw_nums = list_match.group(1).split(",")
            nums = []
            for n in raw_nums:
                try:
                    nums.append(float(n.strip()))
                except ValueError:
                    pass
            if len(nums) >= 2:
                return True, nums

        # Fallback: extract list of all numbers if at least 3 numbers present
        all_numbers = re.findall(r'[-+]?[0-9]*\.?[0-9]+', text)
        float_nums = []
        for n in all_numbers:
            try:
                float_nums.append(float(n))
            except ValueError:
                pass

        if len(float_nums) >= 3:
            return True, float_nums

        return False, []

    def _extract_math_expression(self, text: str) -> str:
        """Sanitize and clean up natural language into a clean math expression."""
        expr = text.strip()

        # Handle phrases like "what is 25% of 800" -> "(25 / 100) * 800"
        pct_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*%\s+of\s+([0-9]+(?:\.[0-9]+)?)', expr, re.IGNORECASE)
        if pct_match:
            p = pct_match.group(1)
            total = pct_match.group(2)
            return f"({p} / 100) * {total}"

        # Remove leading "calculate", "what is", "evaluate", "solve", "compute", etc.
        cleaned = re.sub(r'^(?:what is|calculate|evaluate|solve|compute|find|please calculate|tell me)\s+', '', expr, flags=re.IGNORECASE)
        cleaned = cleaned.rstrip("?").strip()

        # Replace natural math keywords
        replacements = [
            ("square root of", "sqrt"),
            ("sqrt of", "sqrt"),
            ("plus", "+"),
            ("minus", "-"),
            ("times", "*"),
            ("multiplied by", "*"),
            ("divided by", "/"),
            ("over", "/"),
            ("to the power of", "**"),
            ("cubed", "**3"),
            ("squared", "**2"),
            ("percent", "/ 100"),
        ]
        for old, new in replacements:
            cleaned = re.sub(r'\b' + re.escape(old) + r'\b', new, cleaned, flags=re.IGNORECASE)

        return cleaned


def json_summary(d: Dict[str, Any]) -> str:
    """Format dictionary concisely."""
    parts = [f"{k}={v}" for k, v in d.items()]
    return ", ".join(parts[:3])


if __name__ == "__main__":
    assistant = CalculatorAssistant()
    print("Mode:", assistant.get_mode())
    
    test_queries = [
        "What is (25 * 4) + sqrt(144) / 3?",
        "What is 15% of 850?",
        "Calculate compound interest on $10,000 at 5% for 3 years compounded monthly",
        "Convert 100 miles to kilometers",
        "Find the mean and standard deviation of [12, 15, 23, 29, 35]"
    ]
    
    for q in test_queries:
        print("\n" + "=" * 60)
        print("QUERY:", q)
        res = assistant.ask(q)
        print("TOOL CALLS:", res["tool_calls"])
        print("ANSWER:\n", res["answer"])
