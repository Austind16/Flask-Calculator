import re
import unittest

from Calc.app import app, db, _safe_expression_result


class CalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        )
        with app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            db.drop_all()
        app.config["SQLALCHEMY_DATABASE_URI"] = cls.database_uri

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            db.session.query(db.Model.registry._class_registry["Calculation"]).delete()
            db.session.commit()

    def _csrf_token(self):
        response = self.client.get("/")
        match = re.search(
            r'name="csrf_token" value="([^"]+)"',
            response.get_data(as_text=True),
        )
        self.assertIsNotNone(match)
        return match.group(1)

    def test_supported_math_expressions(self):
        cases = {
            "2 + 3 * 4": 14,
            "sin(90)": 1,
            "sqrt(9) + log(100)": 5,
            "2^3": 8,
            "25%": 0.25,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertAlmostEqual(_safe_expression_result(expression), expected)

    def test_unsafe_syntax_is_rejected(self):
        expressions = [
            '__import__("os")',
            "(1).__class__",
            "[x for x in [1]]",
            "lambda: 1",
            "sqrt.__call__(9)",
            "unknown_name + 1",
            "1; 2",
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    _safe_expression_result(expression)

    def test_expression_limits_are_enforced(self):
        with self.assertRaises(ValueError):
            _safe_expression_result("1" * 501)
        with self.assertRaises(ValueError):
            _safe_expression_result("2^1001")
        with self.assertRaises(ValueError):
            _safe_expression_result("1@" + "1")

    def test_form_rejects_invalid_operation_and_non_finite_number(self):
        token = self._csrf_token()
        response = self.client.post(
            "/",
            data={
                "csrf_token": token,
                "operation_type": "single_ops",
                "operation": "not-supported",
                "num1": "1",
            },
            follow_redirects=True,
        )
        self.assertIn("Invalid operation.", response.get_data(as_text=True))

        response = self.client.post(
            "/",
            data={
                "csrf_token": token,
                "operation_type": "single_ops",
                "operation": "sqrt",
                "num1": "nan",
            },
            follow_redirects=True,
        )
        self.assertIn(
            "Invalid input. Please enter a valid number.",
            response.get_data(as_text=True),
        )

    def test_csrf_is_required_for_calculations(self):
        response = self.client.post(
            "/",
            data={"operation_type": "expression", "expression": "2+2"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
