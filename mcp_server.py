"""
MCP Calculator Server
A Model Context Protocol (MCP) server providing calculation, financial,
statistical, and unit conversion tools for AI assistants.
"""

import ast
import math
import operator
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from mcp.server.mcpserver import MCPServer

# Create the MCP server instance
server = MCPServer("calculator-server")

# In-memory history of calculations performed on this server
_calculation_history: List[Dict[str, Any]] = []


def _record_history(operation: str, inputs: Dict[str, Any], result: Any) -> None:
    """Record an operation to server history."""
    _calculation_history.append({
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "inputs": inputs,
        "result": result
    })
    # Keep last 100 entries
    if len(_calculation_history) > 100:
        _calculation_history.pop(0)


# ---------------------------------------------------------------------------
# Safe AST Expression Evaluator
# ---------------------------------------------------------------------------

# Allowed binary operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitXor: operator.pow,  # Treat ^ as power
}

# Allowed unary operators
SAFE_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Allowed functions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "cbrt": math.cbrt if hasattr(math, "cbrt") else lambda x: x ** (1.0 / 3.0),
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": math.log,
    "ln": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "radians": math.radians,
    "rad": math.radians,
    "degrees": math.degrees,
    "deg": math.degrees,
    "factorial": math.factorial,
    "ceil": math.ceil,
    "floor": math.floor,
    "gcd": math.gcd,
    "comb": math.comb if hasattr(math, "comb") else None,
    "perm": math.perm if hasattr(math, "perm") else None,
}

# Allowed constants
SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau if hasattr(math, "tau") else 2 * math.pi,
    "inf": math.inf,
}


