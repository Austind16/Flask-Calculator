import ast
import math
import os
import re
from pathlib import Path
from uuid import uuid4
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")
database_url = os.getenv("DATABASE_URL")
if os.getenv("RENDER") and not database_url:
    raise RuntimeError("DATABASE_URL is required when running on Render")
if not database_url:
    database_url = "sqlite:///calculator.db"
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


MAX_EXPRESSION_LENGTH = 500
MAX_AST_NODES = 100
MAX_AST_DEPTH = 20
MAX_POWER = 1000


def _safe_expression_result(expression):
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError("Expression is too long")

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
    db.session.add(Calculation(user_uuid=get_user_uuid(), history=entry))
    db.session.commit()

@app.route("/", methods=["GET", "POST"])
def calculator():
    session.permanent = True

    if request.method == "POST":
        result = None
        operation_type = request.form.get("operation_type")  # "single", "expression", or "single_ops"
        
        # Handle single function operations (sin, cos, etc.)
        if operation_type == "single_ops":
            operation = request.form.get("operation")
            num1 = request.form.get("num1", "").strip()
            
            if num1 == "":
                result = "Please enter a number."
            else:
                try:
                    num = float(num1)
                except ValueError:
                    result = "Invalid input. Please enter a valid number."
                else:
                    if operation == "sin":
                        result = round(math.sin(math.radians(num)), 8)
                        save_history(f"sin({num}) = {result}")
                    elif operation == "cos":
                        result = round(math.cos(math.radians(num)), 8)  
                        save_history(f"cos({num}) = {result}")
                    elif operation == "tan":
                        result = round(math.tan(math.radians(num)), 8)
                        save_history(f"tan({num}) = {result}")
                    elif operation == "sqrt":
                        result = "Negative root invalid" if num < 0 else round(math.sqrt(num), 4)
                        save_history(f"sqrt({num}) = {result}")
                    elif operation == "log":
                        result = "Log undefined for less than or equal to 0" if num <= 0 else round(math.log10(num), 4)
                        save_history(f"log({num}) = {result}")
                    elif operation == "exp":
                        try:
                            result = round(math.exp(num), 4)
                            save_history(f"exp({num}) = {result}")
                        except OverflowError:
                            result = "Result too large to calculate"
                            save_history(f"exp({num}) = {result}")
                    elif operation == "square":
                        result = round(num ** 2, 4)
                        save_history(f"square({num}) = {result}")
        
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

        session["last_result"] = result
        session.modified = True
        return redirect(url_for("calculator"))

    result = session.pop("last_result", None)
    history = [calculation.history for calculation in Calculation.query.filter_by(
        user_uuid=get_user_uuid()
    ).order_by(Calculation.id.desc()).all()]
    return render_template("index.html", input_value=result, history=history)

@app.route("/clear-history", methods=["POST"])
def clear_history():
    Calculation.query.filter_by(user_uuid=get_user_uuid()).delete()
    db.session.commit()
    return '', 204

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)  