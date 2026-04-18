import os
from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import math

load_dotenv(dotenv_path="../../.env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")

@app.route("/", methods=["GET", "POST"])
def calculator():
    if "history" not in session:
        session["history"] = []
    
    session.permanent = True
    result = None

    if request.method == "POST":
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
        
        # Handle expression evaluation (multiple operations)
        elif operation_type == "expression":
            expression = request.form.get("expression", "").strip()
            
            if expression == "":
                result = "Please enter an expression."
            else:
                try:
                    # Replace ^ with ** for power operations
                    expression_eval = expression.replace("^", "**")
                    # Safely evaluate with restricted namespace
                    result = eval(expression_eval, {"__builtins__": {}}, {})
                    result = round(result, 4) if isinstance(result, float) else result
                    session["history"].append(f"{expression} = {result}")
                except ZeroDivisionError:
                    result = "Error: cannot divide by 0"
                    session["history"].append(f"{expression} = {result}")
                except Exception as e:
                    result = f"Error: {str(e)}"
                    session["history"].append(f"{expression} = {result}")

    return render_template("index.html", input_value=result, history=session.get("history", []))

@app.route("/clear-history", methods=["POST"])
def clear_history():
    session["history"] = []
    return '', 204

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)