def _eval_node(node: ast.AST) -> Any:
    """Recursively and safely evaluate an AST node."""
    if isinstance(node, ast.Constant):  # Python 3.8+ numbers/constants
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_UNARY_OPS:
            operand = _eval_node(node.operand)
            return SAFE_UNARY_OPS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            # Guard against massive exponentiation attacks
            if op_type in (ast.Pow, ast.BitXor):
                if right > 10000:
                    raise ValueError("Exponent too large (max: 10000)")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are allowed")
        func_name = node.func.id.lower()
        if func_name not in SAFE_FUNCTIONS or SAFE_FUNCTIONS[func_name] is None:
            raise ValueError(f"Function '{func_name}' is not allowed or supported")
        args = [_eval_node(arg) for arg in node.args]
        return SAFE_FUNCTIONS[func_name](*args)

    elif isinstance(node, ast.Name):
        const_name = node.id.lower()
        if const_name in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[const_name]
        raise ValueError(f"Variable or identifier '{node.id}' is undefined")

    elif isinstance(node, ast.Expression):
        return _eval_node(node.body)

    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def safe_calculate(expression: str) -> float:
    """Safely parse and evaluate a mathematical expression."""
    # Preprocessing
    expr = expression.strip()
    # Replace common symbol variations
    expr = expr.replace("×", "*").replace("÷", "/")
    # If expression contains ^ replace with ** for standard Python AST parsing
    expr = expr.replace("^", "**")

    try:
        parsed = ast.parse(expr, mode="eval")
        result = _eval_node(parsed.body)
        if isinstance(result, float) and result.is_integer():
            return int(result)
        return result
    except ZeroDivisionError:
        raise ZeroDivisionError("Division by zero is undefined.")
    except Exception as e:
        raise ValueError(f"Calculation error: {str(e)}")


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@server.tool()
def calculate(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression.
    Supports arithmetic (+, -, *, /, //, %, ** or ^), brackets,
    and functions (sqrt, sin, cos, tan, asin, acos, atan, log, ln, log10,
    exp, abs, round, ceil, floor, factorial, deg, rad) and constants (pi, e).

    Args:
        expression: The mathematical expression string, e.g., "(12 * 5) + sqrt(144)" or "sin(rad(90)) + 2^4"
    """
    try:
        res = safe_calculate(expression)
        _record_history("calculate", {"expression": expression}, res)
        return {
            "status": "success",
            "expression": expression,
            "result": res,
            "formatted": f"{expression} = {res}"
        }
    except Exception as err:
        return {
            "status": "error",
            "expression": expression,
            "error": str(err)
        }


@server.tool()
def financial_calculate(
    calc_type: str,
    principal: float,
    rate_pct: float,
    time_years: float,
    compounding_freq: int = 12
) -> Dict[str, Any]:
    """
    Perform financial calculations including Compound Interest, Simple Interest, and Loan EMI / Mortgage.

    Args:
        calc_type: One of 'compound_interest', 'simple_interest', 'loan_emi'
        principal: The principal amount (starting balance or loan amount), e.g. 10000
        rate_pct: The annual interest rate as a percentage (e.g. 5.5 for 5.5%)
        time_years: Duration in years (e.g. 5 or 2.5)
        compounding_freq: Compounding periods per year (default: 12 for monthly, 1 for annual, 4 for quarterly, 365 for daily)
    """
    try:
        calc_type = calc_type.lower().strip()
        r = rate_pct / 100.0

        if calc_type == "compound_interest":
            n = compounding_freq
            t = time_years
            amount = principal * ((1 + r / n) ** (n * t))
            interest_earned = amount - principal
            res = {
                "principal": principal,
                "annual_rate_percent": rate_pct,
                "time_years": time_years,
                "compounding_frequency": compounding_freq,
                "total_future_value": round(amount, 2),
                "total_interest_earned": round(interest_earned, 2),
            }
            _record_history("financial_calculate", {"type": calc_type, "principal": principal, "rate": rate_pct}, res)
            return {"status": "success", "calculation": "compound_interest", "details": res}

        elif calc_type == "simple_interest":
            interest = principal * r * time_years
            total = principal + interest
            res = {
                "principal": principal,
                "annual_rate_percent": rate_pct,
                "time_years": time_years,
                "total_future_value": round(total, 2),
                "total_interest_earned": round(interest, 2),
            }
            _record_history("financial_calculate", {"type": calc_type, "principal": principal, "rate": rate_pct}, res)
            return {"status": "success", "calculation": "simple_interest", "details": res}

        elif calc_type in ("loan_emi", "mortgage", "emi"):
            # Monthly Interest Rate
            monthly_rate = r / 12.0
            total_months = int(time_years * 12)
            if monthly_rate == 0:
                emi = principal / total_months
            else:
                emi = (principal * monthly_rate * ((1 + monthly_rate) ** total_months)) / (
                    ((1 + monthly_rate) ** total_months) - 1
                )
            total_payment = emi * total_months
            total_interest = total_payment - principal
            res = {
                "principal_loan_amount": principal,
                "annual_interest_rate_percent": rate_pct,
                "term_years": time_years,
                "total_months": total_months,
                "monthly_payment_emi": round(emi, 2),
                "total_repayment": round(total_payment, 2),
                "total_interest_payable": round(total_interest, 2),
            }
            _record_history("financial_calculate", {"type": "loan_emi", "principal": principal, "rate": rate_pct}, res)
            return {"status": "success", "calculation": "loan_emi", "details": res}

        else:
            return {
                "status": "error",
                "error": f"Unknown calc_type '{calc_type}'. Supported: 'compound_interest', 'simple_interest', 'loan_emi'"
            }
    except Exception as err:
        return {"status": "error", "error": str(err)}


@server.tool()
def statistics_calculate(numbers: List[float]) -> Dict[str, Any]:
    """
    Compute comprehensive statistical summary for a list of numbers.
    Computes count, sum, mean, median, mode, sample standard deviation,
    variance, min, and max.

    Args:
        numbers: List of numbers, e.g. [12, 15, 23, 29, 35]
    """
    try:
        if not numbers:
            return {"status": "error", "error": "Numbers list cannot be empty."}

        count = len(numbers)
        total_sum = sum(numbers)
        mean_val = statistics.mean(numbers)
        median_val = statistics.median(numbers)

        try:
            mode_val = statistics.mode(numbers)
        except statistics.StatisticsError:
            mode_val = None

        variance_val = statistics.variance(numbers) if count > 1 else 0.0
        stdev_val = statistics.stdev(numbers) if count > 1 else 0.0
        min_val = min(numbers)
        max_val = max(numbers)
        num_range = max_val - min_val

        summary = {
            "count": count,
            "sum": round(total_sum, 4),
            "mean": round(mean_val, 4),
            "median": round(median_val, 4),
            "mode": round(mode_val, 4) if mode_val is not None else "No unique mode",
            "variance": round(variance_val, 4),
            "standard_deviation": round(stdev_val, 4),
            "min": round(min_val, 4),
            "max": round(max_val, 4),
            "range": round(num_range, 4)
        }
        _record_history("statistics_calculate", {"count": count}, summary)
        return {"status": "success", "statistics": summary}
    except Exception as err:
        return {"status": "error", "error": str(err)}


@server.tool()
def unit_convert(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """
    Convert values between various units of measurement.
    Supported categories:
    - Length: m, km, cm, mm, mi, yd, ft, in
    - Mass/Weight: kg, g, mg, lb, oz, ton
    - Temperature: c, f, k
    - Digital: b, kb, mb, gb, tb
    - Time: s, min, h, d

    Args:
        value: Numeric value to convert, e.g. 100
        from_unit: Source unit, e.g. 'mi' or 'miles' or 'c'
        to_unit: Target unit, e.g. 'km' or 'kilometers' or 'f'
    """
    try:
        u_from = from_unit.lower().strip()
        u_to = to_unit.lower().strip()

        # Normalization map
        aliases = {
            "meter": "m", "meters": "m", "kilometre": "km", "kilometer": "km", "kilometers": "km",
            "centimeter": "cm", "centimeters": "cm", "millimeter": "mm", "millimeters": "mm",
            "mile": "mi", "miles": "mi", "yard": "yd", "yards": "yd", "foot": "ft", "feet": "ft",
            "inch": "in", "inches": "in",
            "kilogram": "kg", "kilograms": "kg", "gram": "g", "grams": "g", "milligram": "mg",
            "milligrams": "mg", "pound": "lb", "pounds": "lb", "ounce": "oz", "ounces": "oz",
            "celsius": "c", "fahrenheit": "f", "kelvin": "k",
            "byte": "b", "bytes": "b", "kilobyte": "kb", "megabyte": "mb", "gigabyte": "gb", "terabyte": "tb",
            "second": "s", "seconds": "s", "minute": "min", "minutes": "min", "hour": "h", "hours": "h",
            "day": "d", "days": "d"
        }
        u_from = aliases.get(u_from, u_from)
        u_to = aliases.get(u_to, u_to)

        # 1. Temperature
        if u_from in ("c", "f", "k") and u_to in ("c", "f", "k"):
            # Convert to Celsius first
            if u_from == "c":
                c = value
            elif u_from == "f":
                c = (value - 32.0) * (5.0 / 9.0)
            elif u_from == "k":
                c = value - 273.15

            # Convert Celsius to target
            if u_to == "c":
                res = c
            elif u_to == "f":
                res = (c * (9.0 / 5.0)) + 32.0
            elif u_to == "k":
                res = c + 273.15

            output = {
                "input_value": value,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "converted_value": round(res, 4),
                "category": "temperature"
            }
            _record_history("unit_convert", output, round(res, 4))
            return {"status": "success", **output}

        # Conversion tables relative to base units
        length_to_meters = {
            "m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001,
            "mi": 1609.344, "yd": 0.9144, "ft": 0.3048, "in": 0.0254
        }

        mass_to_kg = {
            "kg": 1.0, "g": 0.001, "mg": 0.000001,
            "lb": 0.45359237, "oz": 0.028349523125, "ton": 1000.0
        }

        digital_to_bytes = {
            "b": 1.0, "kb": 1024.0, "mb": 1024.0**2, "gb": 1024.0**3, "tb": 1024.0**4
        }

        time_to_seconds = {
            "s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0
        }

        for category, table in [
            ("length", length_to_meters),
            ("mass", mass_to_kg),
            ("digital", digital_to_bytes),
            ("time", time_to_seconds),
        ]:
            if u_from in table and u_to in table:
                base_val = value * table[u_from]
                res = base_val / table[u_to]
                output = {
                    "input_value": value,
                    "from_unit": from_unit,
                    "to_unit": to_unit,
                    "converted_value": round(res, 6),
                    "category": category
                }
                _record_history("unit_convert", output, round(res, 6))
                return {"status": "success", **output}

        return {
            "status": "error",
            "error": f"Cannot convert between '{from_unit}' and '{to_unit}'. Incompatible or unsupported units."
        }
    except Exception as err:
        return {"status": "error", "error": str(err)}


@server.tool()
def get_history(limit: int = 10) -> Dict[str, Any]:
    """
    Get the recent calculation history performed on the MCP server.

    Args:
        limit: Maximum number of entries to return (default: 10)
    """
    return {
        "status": "success",
        "count": min(len(_calculation_history), limit),
        "history": _calculation_history[-limit:]
    }


@server.tool()
def clear_history() -> Dict[str, Any]:
    """
    Clear the server calculation history.
    """
    _calculation_history.clear()
    return {"status": "success", "message": "Calculation history has been cleared."}


# ---------------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run the server over stdio transport
    server.run("stdio")
