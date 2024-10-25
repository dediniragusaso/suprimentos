import openai
import time
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import google.generativeai as genai
import logging
import base64
import requests
import json
import psycopg2
import PyPDF2

# Logging configuration
logging.basicConfig(
    level=logging.ERROR,
    filename="logs.log",
    filemode="a",
    format='%(levelname)s->%(asctime)s->%(message)s->%(name)s'
)

logging.getLogger('openai').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Load environment variables
load_dotenv()
api_key = os.getenv("openai_api_key")
correct_password = os.getenv("CORRECT_PASSWORD")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
if not api_key:
    raise ValueError("API key not found. Make sure 'openai_api_key' is set in the environment.")

# Global variables
indicador = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor = open('./prompts/escritor_prompt.txt', "r", encoding="utf8").read()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=["POST"])
def login():
    try:
        password = request.json["password"]
        if password == correct_password:
            return jsonify({"status": "success"}),200
        else:
            return jsonify({"status": "error"}),401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}),500

@app.route("/limparTerminal", methods=["POST"])
def limparTerminal():
    global cont_requisicao
    reiniciar = request.json["recarregadoPorBotao"]
    if reiniciar == True:
        cont_requisicao = 0
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "success"})
    


def algo_ocorreu_de_errado():
    yield "Um erro ocorreu. Por favor, tente novamente ou entre em contato conosco se o problema persistir por meio do e-mail <a href='mailto:gedaijef@gmail.com' class='link_resposta'>gedaijef@gmail.com</a>"


def categorizador(prompt_usuario, api_key):
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
    global custo
    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o-2024-08-06",
        "messages": [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": prompt_usuario
            }
        ],
        "max_tokens": 1000,
        "seed": 42
    }
   

    payload["messages"][0]["content"] = prompt_100
    resposta = requests.post("https://api.openai.com/v1/chat/completions",headers=headers, json=payload)
    # print(resposta.json())

    return resposta.json()["choices"][0]["message"]["content"]

def imagem_para_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def respostaArquivo(prompt_usuario, arquivo, historico):
    if arquivo == "erro":
        yield "Please provide more details so I can assist you!"

    prompt = escritor
    prompt+= f"Nome do arquivo: {arquivo}"
    arquivoInput = (f"./pdfs_bases/procedimentos/{arquivo}")
    pdf = open(arquivoInput, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf)
    total_paginas=len(pdf_reader.pages)
    for i in range (total_paginas):
        pagina = pdf_reader.pages[i]
        prompt+=pagina.extract_text()
    prompt += historico

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    
    payload = {
        "model": "gpt-4o-2024-08-06",
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": [
                    {"type":"text",
                     "text":prompt_usuario
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "stream": True,
        "seed": 42
    }

    if os.path.exists(f"imagens_certa/{arquivo.replace('.pdf', '')}"):
        imagens = os.listdir(f"imagens_certa/{arquivo.replace('.pdf', '')}")
        
        imagens_map = map(lambda x: 
            {
            "type": "image_url",
            "image_url": {"url": "data:image/jpeg;base64,"+imagem_para_base64(f'imagens_certa/{arquivo.replace(".pdf", "")}/'+x)}
            },imagens)
        print(imagens_map)
        payload["messages"][1]["content"].extend(list(imagens_map))
        
        print(payload)

    try:
    
        resposta = requests.post("https://api.openai.com/v1/chat/completions",
                                 headers=headers, json=payload, stream=True)
        
        
        
        if resposta.status_code != 200:
            logging.error(f"Erro na requisição: {resposta.status_code} - {resposta.text}")
            return
        
        logging.info(f"Conexão bem-sucedida: {resposta.status_code}")


        
      
        for line in resposta.iter_lines(decode_unicode=True):
              
            if line.startswith('data: '):  
                line = line[len('data: '):]  
                    
                if line.strip() == '[DONE]':  
                    logging.info("Recebido [DONE], finalizando.")
                    break
                    
                try:   
                    chunk = json.loads(line)
                    logging.debug(f"Chunk recebido: {chunk}")  # Log detalhado do chunk recebido
                    delta = chunk.get('choices', [])[0].get('delta', {}).get('content', '')
                    if delta:
                        yield delta  
                        
                except json.JSONDecodeError as e:
                        logging.error(f"Erro ao decodificar JSON: {e} - Linha: {line}")
                        continue  
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição: {e}") 

   
  

@app.route("/submit", methods=["POST"])
def submit():
    try:
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        arquivo = categorizador(pergunta_usuario,api_key)
        
        return Response(stream_with_context(respostaArquivo(pergunta_usuario, arquivo, historico)), content_type='text/plain')

    except Exception as e:
        logging.error(e)


app.run(debug=True, port=5000)








