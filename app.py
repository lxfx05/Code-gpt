import logging
from flask import Flask, request, jsonify, render_template
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import difflib
import ast

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MAX_LINES = 10000
SUPPORTED_LANGS = ["php","c#","c++","lua","javascript","python","rust","kotlin","perl","scala","go"]

def color_code(code, language="python", fix_lines=None):
    lexer = get_lexer_by_name(language.lower())
    formatter = HtmlFormatter(nowrap=True)
    highlighted_code = highlight(code, lexer, formatter)
    if fix_lines:
        code_lines = highlighted_code.splitlines()
        for i in fix_lines:
            if i-1 < len(code_lines):
                code_lines[i-1] = f'<span class="fix-line">{code_lines[i-1]}</span>'
        highlighted_code = "\n".join(code_lines)
    html = f'<pre class="line-numbers language-{language}"><code>{highlighted_code}</code></pre>'
    return html

def get_modified_lines(original_code, fixed_code):
    original_lines = original_code.split("\n")
    fixed_lines = fixed_code.split("\n")
    diff = list(difflib.ndiff(original_lines, fixed_lines))
    modified_lines = []
    line_num = 0
    for d in diff:
        if d.startswith("  "):
            line_num += 1
        elif d.startswith("+ "):
            modified_lines.append(line_num + 1)
            line_num += 1
    return modified_lines

# --- Funzioni di reasoning locale ---
def explain_code(code):
    """Analizza codice Python e genera spiegazione logica linea per linea"""
    lines = code.split("\n")
    explanation = []
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("def "):
            explanation.append(f"Linea {i+1}: definizione funzione {line_stripped[4:].split('(')[0]}")
        elif line_stripped.startswith("class "):
            explanation.append(f"Linea {i+1}: definizione classe {line_stripped[6:].split('(')[0]}")
        elif "=" in line_stripped:
            var_name = line_stripped.split("=")[0].strip()
            explanation.append(f"Linea {i+1}: assegnazione variabile {var_name}")
        else:
            explanation.append(f"Linea {i+1}: operazione/istruzione")
    return "\n".join(explanation)

def fix_code(code):
    """Semplice sistema di fix: rimuove spazi finali e righe vuote consecutive"""
    lines = code.split("\n")
    fixed_lines = []
    prev_empty = False
    for line in lines:
        l = line.rstrip()
        if not l:
            if prev_empty:
                continue
            prev_empty = True
        else:
            prev_empty = False
        fixed_lines.append(l)
    return "\n".join(fixed_lines)

def translate_code(code, target_lang):
    """Traduzione minimale fra linguaggi comuni (Python -> JS per esempio)"""
    lines = code.split("\n")
    translated = []
    for line in lines:
        l = line.rstrip()
        if l.startswith("print(") and target_lang.lower() == "javascript":
            translated.append("console.log(" + l[6:])
        else:
            translated.append(l)
    return "\n".join(translated)

def generate_response(task, code, target_lang=None):
    if code.count("\n") > MAX_LINES:
        return "Errore: codice troppo lungo (>10.000 righe)"
    if target_lang and target_lang.lower() not in SUPPORTED_LANGS:
        return f"Linguaggio non supportato: {target_lang}"

    if task=="spiegazione":
        result = explain_code(code)
        lang = "python"
        fix_lines = None
    elif task=="traduzione":
        result = translate_code(code, target_lang)
        lang = target_lang
        fix_lines = None
    elif task=="fix":
        result = fix_code(code)
        lang = "python"
        fix_lines = get_modified_lines(code, result)
    else:
        return "Task non valido"

    html_result = color_code(result, language=lang, fix_lines=fix_lines)
    return html_result

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html", languages=SUPPORTED_LANGS)

@app.route("/api/code", methods=["POST"])
def code():
    data = request.json
    code_text = data.get("code","")
    task = data.get("task","")
    target_lang = data.get("target_lang",None)

    try:
        result = generate_response(task=task, code=code_text, target_lang=target_lang)
    except Exception as e:
        logging.error(f"Errore durante generate_response: {e}")
        return jsonify({"result": f"Errore interno: {e}"}), 500

    return jsonify({"result": result})

if __name__=="__main__":
    app.run()
    
