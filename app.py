from flask import Flask, request, jsonify, render_template
from transformers import AutoModelForCausalLM, AutoTokenizer
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from cache import SimpleCache
import difflib

app = Flask(__name__)

model_name = "EleutherAI/gpt-neo-125M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

cache = SimpleCache()
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
    """
    Restituisce gli indici delle linee modificate o aggiunte
    """
    original_lines = original_code.split("\n")
    fixed_lines = fixed_code.split("\n")
    diff = list(difflib.ndiff(original_lines, fixed_lines))
    modified_lines = []
    line_num = 0
    for d in diff:
        code = d[2:]
        if d.startswith("  "):
            line_num += 1
        elif d.startswith("+ "):
            modified_lines.append(line_num + 1)  # linea aggiunta/ modificata
            line_num += 1
        elif d.startswith("- "):
            # linea rimossa: non incrementiamo line_num
            continue
    return modified_lines

def generate_response(task, code, target_lang=None, max_length=1200):
    if code.count('\n') > MAX_LINES:
        return "Errore: codice troppo lungo (>10.000 righe)"
    
    if target_lang and target_lang.lower() not in SUPPORTED_LANGS:
        return f"Linguaggio non supportato: {target_lang}"

    key = cache.hash_input(task, code, target_lang)
    cached = cache.get(key)
    if cached:
        return cached

    # Prompt dinamico
    if task=="spiegazione":
        prompt = f"# Spiega il seguente codice passo passo in maniera chiara\n{code}"
        lang = "python"
        fix_lines = None
    elif task=="traduzione":
        prompt = f"# Traduci questo codice in {target_lang} mantenendo logica e funzionalità\n{code}"
        lang = target_lang
        fix_lines = None
    elif task=="fix":
        prompt = f"# Analizza e correggi errori nel codice seguente\n{code}"
        lang = "python"
    else:
        return "Task non valido"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_length=max_length,
        temperature=0.2,
        do_sample=True,
        top_p=0.9,
        top_k=50
    )

    result_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if task=="fix":
        # calcola linee modificate
        fix_lines = get_modified_lines(code, result_text)
    else:
        fix_lines = None

    html_result = color_code(result_text, language=lang, fix_lines=fix_lines)
    cache.set(key, html_result)
    return html_result

@app.route("/")
def index():
    return render_template("index.html", languages=SUPPORTED_LANGS)

@app.route("/api/code", methods=["POST"])
def code():
    data = request.json
    code_text = data.get("code","")
    task = data.get("task","")
    target_lang = data.get("target_lang",None)

    result = generate_response(code_text=code_text, task=task, target_lang=target_lang)
    return jsonify({"result": result})

if __name__=="__main__":
    app.run()
        
