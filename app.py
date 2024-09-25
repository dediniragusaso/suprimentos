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
import tiktoken

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

# variáveis globais
categorizador=open('./prompts/categorizador_prompt.txt',"r",encoding="utf8").read() 
viagens = open('./prompts/viagens.txt',"r",encoding="utf8").read() 
outros= open('./prompts/outros.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 

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
    


# função quando dá erro
def algo_ocorreu_de_errado():
    yield "Algo ocorreu de errado, tente novamente"




def identificaArquivo(prompt_usuario):
    prompt= categorizador
    for arq in (os.listdir("./basesViagens")):
        prompt += "\n\n" + open(f"./basesViagens/{arq}","r",encoding="utf8").read() 
    for arq in (os.listdir("./bases")):
        prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 

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
                presence_penalty=0
            )
            
            print("Análise realizada com sucesso")
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





def respostaViagens (prompt_usuario, historico):
    prompt=viagens
    for arq in (os.listdir("./basesViagens")):
        prompt += "\n\n" + open(f"./basesViagens/{arq}","r",encoding="utf8").read() 
    
    prompt += historico
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
                stream=True
            )
            
            print("Resposta feita com sucesso")
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            print(text, end="")
                            yield text

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


def respostaOutros (prompt_usuario, historico):
    prompt=outros
    for arq in (os.listdir("./bases")):
        prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
    prompt += historico
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
                stream=True
            )
            
            print("Resposta feita com sucesso")
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            print(text, end="")
                            yield text

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
    prompt=outros
    prompt += historico
    
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
                stream=True
            )
            
            print("Resposta feita com sucesso")
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            print(text, end="")
                            yield text

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


@app.route("/submit", methods=["POST"])
def submit():
    
    try:
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        tipo = identificaArquivo(pergunta_usuario)
        print("tipo: " + tipo)
        if (tipo == "Viagens"):
            tokens = encoding.encode(viagens)
            token_count = len(tokens)
            print(f"Tokens do prompt: {token_count}")
            
            return Response(stream_with_context(respostaViagens(pergunta_usuario, historico)), content_type='text/plain')
        elif (tipo== "Outros"):
            tokens = encoding.encode(outros)
            token_count = len(tokens)
            print(f"Tokens do prompt: {token_count}")
            return Response(stream_with_context(respostaOutros(pergunta_usuario, historico)), content_type='text/plain')
            
        elif (tipo == "Nenhum"):
            tokens = encoding.encode(erro)
            token_count = len(tokens)
            print(f"Tokens do prompt: {token_count}")
            return Response(stream_with_context(respostaErro(pergunta_usuario, historico)), content_type='text/plain')
        
        else: 
            print("Erro")
    except Exception as e:
        
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)