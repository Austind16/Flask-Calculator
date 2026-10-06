import re
import unittest

from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from Calc.app import (
    HistoryPersistenceError,
    _safe_expression_result,
    app,
    db,
    limiter,
    save_history,
)


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

    def test_health_check_reports_database_status(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_health_check_reports_database_failure(self):
        with patch.object(
            db.session,
            "execute",
            side_effect=SQLAlchemyError("simulated database failure"),
        ):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"status": "unhealthy"})

    def test_history_write_rolls_back_database_error(self):
        with patch.object(
            db.session,
            "commit",
            side_effect=SQLAlchemyError("simulated database failure"),
        ):
            with self.client.session_transaction() as session:
                session["user_uuid"] = "test-user"
            with self.client:
                self.client.get("/")
                with self.assertRaises(HistoryPersistenceError):
                    save_history("2 + 2 = 4")
        with app.app_context():
            self.assertFalse(db.session.new)

    def test_unknown_operation_type_is_rejected(self):
        token = self._csrf_token()
        response = self.client.post(
            "/",
            data={"csrf_token": token, "operation_type": "unknown"},
            follow_redirects=True,
        )
        self.assertIn("Invalid operation type.", response.get_data(as_text=True))

    def test_clear_history_is_rate_limited(self):
        limiter.reset()
        token = self._csrf_token()
        responses = [
            self.client.post(
                "/clear-history",
                headers={"X-CSRFToken": token},
            )
            for _ in range(11)
        ]
        self.assertEqual(responses[-1].status_code, 429)


if __name__ == "__main__":
    unittest.main()
