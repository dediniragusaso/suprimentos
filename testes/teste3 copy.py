import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context
from logging import ERROR
# #Funções
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
from logging import getLogger

basicConfig(
    level = ERROR  , #Todas as informações com maior ou prioridade igual ao DEBUG serão armazenadas
    filename= "logs.log", #Onde serão armazenadas as informações
    filemode= "a", # Permissões do arquivo [se poderá editar, apenas ler ...]
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' # Formatação da informação
)

# Configuração explícita dos loggers das bibliotecas
getLogger('openai').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

load_dotenv()
api_key = os.getenv("openai_api_key")
if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

openai.api_key = api_key

# variáveis globais
categorizador=open('./categorizador_prompt.txt',"r",encoding="utf8").read() 
viagens = open('./viagens.txt',"r",encoding="utf8").read() 
outros= open('./outros.txt',"r",encoding="utf8").read() 
erro = open('./erro.txt',"r",encoding="utf8").read() 
cont_requisicao = 0
lista_historico = ["","",""]

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
    


# função quando dá erro
def algo_ocorreu_de_errado():
    yield "Algo ocorreu de errado, tente novamente"




def identificaArquivo(prompt_usuario):
    prompt= categorizador
    for arq in (os.listdir("projeto_chat_suprimentos/basesViagens")):
        prompt += "\n\n" + open(f"projeto_chat_suprimentos/basesViagens/{arq}","r",encoding="utf8").read() 
    for arq in (os.listdir("projeto_chat_suprimentos/bases")):
        prompt += "\n\n" + open(f"projeto_chat_suprimentos/bases/{arq}","r",encoding="utf8").read() 

    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        try:
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
                temperature=0.7,
                max_tokens=100,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            
            print("Análise realizada com sucesso")
            return Response(stream_with_context(resposta.choices[0].message.content), content_type='text/plain')
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2





def respostaViagens (prompt_usuario):
    prompt=viagens
    for arq in (os.listdir("./basesViagens")):
        prompt += "\n\n" + open(f"./basesViagens/{arq}","r",encoding="utf8").read() 
    
    tentativas = 0
    tempo_de_espera = 5
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
            )
            
            print("Resposta feita com sucesso")
            print(resposta.choices[0].message.content)
            return resposta.choices[0].message.content
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2


def respostaOutros (prompt_usuario):
    prompt=outros
    for arq in (os.listdir("./bases")):
        prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
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
                        "content": prompt_usuario
                    }
                ],
                temperature=0.,
                max_tokens=5000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            
            print("Resposta feita com sucesso")
            return resposta.choices[0].message.content
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2


def respostaErro (prompt_usuario):
    prompt=outros
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
                        "content": prompt_usuario
                    }
                ],
                temperature=0.,
                max_tokens=5000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            
            print("Resposta feita com sucesso")
            return resposta.choices[0].message.content
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2


@app.route("/submit", methods=["POST"])
def submit():
    
    try:
        historico = request.form['historico']
    
        pergunta_usuario = request.form['inputMessage']
        identificaArquivo(pergunta_usuario)
        tipo = identificaArquivo(pergunta_usuario)
        print(tipo)
        if (tipo == "Viagens"):
            resposta = respostaViagens(pergunta_usuario)
            
        elif (tipo== "Outros"):
            resposta =respostaOutros(pergunta_usuario)
        elif (tipo == "Nenhum"):
            resposta =respostaErro(pergunta_usuario)
        else: 
            print("Erro")
        
        
        return Response(stream_with_context(resposta), content_type='text/plain')
        
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    

def submit():
    
    try:
        global cont_requisicao
        global prompt_sistema_resposta_api
        global lista_historico
    
        pergunta_usuario = request.form['inputMessage']
        identificaArquivo(pergunta_usuario)
        tipo = identificaArquivo(pergunta_usuario)
        print(tipo)
        if (tipo == "Viagens"):
            resposta = respostaViagens(pergunta_usuario)
            
        elif (tipo== "Outros"):
            resposta =respostaOutros(pergunta_usuario)
        elif (tipo == "Nenhum"):
            resposta =respostaErro(pergunta_usuario)
        else: 
            print("Erro")
        
        
        return Response(stream_with_context(resposta), content_type='text/plain')
        
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)
