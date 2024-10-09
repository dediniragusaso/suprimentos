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
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory

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
    yield "Ocorreu um erro. Por favor, tente novamente mais tarde ou entre em contato com um de nossos desenvolvedores pelo e-mail: <a emailto:gedaijef@gmail.com>gedaijef@gmail.com</a>."

def identificaArquivo(prompt_usuario):
    prompt = indicador
    for arq in (os.listdir("./bases")):
        prompt += f"\n\n{arq}"
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
            print(resposta)
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


def respostaArquivo (prompt_usuario, arquivo, historico):
    # for arq in (os.listdir("./bases")):
    #     prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
    if arquivo == "erro":
        yield "Por favor, informe mais detalhes para que eu possa te ajudar."
        return

    # Carrega o conteúdo do arquivo especificado na base
    prompt = escritor
    prompt += "\n\n" + open(f"./bases/{arquivo}", "r", encoding="utf8").read()
    prompt += historico  # Adiciona o histórico ao prompt
    
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")
            
            # preparar o prompt
            prompt += "human: {input}\n"
            prompt += "ai: "
            
            modelo = PromptTemplate(template=prompt, input_variables=["input"])
            cadeia = modelo | llm | StrOutputParser()
            cadeia = cadeia.invoke(input=prompt_usuario)
            # resposta_stream = cadeia.invoke(input=prompt_usuario)
            
            for chunk in llm.stream(cadeia):
                print(chunk)
                yield chunk

            print("Resposta feita com sucesso")
            return
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
            print(f"Ocorreu um erro inesperado: {e}")


# def respostaViagens (prompt_usuario, historico):
#     prompt=viagens
#     for arq in (os.listdir("./basesViagens")):
#         prompt += "\n\n" + open(f"./basesViagens/{arq}","r",encoding="utf8").read() 
    
#     prompt += historico
    
#     tentativas = 0
#     tempo_de_espera = 5
#     while tentativas <3:
#         tentativas+=1
#         print(f"Tentativa {tentativas}")
#         print(prompt)
#         try:
#             print(f"Iniciando a análise")
            
#             # preparar o prompt
#             prompt += "human: {input}\n"
#             prompt += "ai: "
            
#             modelo = PromptTemplate(template=prompt, input_variables=["input"])
#             cadeia = modelo | llm | StrOutputParser()
#             resposta_stream = cadeia.invoke(input=prompt_usuario)
            
#             print("Resposta feita com sucesso")
#             print(resposta_stream)
#             return resposta_stream
#         except TracerException as e:
#             print(f"Erro de rastreamento: {e}")
#         except OutputParserException as e:
#             print(f"Erro ao parser saída: {e}")
#             time.sleep(5)
#         except LangChainException as e:
#             print(f"Erro da LangChain: {e}")
#             time.sleep(tempo_de_espera)
#             tempo_de_espera *=2
#         except Exception as e:
#             print(f"Ocorreu um erro inesperado: {e}")


# def respostaOutros (prompt_usuario, historico):
#     prompt=outros
#     for arq in (os.listdir("./bases")):
#         prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
#     prompt += historico
    
#     tentativas = 0
#     tempo_de_espera = 5
#     while tentativas <3:
#         tentativas+=1
#         print(f"Tentativa {tentativas}")
#         try:
#             print(f"Iniciando a análise")
            
#             # preparar o prompt
#             prompt += "human: {input}\n"
#             prompt += "ai: "
            
#             modelo = PromptTemplate(template=prompt, input_variables=["input"])
#             cadeia = modelo | llm | StrOutputParser()
#             resposta_stream = cadeia.invoke(input=prompt_usuario)
            
#             print("Resposta feita com sucesso")
#             print(resposta_stream)
#             return resposta_stream
#         except TracerException as e:
#             print(f"Erro de rastreamento: {e}")
#         except OutputParserException as e:
#             print(f"Erro ao parser saída: {e}")
#             time.sleep(5)
#         except LangChainException as e:
#             print(f"Erro da LangChain: {e}")
#             time.sleep(tempo_de_espera)
#             tempo_de_espera *=2
#         except Exception as e:
#             print(f"Ocorreu um erro inesperado: {e}")


# def respostaErro (prompt_usuario, historico):
#     prompt=erro
#     prompt += historico
    
#     tentativas = 0
#     tempo_de_espera = 5
#     while tentativas <3:
#         tentativas+=1
#         print(f"Tentativa {tentativas}")
#         try:
#             print(f"Iniciando a análise")
            
#             # Preparar os prompts
#             prompt += "human: {input}\n"
#             prompt += "ai: "
            
#             modelo = PromptTemplate(template=prompt, input_variables=["input"])
#             cadeia = modelo | llm | StrOutputParser()
#             resposta_stream = cadeia.invoke(input=prompt_usuario)
            
#             print(resposta_stream)
#             print("Resposta feita com sucesso")
#             return resposta_stream
#         except TracerException as e:
#             print(f"Erro de rastreamento: {e}")
#         except OutputParserException as e:
#             print(f"Erro ao parser saída: {e}")
#             time.sleep(5)
#         except LangChainException as e:
#             print(f"Erro da LangChain: {e}")
#             time.sleep(tempo_de_espera)
#             tempo_de_espera *=2
#         except Exception as e:
#             print(f"Ocorreu um erro inesperado: {e}")


@app.route("/submit", methods=["POST"])
def submit():
    
    try:
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        arquivo = identificaArquivo(pergunta_usuario)
        print("tipo: " + arquivo)
        tokens = encoding.encode(escritor)
        token_count = len(tokens)
        print(f"Tokens do prompt: {token_count}")
        
        
        # if (tipo == "Viagens"):
        #     tokens = encoding.encode(viagens)
        #     token_count = len(tokens)
        #     print(f"Tokens do prompt: {token_count}")
            
        #     return Response(stream_with_context(respostaViagens(pergunta_usuario, historico)), content_type='text/plain')
        # elif (tipo== "Outros"):
        #     tokens = encoding.encode(outros)
        #     token_count = len(tokens)
        #     print(f"Tokens do prompt: {token_count}")
        #     return Response(stream_with_context(respostaOutros(pergunta_usuario, historico)), content_type='text/plain')
            
        # elif (tipo == "Nenhum"):
        #     tokens = encoding.encode(erro)
        #     token_count = len(tokens)
        #     print(f"Tokens do prompt: {token_count}")
        #     return Response(stream_with_context(respostaErro(pergunta_usuario, historico)), content_type='text/plain')
        
        # else: 
        #     print("Erro")
        
        return Response(stream_with_context(respostaArquivo(pergunta_usuario,arquivo, historico)), content_type='text/plain')
    except Exception as e:
        error(e)
        print(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)