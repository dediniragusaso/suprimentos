import time
import tiktoken
from dotenv import load_dotenv
import os
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context
from logging import ERROR

#Funções
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
from logging import getLogger
import tiktoken

# Langchain
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.exceptions import LangChainException, OutputParserException, TracerException
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import pprint

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

# Configure o OpenAI
llm = ChatOpenAI(api_key=api_key,
                 model = "gpt-4o-2024-08-06",
                 temperature = 0.7,
                 max_tokens = 1000,
                 top_p = 1,
                 frequency_penalty = 0,
                 presence_penalty = 0,
                 streaming = True)

# variáveis globais
# categorizador=open('./categorizador_prompt.txt',"r",encoding="utf8").read() 
# viagens = open('./viagens.txt',"r",encoding="utf8").read() 
# outros= open('./outros.txt',"r",encoding="utf8").read() 
# erro = open('./erro.txt',"r",encoding="utf8").read() 

# variáveis globais
indicador= open('./prompts/indicador_prompt.txt',"r",encoding="utf8").read() 
escritor = open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 

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
    yield "Ocorreu um erro. Por favor, tente novamente mais tarde ou entre em contato com um de nossos desenvolvedores pelo e-mail: gedaijef@gmail.com."




def identificaArquivo(prompt_usuario):
    prompt = indicador
    for arq in (os.listdir("./bases")):
        prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        try:
            
            # preparar o prompt
            prompt += "human: {input}\n"
            prompt += "ai: "
            
            modelo = PromptTemplate(template=prompt, input_variables=["input"])
            cadeia = modelo | llm | StrOutputParser()
            resposta = cadeia.invoke(input = {prompt_usuario})
            
            print("Análise realizada com sucesso")
            return resposta
        except TracerException as e:
            print(f"Erro de rastreamento: {e}")
        except OutputParserException as e:
            print(f"Erro ao parser saída: {e}")
            time.sleep(5)
        except LangChainException as e:
            print(f"Erro da LangChain: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2
        except Exception as e:
            # Captura outras exceções genéricas
            print(f"Ocorreu um erro inesperado: {e}")

def respostaArquivo(prompt_usuario, arquivo, historico):
    # Verifica se o arquivo está com erro
    if arquivo == "erro":
        yield "Por favor, informe mais detalhes para que eu possa te ajudar."
        return

    # Carrega o conteúdo do arquivo especificado na base
    prompt = escritor
    prompt += "\n\n" + open(f"./bases/{arquivo}", "r", encoding="utf8").read()
    prompt += historico  # Adiciona o histórico ao prompt

    tentativas = 0
    tempo_de_espera = 5  # Tempo inicial de espera entre tentativas

    while tentativas < 3:  # Tenta até 3 vezes em caso de erro
        tentativas += 1
        print(f"Tentativa {tentativas}")
        try:
            print("Iniciando a análise")

            # Preparar o prompt para o modelo
            prompt += "human: {input}\n"
            prompt += "ai: "
            
            modelo = PromptTemplate(template=prompt, input_variables=["input"])
            cadeia = modelo | llm | StrOutputParser()

            # Usar o streaming para capturar a resposta e retornar cada chunk imediatamente
            print("Resposta feita com sucesso")
            for chunk in cadeia.stream({"input": prompt_usuario}):
                yield chunk
            return

        except TracerException as e:
            print(f"Erro de rastreamento: {e}")
        except OutputParserException as e:
            print(f"Erro ao parser saída: {e}")
            time.sleep(tempo_de_espera)
        except LangChainException as e:
            print(f"Erro da LangChain: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *= 2  # Dobrar o tempo de espera a cada tentativa
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")

    # Caso todas as tentativas falhem, pode-se retornar uma mensagem de erro
    yield "Erro ao processar a resposta após múltiplas tentativas."

@app.route("/submit", methods=["POST"])
def submit():
    
    try:
        # Obter o histórico e a pergunta do usuário a partir do formulário
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        
        # Identificar o arquivo com base na pergunta
        arquivo = identificaArquivo(pergunta_usuario)
        print("tipo: " + arquivo)
        
        # Contar os tokens no escritor
        tokens = encoding.encode(escritor)
        token_count = len(tokens)
        print(f"Tokens do prompt: {token_count}")
    
        # Retornar a resposta como um stream
        return Response(stream_with_context(respostaArquivo(pergunta_usuario, arquivo, historico)), content_type='text/plain')
    except Exception as e:
        error(e)
        print(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)