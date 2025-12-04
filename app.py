import os
import logging
import requests
from flask import Flask, request, jsonify, render_template
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import difflib
from dotenv import load_dotenv

# Carica .env.local in locale
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configurazione generale
MAX_LINES = 10000
SUPPORTED_LANGS = ["php","c#","c++","lua","javascript","python","rust","kotlin","perl","scala","go"]

# API HuggingFace
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
HUGGINGFACE_URL = "https://api-inference.huggingface.co/models/Qwen-3-4B-GGUF"
HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

# Funzioni helper
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
    html = f'<
    
