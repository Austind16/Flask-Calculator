from flask import Flask, render_template, request
import math

app = Flask(__name__)
history = []

@app.route("/", methods=["GET", "POST"])
def calculator():
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
                num = float(num1)

                if operation == "sin":
                    result = math.sin(math.radians(num))
                    history.append(f"sin({num}) = {result}")
                elif operation == "cos":
                    result = math.cos(math.radians(num))
                    history.append(f"cos({num}) = {result}")
                elif operation == "tan":
                    result = math.tan(math.radians(num))
                    history.append(f"tan({num}) = {result}")
                elif operation == "sqrt":
                    result = "Error: negative root" if num < 0 else math.sqrt(num)
                    history.append(f"sqrt({num}) = {result}")
                elif operation == "log":
                    result = "Error: log undefined for ≤ 0" if num <= 0 else math.log10(num)
                    history.append(f"log({num}) = {result}")
                elif operation == "exp":
                    result = math.exp(num)
                    history.append(f"exp({num}) = {result}")

        # ------------------------------
        # TWO-NUMBER OPERATIONS
        # ------------------------------
        else:
            if num1 == "" or num2 == "":
                result = "Please enter both numbers."
            else:
                num1 = float(num1)
                num2 = float(num2)

                if operation in ["+", "add"]:
                    result = num1 + num2
                    history.append(f"{num1} + {num2} = {result}")
                elif operation in ["-", "sub"]:
                    result = num1 - num2
                    history.append(f"{num1} - {num2} = {result}")
                elif operation in ["*", "mul"]:
                    result = num1 * num2
                    history.append(f"{num1} * {num2} = {result}")
                elif operation in ["/", "div"]:
                    result = "Error: cannot divide by 0" if num2 == 0 else num1 / num2
                    history.append(f"{num1} / {num2} = {result}")
                elif operation in ["^", "pow"]:
                    result = num1 ** num2
                    history.append(f"{num1} ^ {num2} = {result}")

    return render_template("index.html", input_value=result, history=history)


if __name__ == "__main__":
    app.run(debug=True)