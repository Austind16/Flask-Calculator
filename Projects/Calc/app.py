import os
from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import math

load_dotenv(dotenv_path="../../.env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

@app.route("/", methods=["GET", "POST"])
def calculator():
    if "history" not in session:
        session["history"] = []
    
    result = None

    if request.method == "POST":
        operation = request.form.get("operation")

        # Always read num1 and num2 from the HTML
        num1 = request.form.get("num1", "").strip()
        num2 = request.form.get("num2", "").strip()

        # ------------------------------
        # SINGLE NUMBER OPERATIONS
        # ------------------------------
        single_ops = ["sin", "cos", "tan", "sqrt", "log", "exp"]

        if operation in single_ops:
            if num1 == "":
                result = "Please enter a number."
            else:
                try:
                    num = float(num1)
                except:
                    result = "Invalid input. Please enter a valid number."

                if operation == "sin":
                    result = round(math.sin(math.radians(num)), 4)
                    session["history"].append(f"sin({num}) = {result}")
                elif operation == "cos":
                    result = round(math.cos(math.radians(num)), 4)  
                    session["history"].append(f"cos({num}) = {result}")
                elif operation == "tan":
                    result = round(math.tan(math.radians(num)), 4)
                    session["history"].append(f"tan({num}) = {result}")
                elif operation == "sqrt":
                    result = "Error: negative root" if num < 0 else round(math.sqrt(num), 4)
                    session["history"].append(f"sqrt({num}) = {result}")
                elif operation == "log":
                    result = "Error: log undefined for ≤ 0" if num <= 0 else round(math.log10(num), 4)
                    session["history"].append(f"log({num}) = {result}")
                elif operation == "exp":
                    try:
                        result = round(math.exp(num), 4)
                        session["history"].append(f"exp({num}) = {result}")
                    except OverflowError:
                        result = "Error: result too large to calculate"
                        session["history"].append(f"exp({num}) = {result}")

        # ------------------------------
        # TWO-NUMBER OPERATIONS
        # ------------------------------
        else:
            if num1 == "" or num2 == "":
                result = "Please enter both numbers."
            else:
                try:
                    num1 = float(num1)
                    num2 = float(num2)
                except:
                    result = "Invalid input. Please enter valid numbers."

                if operation in ["+", "add"]:
                    result = num1 + num2
                    session["history"].append(f"{num1} + {num2} = {result}")
                elif operation in ["-", "sub"]:
                    result = num1 - num2
                    session["history"].append(f"{num1} - {num2} = {result}")
                elif operation in ["*", "mul"]:
                    result = num1 * num2
                    session["history"].append(f"{num1} * {num2} = {result}")
                elif operation in ["/", "div"]:
                    result = "Error: cannot divide by 0" if num2 == 0 else round(num1 / num2, 4)
                    session["history"].append(f"{num1} / {num2} = {result}")
                elif operation in ["^", "pow"]:
                    result = round(num1 ** num2, 4)
                    session["history"].append(f"{num1} ^ {num2} = {result}")

    return render_template("index.html", input_value=result, history=session.get("history", []))

@app.route("/clear-history", methods=["POST"])
def clear_history():
    session["history"] = []
    return '', 204

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)