#importação bibliotecas
import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
import re
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context
from logging import ERROR
from logging import basicConfig
from logging import error
from logging import getLogger
import tiktoken
import requests 
import psycopg2
import PyPDF2

basicConfig(
    level = ERROR  , 
    filename= "logs.log", 
    filemode= "a", 
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' 
)
getLogger('openai').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

load_dotenv()
api_key = os.getenv("openai_api_key")
correct_password = os.getenv("CORRECT_PASSWORD")
if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

openai.api_key = api_key

def inserir_banco(query):

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

    return conn, conn.cursor()

categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()
custo=0

encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

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
    


# função quando dá erro
def algo_ocorreu_de_errado():
    yield "Algo ocorreu de errado, tente novamente"


def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario, api_key):
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
    global custo
    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()

    custo+= (contar_tokens(prompt_100)/1000)*0.0025
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
    print(resposta.json())
    custo+=  (contar_tokens( resposta.json()["choices"][0]["message"]["content"])/1000)*0.01
    return resposta.json()["choices"][0]["message"]["content"]

       


def resposta (prompt_usuario, historico, nome_arquivo):
    prompt=escritor
    prompt += historico
    global custo
    arquivoInput = (f"./pdfs_bases/procedimentos/{nome_arquivo}")
    pdf = open(arquivoInput, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf)
    total_paginas=len(pdf_reader.pages)
    for i in range (total_paginas):
        pagina = pdf_reader.pages[i]
        prompt+=pagina.extract_text()
    print("Prompt de resposta")
    tentativas = 0
    tempo_de_espera = 5
    custo+= (contar_tokens(prompt)/1000)*0.0025
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        print(prompt)
        try:
            print(f"Iniciando a análise")
            resposta = openai.ChatCompletion.create(
                model = "gpt-4o-2024-08-06",
                messages = [
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": prompt_usuario
                    }
                ],
                temperature=0.,
                max_tokens=5000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True
            )
            
            print("Resposta feita com sucesso")
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            tokens_output = contar_tokens(output)
            custo+= (contar_tokens(output)/1000)*0.01
            print(f"Tokens de saída: {tokens_output}")               

            return
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2



def respostaErro (prompt_usuario, historico):
    prompt=erro
    prompt += historico
    tokens_input= contar_tokens(prompt)
    global custo
    print(f"Entrada:{tokens_input}")
    custo+= (contar_tokens(prompt)/1000)*0.0025
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        print("Prompt de erro")
        try:
            print(f"Iniciando a análise")
            resposta = openai.ChatCompletion.create(
                model = "gpt-4o-2024-08-06",
                messages = [
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": prompt_usuario
                    }
                ],
                temperature=0.,
                max_tokens=5000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True
            )
            
            print("Resposta feita com sucesso")
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            tokens_output = contar_tokens(output)
            custo+= (contar_tokens(output)/1000)*0.01
            print(f"Tokens de saída: {tokens_output}") 

            return
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2

def substituidorNormas (resp,historico,pergunta_usuario,norma):
    prompt=normas
    prompt += historico
    prompt += resp
    global custo
    arquivoInput = (f"./pdfs_bases/politicas/{norma}.pdf")
    pdf = open(arquivoInput, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf)
    total_paginas=len(pdf_reader.pages)
    for i in range (total_paginas):
        pagina = pdf_reader.pages[i]
        prompt+=pagina.extract_text()
    tokens_input= contar_tokens(prompt)
    custo+= (contar_tokens(prompt)/1000)*0.0025
    print(f"Entrada:{tokens_input}")
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")
            resposta = openai.ChatCompletion.create(
                model = "gpt-4o-2024-08-06",
                messages = [
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": pergunta_usuario
                    }
                ],
                temperature=0.,
                max_tokens=5000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True
            )
            
            print("Resposta feita com sucesso")
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            tokens_output = contar_tokens(output)
            custo+= (contar_tokens(output)/1000)*0.01
            print(f"Tokens de saída: {tokens_output}") 

            return
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2

arquivos=[]
for arq in (os.listdir("./pdfs_bases/procedimentos")):
        arquivos.append(arq) 


@app.route("/submit", methods=["POST"])
 
def submit():
    
    try:
    
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        global custo
        base = categorizador(pergunta_usuario, api_key)
        resposta_sem_normas = resposta(pergunta_usuario, historico, base)
        if (base in arquivos ):
            print("Base encontrada")
            print(base)
            string_sem_espacos = ''.join(parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas)
            norma = re.search(r'(IN|M)-.{5,9}-[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                print(regra)
                reais= custo * 5.60
                print(f"Custo: {reais} reais pela pergunta")
                return Response(stream_with_context(substituidorNormas(string_sem_espacos, historico, pergunta_usuario,regra,)), content_type='text/plain')
            
            else:
                print("nope")
                print(type(resposta_sem_normas))
                reais= custo * 5.60
                print(f"Custo: {reais} reais pela pergunta")
                return Response(stream_with_context(resposta(pergunta_usuario, historico, base)), content_type='text/plain')
            
           
     
        else: 
            reais= custo * 5.60
            print(f"Custo em dólares: {custo}")
            print(f"Custo: {reais} reais pela pergunta")
            return Response(stream_with_context(respostaErro(pergunta_usuario,historico)), content_type='text/plain')
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)