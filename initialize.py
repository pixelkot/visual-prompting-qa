import subprocess
import sys
from IPython.display import HTML

pip_package_list = [
    "lxml",
    "cssselect",
    "requests",
    "html5lib",
    "bs4",
    "tiktoken",
    "selenium",
    "datasets"
]

def setup():
    for package in pip_package_list:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def install_hugging_face_transformers():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "git+https://github.com/huggingface/transformers"])

def set_background(color):    
    script = (
        "var cell = this.closest('.jp-CodeCell');"
        "var editor = cell.querySelector('.jp-Editor');"
        "editor.style.background='{}';"
        "this.parentNode.removeChild(this)"
    ).format(color)
    
    display(HTML('<img src onerror="{}" style="display:none">'.format(script)))