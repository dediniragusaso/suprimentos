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
                 max_tokens = 100,
                 top_p = 1,
                 frequency_penalty = 0,
                 presence_penalty = 0,
                 streaming = True)

# variáveis globais
categorizador=open('./categorizador_prompt.txt',"r",encoding="utf8").read() 
viagens = open('./viagens.txt',"r",encoding="utf8").read() 
outros= open('./outros.txt',"r",encoding="utf8").read() 
erro = open('./erro.txt',"r",encoding="utf8").read() 

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
            modelo = PromptTemplate(template=prompt, input_variables=[""])
    cadeia = modelo | llm | StrOutputParser()
    resposta = cadeia.invoke(input= {})
            
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





def respostaViagens (prompt_usuario, historico):
    prompt=viagens
    for arq in (os.listdir("./basesViagens")):
        prompt += "\n\n" + open(f"./basesViagens/{arq}","r",encoding="utf8").read() 
    
    prompt += historico
    
    # Preparar os prompts
    mensagens = ChatPromptTemplate.from_messages([
        {"role": "system", "content": prompt},
        {"role": "user", "content": prompt_usuario}
    ])
    
    llm_chain = mensagens | llm
    
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        print(prompt)
        try:
            print(f"Iniciando a análise")
            resposta_stream = llm_chain.astream()
            
            print("Resposta feita com sucesso")
            for chunk in resposta_stream:
                # Verifica se o chunk contém as informações esperadas
                if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                    text = chunk['choices'][0]['delta']['content']
                    if text:
                        print(text, end='', flush=True)
                        yield text

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


def respostaOutros (prompt_usuario, historico):
    prompt=outros
    for arq in (os.listdir("./bases")):
        prompt += "\n\n" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
    prompt += historico
    
    # Preparar os prompts
    mensagens = ChatPromptTemplate.from_messages([
        {"role": "system", "content": prompt},
        {"role": "user", "content": prompt_usuario}
    ])
    
    llm_chain = mensagens | llm
    
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")
            resposta_stream = llm_chain.astream()
            
            print("Resposta feita com sucesso")
            for chunk in resposta_stream:
                # Verifica se o chunk contém as informações esperadas
                if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                    text = chunk['choices'][0]['delta']['content']
                    if text:
                        print(text, end='', flush=True)
                        yield text

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


def respostaErro (prompt_usuario, historico):
    prompt=outros
    prompt += historico
    
    # Preparar os prompts
    mensagens = ChatPromptTemplate.from_messages([
        {"role": "system", "content": prompt},
        {"role": "user", "content": prompt_usuario}
    ])
    
    llm_chain = mensagens | llm 
    
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")
            resposta_stream = llm_chain.astream()
            
            print("Resposta feita com sucesso")
            for chunk in resposta_stream:
                # Verifica se o chunk contém as informações esperadas
                if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                    text = chunk['choices'][0]['delta']['content']
                    if text:
                        print(text, end='', flush=True)
                        yield text

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
        print(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)