import os
import openai
from dotenv import load_dotenv
import time
from flask import Flask, render_template, request, redirect, jsonify, Response, stream_with_context
from flask_cors import CORS, cross_origin

load_dotenv()
openai.api_key = os.getenv("openai_api_key")

# Flask
app = Flask(__name__)

@app.route('/')
@cross_origin(origin='https://institutojef.org.br')
def index():
    return render_template('index.html')

app.run(debug=True, port=5000)

# Funções de identificação de arquivos

def identificaArquivo(prompt_usuario):
    prompt_sistema= '''
'''
