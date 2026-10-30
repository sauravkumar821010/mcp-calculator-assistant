"""
Automated Test Suite for MCP-Powered AI Calculator Assistant
Run with: python -m unittest tests/test_calculator.py
"""

import math
import unittest
from mcp_server import (
    safe_calculate,
    calculate,
    financial_calculate,
    statistics_calculate,
    unit_convert,
    get_history,
    clear_history
)
from assistant import CalculatorAssistant


class TestSafeCalculator(unittest.TestCase):
    """Test safe AST mathematical expression evaluation."""

    def test_basic_arithmetic(self):
        self.assertEqual(safe_calculate("2 + 3"), 5)
        self.assertEqual(safe_calculate("10 - 4"), 6)
        self.assertEqual(safe_calculate("7 * 8"), 56)
        self.assertEqual(safe_calculate("100 / 4"), 25)
        self.assertEqual(safe_calculate("2 ** 5"), 32)
        self.assertEqual(safe_calculate("2 ^ 5"), 32)  # ^ as power
        self.assertEqual(safe_calculate("17 % 5"), 2)

    def test_operator_precedence_and_brackets(self):
        self.assertEqual(safe_calculate("2 + 3 * 4"), 14)
        self.assertEqual(safe_calculate("(2 + 3) * 4"), 20)
        self.assertEqual(safe_calculate("((10 + 5) * 2) - 10"), 20)

    def test_scientific_functions(self):
        self.assertEqual(safe_calculate("sqrt(144)"), 12)
        self.assertEqual(safe_calculate("abs(-55)"), 55)
        self.assertEqual(safe_calculate("round(3.14159, 2)"), 3.14)
        self.assertAlmostEqual(safe_calculate("sin(rad(90))"), 1.0, places=5)
        self.assertAlmostEqual(safe_calculate("cos(rad(0))"), 1.0, places=5)
        self.assertEqual(safe_calculate("factorial(5)"), 120)
        self.assertAlmostEqual(safe_calculate("log10(1000)"), 3.0, places=5)

    def test_constants(self):
        self.assertAlmostEqual(safe_calculate("pi"), math.pi, places=5)
        self.assertAlmostEqual(safe_calculate("e"), math.e, places=5)
        self.assertAlmostEqual(safe_calculate("2 * pi"), 2 * math.pi, places=5)

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            safe_calculate("10 / 0")

    def test_security_ast_injection_prevention(self):
        """Verify arbitrary code and method calls are strictly blocked."""
        unsafe_expressions = [
            "__import__('os').system('dir')",
            "open('test.txt', 'w')",
            "exec('x = 1')",
            "eval('1 + 1')",
            "(lambda x: x)(5)",
            "[x for x in [1, 2]]",
            "import os",
            "print('hello')"
        ]
        for expr in unsafe_expressions:
            with self.assertRaises(ValueError, msg=f"Should reject: {expr}"):
                safe_calculate(expr)


class TestFinancialCalculations(unittest.TestCase):
    """Test financial calculation tools."""

    def test_compound_interest(self):
        res = financial_calculate("compound_interest", principal=10000, rate_pct=5, time_years=2, compounding_freq=12)
        self.assertEqual(res["status"], "success")
        details = res["details"]
        self.assertEqual(details["total_future_value"], 11049.41)
        self.assertEqual(details["total_interest_earned"], 1049.41)

    def test_simple_interest(self):
        res = financial_calculate("simple_interest", principal=5000, rate_pct=6, time_years=3)
        self.assertEqual(res["status"], "success")
        details = res["details"]
        self.assertEqual(details["total_future_value"], 5900.0)
        self.assertEqual(details["total_interest_earned"], 900.0)

    def test_loan_emi(self):
        res = financial_calculate("loan_emi", principal=300000, rate_pct=6.5, time_years=30)
        self.assertEqual(res["status"], "success")
        details = res["details"]
        self.assertEqual(details["monthly_payment_emi"], 1896.20)
        self.assertEqual(details["total_months"], 360)
        self.assertGreater(details["total_repayment"], 300000)

    def test_invalid_type(self):
        res = financial_calculate("unknown_type", principal=100, rate_pct=5, time_years=1)
        self.assertEqual(res["status"], "error")


