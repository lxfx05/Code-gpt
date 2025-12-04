import logging
from flask import Flask, request, jsonify, render_template
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import difflib

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MAX_LINES = 10000
SUPPORTED_LANGS = ["php","c#","c++","lua","javascript","python","rust","kotlin","perl","scala","go"]

def chunk_code(code, max_lines=MAX_LINES):
    lines = code.split("\n")
    return ["\n".join(lines[i:i+max_lines]) for i in range(0, len(lines), max_lines)]

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

# Funzioni base senza AI
def explain_code(code):
    lines = code.split("\n")
    explanation = "\n".join([f"Linea {i+1}: {line[:50]}..." for i,line in enumerate(lines)])
    return explanation

def translate_code(code, target_lang):
    # Dummy translation: aggiunge commento di lingua
    return f"// Traduzione in {target_lang}\n{code}"

def fix_code(code):
    # Dummy fix: rimuove spazi extra
    fixed = "\n".join([line.rstrip() for line in code.split("\n")])
    return fixed

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

# Routes
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
    
