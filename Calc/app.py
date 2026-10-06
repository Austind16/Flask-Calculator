import ast
import math
import os
import re
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY must be set to a long, random value before starting the app"
    )
app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.getenv("RENDER"))
csrf = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)
database_url = os.getenv("DATABASE_URL")
if os.getenv("RENDER") and not database_url:
    raise RuntimeError("DATABASE_URL is required when running on Render")
if not database_url:
    instance_dir = Path(__file__).resolve().parent.parent / "instance"
    instance_dir.mkdir(exist_ok=True)
    database_url = f"sqlite:///{(instance_dir / 'calculator.db').as_posix()}"
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Calculation(db.Model):
    __tablename__ = "calculations"

    id = db.Column(db.Integer, primary_key=True)
    user_uuid = db.Column(db.String(36), nullable=False, index=True)
    history = db.Column(db.Text, nullable=False)


class UnsafeExpressionError(ValueError):
    """Raised when an expression contains unsupported calculator syntax."""


class HistoryPersistenceError(RuntimeError):
    """Raised when a calculation cannot be saved or deleted."""


MAX_EXPRESSION_LENGTH = 500
MAX_AST_NODES = 100
MAX_AST_DEPTH = 20
MAX_POWER = 1000
MAX_NUMBER_LENGTH = 100
MAX_NUMBER_ABS = 1_000_000_000_000
ALLOWED_SINGLE_OPERATIONS = {"sin", "cos", "tan", "sqrt", "log", "exp", "square"}
ALLOWED_EXPRESSION_CHARACTERS = re.compile(r"^[0-9A-Za-z_+\-*/%^().\s]*$")


def _safe_expression_result(expression):
    if not isinstance(expression, str):
        raise UnsafeExpressionError("Expression must be text")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError("Expression is too long")
    if not ALLOWED_EXPRESSION_CHARACTERS.fullmatch(expression):
        raise UnsafeExpressionError("Expression contains invalid characters")

    expression_eval = expression.replace("^", "**")
    expression_eval = re.sub(
        r"(\d+(?:\.\d+)?)%",
        r"(\1 / 100)",
        expression_eval,
    )
    expression_eval = re.sub(
        r"(\d|\))\s*(pi|e|sin|cos|tan|sqrt|log|exp|\()",
        r"\1*\2",
        expression_eval,
    )

    open_parens = expression_eval.count("(")
    close_parens = expression_eval.count(")")
    if open_parens > close_parens:
        expression_eval += ")" * (open_parens - close_parens)

    try:
        tree = ast.parse(expression_eval, mode="eval")
    except SyntaxError:
        raise

    functions = {
        "sin": lambda value: math.sin(math.radians(value)),
        "cos": lambda value: math.cos(math.radians(value)),
        "tan": lambda value: math.tan(math.radians(value)),
        "sqrt": math.sqrt,
        "log": math.log10,
        "exp": math.exp,
    }
    constants = {"pi": math.pi, "e": math.e}
    binary_operators = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
        ast.Pow: lambda left, right: left ** right,
        ast.Mod: lambda left, right: left % right,
    }
    unary_operators = {
        ast.UAdd: lambda value: value,
        ast.USub: lambda value: -value,
    }
    node_count = 0

    def evaluate(node, depth=0):
        nonlocal node_count
        node_count += 1
        if node_count > MAX_AST_NODES or depth > MAX_AST_DEPTH:
            raise UnsafeExpressionError("Expression is too complex")

        if isinstance(node, ast.Expression):
            return evaluate(node.body, depth + 1)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(
                node.value, (int, float)
            ):
                raise UnsafeExpressionError("Invalid number")
            value = float(node.value)
        elif isinstance(node, ast.Name):
            if node.id not in constants:
                raise UnsafeExpressionError("Unknown name")
            value = constants[node.id]
        elif isinstance(node, ast.UnaryOp):
            operator = unary_operators.get(type(node.op))
            if operator is None:
                raise UnsafeExpressionError("Unsupported operator")
            value = operator(evaluate(node.operand, depth + 1))
        elif isinstance(node, ast.BinOp):
            operator = binary_operators.get(type(node.op))
            if operator is None:
                raise UnsafeExpressionError("Unsupported operator")
            left = evaluate(node.left, depth + 1)
            right = evaluate(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
                raise UnsafeExpressionError("Power is too large")
            value = operator(left, right)
        elif isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in functions
                or node.keywords
                or len(node.args) != 1
            ):
                raise UnsafeExpressionError("Unsupported function call")
            value = functions[node.func.id](evaluate(node.args[0], depth + 1))
        else:
            raise UnsafeExpressionError("Unsupported expression")

        if not math.isfinite(value):
            raise OverflowError
        return value

    return evaluate(tree)


