let display = document.getElementById("display");
let expressionField = document.getElementById("expression");
let opField = document.getElementById("operation");
let opTypeField = document.getElementById("operation_type");

let expression="";

let pendingSingleOp = null;

function press(num) {
    // If a single op is pending, collect number input for it
    if (pendingSingleOp) {
        if (display.value === "" || expression === "") {
            expression = num;
        } else {
            expression += num;
        }
        display.value = expression;
    } else {
        expression += num;
        display.value = expression;
    }
}

function setOp(op) {
    if (expression === "") return;
    expression += op;
    display.value = expression;
}

function setBracket(bracket) {
    if (pendingSingleOp) return;
    if (bracket === ")" && expression === "") return;
    expression += bracket;
    display.value = expression;
}

function setSingle(op) {
    // Arm the operation and show function symbol/notation
    pendingSingleOp = op;
    expression = "";
    let symbol = "";
    switch(op) {
        case "sqrt":
            symbol = "√";
            break;
        case "sin":
            symbol = "sin(";
            break;
        case "cos":
            symbol = "cos(";
            break;
        case "tan":
            symbol = "tan(";
            break;
        case "log":
            symbol = "log(";
            break;
        case "exp":
            symbol = "e^";
            break;
        default:
            symbol = "";
    }
    display.value = symbol;
}


function clearDisplay() {
    expression = "";
    display.value = "";
    expressionField.value = "";
    opField.value = "";
    opTypeField.value = "";
    pendingSingleOp = null;
}


document.getElementById("calcForm").addEventListener("submit", function (e) {
    if (pendingSingleOp) {
        // If a single op is pending, submit as single op
        let num = display.value.trim();
        if (num === "") {
            e.preventDefault();
            return;
        }
        opField.value = pendingSingleOp;
        opTypeField.value = "single_ops";
        document.getElementById("num1").value = num;
        pendingSingleOp = null;
    } else {
        opTypeField.value = "expression";
        expressionField.value = expression;
    }
});


document.addEventListener("keydown", function (e) {
    let key = e.key;

    if (!isNaN(key)) { press(key); }
    if (key === ".") { press("."); }
    if (key === "(" || key === ")") { setBracket(key); }
    if (["+", "-", "*", "/", "^"].includes(key)) { setOp(key); }

    // Function keys: if pending, submit; else, arm
    if (key === "s") { setSingle("sin"); }
    if (key === "c") { setSingle("cos"); }
    if (key === "t") { setSingle("tan"); }
    if (key === "q") { setSingle("sqrt"); }
    if (key === "l") { setSingle("log"); }


    if (key === "e") { setSingle("exp"); }


    if (key === "Enter") {
        e.preventDefault();
        document.getElementById("calcForm").requestSubmit();
    }


    if (key === "Escape") { clearDisplay(); }

    if (key === "Backspace") {
        expression = expression.slice(0, -1);
        display.value = expression;
    }

});
function clearHistory(){

    let historyList = document.getElementById("historyList");
    historyList.innerHTML = "";

    fetch("/clear-history", {
        method: "POST"
    });

}