class TestStatisticsCalculations(unittest.TestCase):
    """Test statistical summary calculations."""

    def test_summary_metrics(self):
        numbers = [10.0, 20.0, 30.0, 40.0, 50.0]
        res = statistics_calculate(numbers)
        self.assertEqual(res["status"], "success")
        s = res["statistics"]
        self.assertEqual(s["count"], 5)
        self.assertEqual(s["sum"], 150.0)
        self.assertEqual(s["mean"], 30.0)
        self.assertEqual(s["median"], 30.0)
        self.assertEqual(s["min"], 10.0)
        self.assertEqual(s["max"], 50.0)
        self.assertEqual(s["range"], 40.0)

    def test_empty_numbers(self):
        res = statistics_calculate([])
        self.assertEqual(res["status"], "error")


class TestUnitConversions(unittest.TestCase):
    """Test unit conversions across categories."""

    def test_length_conversion(self):
        res = unit_convert(1.0, "km", "m")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["converted_value"], 1000.0)

        res_mi = unit_convert(100.0, "miles", "km")
        self.assertEqual(res_mi["status"], "success")
        self.assertAlmostEqual(res_mi["converted_value"], 160.9344, places=2)

    def test_temperature_conversion(self):
        res = unit_convert(100.0, "c", "f")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["converted_value"], 212.0)

        res_c = unit_convert(32.0, "f", "c")
        self.assertEqual(res_c["status"], "success")
        self.assertEqual(res_c["converted_value"], 0.0)

    def test_mass_conversion(self):
        res = unit_convert(1.0, "kg", "g")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["converted_value"], 1000.0)

    def test_digital_conversion(self):
        res = unit_convert(1.0, "gb", "mb")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["converted_value"], 1024.0)

    def test_incompatible_units(self):
        res = unit_convert(50.0, "km", "kg")
        self.assertEqual(res["status"], "error")


class TestHistoryTools(unittest.TestCase):
    """Test MCP history recording and clearing."""

    def test_history_flow(self):
        clear_history()
        calculate("5 * 5")
        calculate("10 + 20")
        hist = get_history(10)
        self.assertEqual(hist["status"], "success")
        self.assertGreaterEqual(hist["count"], 2)
        clear_history()
        hist_empty = get_history(10)
        self.assertEqual(hist_empty["count"], 0)


class TestAssistantIntegration(unittest.TestCase):
    """Test end-to-end Assistant orchestration."""

    def setUp(self):
        self.assistant = CalculatorAssistant()

    def test_math_query(self):
        res = self.assistant.ask("What is (20 * 5) + 15?")
        self.assertIn("115", res["answer"])
        self.assertEqual(len(res["tool_calls"]), 1)
        self.assertEqual(res["tool_calls"][0]["tool"], "calculate")

    def test_financial_query(self):
        res = self.assistant.ask("Compound interest on $5,000 at 5% for 2 years")
        self.assertIn("Compound Interest Calculation", res["answer"])
        self.assertEqual(res["tool_calls"][0]["tool"], "financial_calculate")

    def test_unit_query(self):
        res = self.assistant.ask("Convert 50 km to miles")
        self.assertIn("Unit Conversion Result", res["answer"])
        self.assertEqual(res["tool_calls"][0]["tool"], "unit_convert")

    def test_stats_query(self):
        res = self.assistant.ask("Find the mean and standard deviation of [10, 20, 30]")
        self.assertIn("Statistical Analysis Summary", res["answer"])
        self.assertEqual(res["tool_calls"][0]["tool"], "statistics_calculate")


if __name__ == "__main__":
    unittest.main()
