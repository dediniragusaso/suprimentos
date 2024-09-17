import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, redirect, jsonify, Response, stream_with_context
from openai import RateLimitError, AuthenticationError, APIError
#Constantes
from logging import ERROR #Erro comum  
 
# #Funções
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
 
# from langchain_openai import ChatOpenAI
# from langchain.prompts import PromptTemplate
# from langchain.globals import set_debug
# import os
# from dotenv import load_dotenv
# from langchain_core.output_parsers import StrOutputParser
# from langchain.chains import ConversationChain
# from langchain.memory import ConversationBufferMemory
    
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

# carregando variáveis de ambiente
load_dotenv()
api_key = os.getenv("openai_api_key")
if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

llm = ChatOpenAI(
    model="gpt-4o-2024-08-06",
    temperature=1,
    api_key=api_key)

# variáveis globais
categorizador = os.open('./categorizador_prompt.txt')
viagens = os.open('./viagens.txt')
outros= os.open('./outros.txt')
erro = os.open('./erro.txt')
# Flask
# configurando o Flask
app = Flask(__name__)

# rotas
@app.route('/')
def index():
    return render_template('index.html')

# quando recarrega a página reseta a contagem de requisições - isso é relacionado ao histórico
@app.route("/limparTerminal", methods=["POST"])
def limparTerminal():
    global cont_requisicao
    reiniciar = request.json["recarregadoPorBotao"]
    if reiniciar == True:
        cont_requisicao = 0
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "success"})

# manda o contexto, pergunta para ChatGpt e retorna a resposta, atualiza também o histórico
@app.route("/submit", methods=["POST"])
def submit():

    try:
        global prompt_sistema_resposta_api
        historico = request.form['historico']
    
        pergunta_usuario = request.form['inputMessage']
        prompt_sistema_resposta_api = texto
                
        resposta = respostaApi(pergunta_usuario,prompt_sistema_resposta_api, historico)
        return Response(stream_with_context(resposta), content_type='text/plain')
        
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')

# função quando dá erro
def algo_ocorreu_de_errado():
    yield "Algo ocorreu de errado, tente novamente"

# função que retorna a resposta do chatGpt sobre a pergunta
def respostaApi(pergunta_usuario, prompt_sistema_resposta_api, historico):

    for arq in (os.listdir("./bases")):
        prompt_sistema_resposta_api += f"{arq}" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
    prompt_sistema_resposta_api += historico
    tempo_de_espera = 5
    tentativas = 0
    try:
        while tentativas <3:
            tentativas+=1
            
            try:
                prompt_sistema_resposta_api += "usuário: " + pergunta_usuario+ "\nia: "
                modelo = PromptTemplate(template=prompt_sistema_resposta_api, input_variables=["pergunta_usuario"])
                cadeia = modelo | llm | StrOutputParser()
                resposta = cadeia.invoke(input={"pergunta_usuario": pergunta_usuario})
            
                # print(prompt_sistema_resposta_api)
                print(resposta)
                yield resposta
                return 
            except RateLimitError as e:
                error(e)
                print(f"Erro de limite de taxa: {e}")
                time.sleep(tempo_de_espera)
                tempo_de_espera *=2
            except AuthenticationError as e:
                error(e)
                print(f"Erro de autentificação {e}")
            except APIError as e:
                error(e)
                print(f"Erro de API {e}")
                time.sleep(5)
            
    except Exception as e:
        error(e)
        yield str(e)

app.run(debug=True, port=5000)