def get_user_uuid():
    if "user_uuid" not in session:
        session["user_uuid"] = str(uuid4())
    return session["user_uuid"]


def save_history(entry):
    try:
        db.session.add(Calculation(user_uuid=get_user_uuid(), history=entry))
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise HistoryPersistenceError from exc


def _parse_number(value):
    if not isinstance(value, str):
        raise ValueError("Number must be text")
    value = value.strip()
    if not value or len(value) > MAX_NUMBER_LENGTH:
        raise ValueError("Invalid number")
    number = float(value)
    if not math.isfinite(number) or abs(number) > MAX_NUMBER_ABS:
        raise ValueError("Invalid number")
    return number


@app.route("/", methods=["GET", "POST"])
@limiter.limit("30 per minute", methods=["POST"])
def calculator():
    session.permanent = True

    if request.method == "POST":
        result = None
        operation_type = request.form.get("operation_type")
        
        # Handle single function operations (sin, cos, etc.)
        if operation_type == "single_ops":
            operation = request.form.get("operation")
            num1 = request.form.get("num1", "")
            
            if operation not in ALLOWED_SINGLE_OPERATIONS:
                result = "Invalid operation."
            elif not num1.strip():
                result = "Please enter a number."
            else:
                try:
                    num = _parse_number(num1)
                except ValueError:
                    result = "Invalid input. Please enter a valid number."
                else:
                    try:
                        if operation == "sin":
                            result = round(math.sin(math.radians(num)), 8)
                        elif operation == "cos":
                            result = round(math.cos(math.radians(num)), 8)
                        elif operation == "tan":
                            result = round(math.tan(math.radians(num)), 8)
                        elif operation == "sqrt":
                            result = "Negative root invalid" if num < 0 else round(math.sqrt(num), 4)
                        elif operation == "log":
                            result = "Log undefined for less than or equal to 0" if num <= 0 else round(math.log10(num), 4)
                        elif operation == "exp":
                            result = round(math.exp(num), 4)
                        else:
                            result = round(num ** 2, 4)
                    except OverflowError:
                        result = "Result too large to calculate"
                    try:
                        save_history(f"{operation}({num}) = {result}")
                    except HistoryPersistenceError:
                        result = "Calculation completed, but history could not be saved."
        
        # Handle expression evaluation (multiple operations)
        elif operation_type == "expression":
            expression = request.form.get("expression", "").strip()
            
            if expression == "":
                result = "Please enter an expression."
            else:
                try:
                    result = _safe_expression_result(expression)
                    result = round(result, 4) if isinstance(result, float) else result
                    save_history(f"{expression} = {result}")
                except HistoryPersistenceError:
                    result = "Calculation completed, but history could not be saved."
                except UnsafeExpressionError:
                    result = "Invalid expression"
                    save_history(f"{expression} = {result}")
                except ZeroDivisionError:
                    result = "Cannot divide by 0"
                    save_history(f"{expression} = {result}")
                except ValueError:
                    result = "Math domain error"
                    save_history(f"{expression} = {result}")
                except OverflowError:
                    result = "Result too large to calculate"
                    save_history(f"{expression} = {result}")
                except SyntaxError:
                    result = "Incomplete or invalid expression"
                    save_history(f"{expression} = {result}")
        else:
            result = "Invalid operation type."

        session["last_result"] = result
        session.modified = True
        return redirect(url_for("calculator"))

    result = session.pop("last_result", None)
    history = [calculation.history for calculation in Calculation.query.filter_by(
        user_uuid=get_user_uuid()
    ).order_by(Calculation.id.desc()).all()]
    return render_template("index.html", input_value=result, history=history)

@app.get("/health")
@limiter.exempt
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ok"}, 200
    except SQLAlchemyError:
        db.session.rollback()
        return {"status": "unhealthy"}, 503


@app.route("/clear-history", methods=["POST"])
@limiter.limit("10 per minute")
def clear_history():
    try:
        Calculation.query.filter_by(user_uuid=get_user_uuid()).delete()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return {"error": "Unable to clear history"}, 503
    return "", 204

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)  