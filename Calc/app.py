import os
from pathlib import Path
from uuid import uuid4
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import math

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")
database_url = os.getenv("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///calculator.db"
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Calculation(db.Model):
    __tablename__ = "calculations"

    id = db.Column(db.Integer, primary_key=True)
    user_uuid = db.Column(db.String(36), nullable=False, index=True)
    history = db.Column(db.Text, nullable=False)


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
                    # Replace ^ with ** for power operations
                    expression_eval = expression.replace("^", "**")
                    # Insert * for implicit multiplication (e.g., 2pi, 2sin(30), )(, )log(10)).
                    import re
                    expression_eval = re.sub(
                        r'(\d|\))\s*(pi|e|sin|cos|tan|sqrt|log|exp|\()',
                        r'\1*\2',
                        expression_eval
                    )
                    # Auto-close missing right parentheses for incomplete function inputs.
                    open_parens = expression_eval.count("(")
                    close_parens = expression_eval.count(")")
                    if open_parens > close_parens:
                        expression_eval += ")" * (open_parens - close_parens)
                    allowed_names = {
                        "sin": lambda x: math.sin(math.radians(x)),
                        "cos": lambda x: math.cos(math.radians(x)),
                        "tan": lambda x: math.tan(math.radians(x)),
                        "sqrt": math.sqrt,
                        "log": math.log10,
                        "exp": math.exp,
                        "pi": math.pi,
                        "e": math.e
                    }
                    # Safely evaluate with restricted namespace
                    result = eval(expression_eval, {"__builtins__": {}}, allowed_names)
                    result = round(result, 4) if isinstance(result, float) else result
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
                except Exception:
                    result = "Invalid expression"
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
    