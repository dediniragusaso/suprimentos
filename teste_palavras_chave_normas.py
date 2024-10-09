import os
import google.generativeai as genai
from dotenv import load_dotenv
from google.ai.generativelanguage_v1beta.types import content
import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
import re
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context
from logging import ERROR
# #Funções
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
from logging import getLogger
import tiktoken
import requests 
basicConfig(
    level = ERROR  , #Todas as informações com maior ou prioridade igual ao DEBUG serão armazenadas
    filename= "logs.log", #Onde serão armazenadas as informações
    filemode= "a", # Permissões do arquivo [se poderá editar, apenas ler ...]
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' # Formatação da informação
)
getLogger('openai').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

load_dotenv()
api_key = os.getenv("openai_api_key")
if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

openai.api_key = api_key

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


prompt_indicador = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()
for arq in os.listdir("./bases"):
    prompt_indicador += "\n\n" + open(f"./bases/{arq}", "r", encoding="utf8").read()

def algo_ocorreu_de_errado():
    yield "Algo ocorreu de errado, tente novamente"


encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/limparTerminal", methods=["POST"])
def limparTerminal():
    global cont_requisicao
    reiniciar = request.json["recarregadoPorBotao"]
    if reiniciar == True:
        cont_requisicao = 0
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "success"})
    

# Add user input to the prompt as a new message
user_input = "Como posso me cadastrar no paytrack"

# Create the model
def categorizador(prompt_usuario,historico):
    generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_schema": content.Schema(
        type = content.Type.OBJECT,
        properties = {
        "response": content.Schema(
            type = content.Type.STRING,
        ),
        },
    ),
    "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=prompt_indicador
    )

    chat_session = model.start_chat(
    history=[]
    )
    prompt=prompt_usuario+historico
    base = chat_session.send_message(prompt)
    return base






@app.route("/submit", methods=["POST"])

def submit():
    try:

    
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)

