function insertPi() {
    expression += "pi";
    if (pendingSingleOp && pendingSingleOp !== "square") {
        updateSingleOpDisplay();
    } else {
        display.value = expression;
    }
}
let display = document.getElementById("display");
let expressionField = document.getElementById("expression");
let opField = document.getElementById("operation");
let opTypeField = document.getElementById("operation_type");

let expression="";

let pendingSingleOp = null;
let singleOpHasClosingParen = false;

function getSingleOpPrefix(op) {
    let funcMap = {
        sin: "sin(",
        cos: "cos(",
        tan: "tan(",
        log: "log(",
        sqrt: "√",
        exp: "e^"
    };
    return funcMap[op] || "";
}

function updateSingleOpDisplay() {
    let prefix = getSingleOpPrefix(pendingSingleOp);
    if (prefix === "") {
        display.value = expression;
        return;
    }

    // For trig ops, allow optional closing parenthesis in display only.
    if (["sin", "cos", "tan"].includes(pendingSingleOp)) {
        display.value = prefix + expression + (singleOpHasClosingParen ? ")" : "");
        return;
    }

    display.value = prefix + expression;
}

function press(num) {
    // If a single op is pending, collect number input for it
    if (pendingSingleOp && pendingSingleOp !== "square") {
        if (expression === "") {
            expression = num;
        } else {
            expression += num;
        }
        updateSingleOpDisplay();
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
    if (pendingSingleOp && pendingSingleOp !== "square") {
        // For trig single ops, allow an optional closing parenthesis.
        if (bracket === ")" && ["sin", "cos", "tan"].includes(pendingSingleOp) && expression !== "") {
            singleOpHasClosingParen = true;
            updateSingleOpDisplay();
        }
        return;
    }
    if (bracket === ")" && expression === "") return;
    expression += bracket;
    display.value = expression;
}

function setSingle(op) {
    if (op === "square") {
        if (expression === "") return;
        if (!expression.endsWith("^2")) {
            expression += "^2";
        }
        pendingSingleOp = null;
        display.value = expression;
        return;
    }

    // Insert functions directly into expression to support nesting.
    let fnMap = {
        sin: "sin(",
        cos: "cos(",
        tan: "tan(",
        sqrt: "sqrt(",
        log: "log(",
        exp: "exp("
    };

    let token = fnMap[op] || "";
    if (token === "") return;

    expression += token;
    pendingSingleOp = null;
    singleOpHasClosingParen = false;
    display.value = expression;
}


function clearDisplay() {
    expression = "";
    display.value = "";
    expressionField.value = "";
    opField.value = "";
    opTypeField.value = "";
    pendingSingleOp = null;
    singleOpHasClosingParen = false;
}


document.getElementById("calcForm").addEventListener("submit", function (e) {
    if (pendingSingleOp && pendingSingleOp !== "square") {
        // For single op, send only the numeric part (expression)
        let num = expression.trim();
        if (num === "") {
            e.preventDefault();
            return;
        }
        opField.value = pendingSingleOp;
        opTypeField.value = "single_ops";
        document.getElementById("num1").value = num;
        pendingSingleOp = null;
        singleOpHasClosingParen = false;
    } else if (pendingSingleOp === "square") {
        // For square, use the normal expression flow
        opTypeField.value = "expression";
        expressionField.value = expression;
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
    if (key === "x" || key === "X") { setSingle("square"); }
    if (key === "p" || key === "P") { insertPi(); }


    if (key === "e") { setSingle("exp"); }


    if (key === "Enter") {
        e.preventDefault();
        document.getElementById("calcForm").requestSubmit();
    }


    if (key === "Escape") { clearDisplay(); }

    if (key === "Backspace") {
        expression = expression.slice(0, -1);
        if (pendingSingleOp && pendingSingleOp !== "square") {
            if (expression === "") {
                singleOpHasClosingParen = false;
            }
            updateSingleOpDisplay();
        } else {
            display.value = expression;
        }
    }

});
function clearHistory(){

    let historyList = document.getElementById("historyList");
    historyList.innerHTML = "";

    fetch("/clear-history", {
        method: "POST"
    });

}
