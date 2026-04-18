let display = document.getElementById("display");
let expressionField = document.getElementById("expression");
let opField = document.getElementById("operation");
let opTypeField = document.getElementById("operation_type");

let expression="";

function press(num){
expression+=num;
display.value=expression;
}

function setOp(op){
if(expression==="") return;
expression+=op;
display.value=expression;
}

function setSingle(op){
let num=display.value;
if(num==="") return;
expression=num;
opField.value=op;
opTypeField.value="single_ops";
document.getElementById("num1").value=num;
document.getElementById("calcForm").submit();
}

function clearDisplay(){
expression="";
display.value="";
expressionField.value="";
opField.value="";
opTypeField.value="";
}

document.getElementById("calcForm").addEventListener("submit",function(){
opTypeField.value="expression";
expressionField.value=expression;
});

document.addEventListener("keydown",function(e){

let key=e.key;

if(!isNaN(key)){ press(key); }

if(key==="."){ press("."); }

if(["+","-","*","/","^"].includes(key)){ setOp(key); }

if(key==="s"){ setSingle("sin"); }

if(key==="c"){ setSingle("cos"); }

if(key==="t"){ setSingle("tan"); }

if(key==="q"){ setSingle("sqrt"); }

if(key==="l"){ setSingle("log"); }

if(key==="e"){ setSingle("exp"); }

if(key==="Enter"){
e.preventDefault();
document.getElementById("calcForm").requestSubmit();
}

if(key==="Escape"){ clearDisplay(); }

if(key==="Backspace"){
expression=expression.slice(0,-1);
display.value=expression;
}

});
function clearHistory(){

    let historyList = document.getElementById("historyList");
    historyList.innerHTML = "";

    fetch("/clear-history", {
        method: "POST"
    });

}