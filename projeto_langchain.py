# funções
import time
import tiktoken
from dotenv import load_dotenv
import os
import re
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context

# configurações para os comportamentos dos logs
from logging import ERROR
from logging import basicConfig
from logging import error
from logging import getLogger
import tiktoken
import psycopg2

# langchain
from langchain_openai.llms import OpenAI
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.chains.conversation.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.exceptions import LangChainException, OutputParserException, TracerException 
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts.chat import MessagesPlaceholder
# from langchain_community.document_loaders import PyPDFLoader

basicConfig(
    level = ERROR  , #Todas as informações com maior ou prioridade igual ao DEBUG serão armazenadas
    filename= "logs.log", #Onde serão armazenadas as informações
    filemode= "a", # Permissões do arquivo [se poderá editar, apenas ler ...]
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' # Formatação da informação
)
getLogger('langchain').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
correct_password = os.getenv("CORRECT_PASSWORD")

if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'OPENAI_API_KEY' está definida no ambiente.")

if not correct_password:
    raise ValueError("Chave API não encontrada. Verifique se 'GEMINI_API_KEY' está definida no ambiente.")

# definindo llm
llm = ChatOpenAI(api_key = api_key,
                 temperature=0.,
                 max_tokens=5000,
                 top_p=1,
                 frequency_penalty=0,
                 presence_penalty=0,
                 streaming=True,
                 model="gpt-4o-2024-08-06")

def inserir_banco(query):

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()

# variáveis globais
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()

# Inicializar a memória de conversação
memory = ConversationBufferMemory(memory_key="history", return_messages=True)

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
    yield "Ocorreu um erro. Por favor, tente novamente mais tarde ou entre em contato com um de nossos desenvolvedores pelo e-mail: gedaijef@gmail.com."

def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario):
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()

    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()
        
    prompt_100 += prompt_usuario
         
    categoria = llm.invoke([HumanMessage(content=prompt_100)])
    print("tipo: " + categoria.content)
    
    return categoria.content


def resposta (prompt_usuario, historico, nome_arquivo):
    prompt=escritor
    prompt+= open(f"./bases/{nome_arquivo}","r",encoding="utf8").read()
    #prompt += historico
    
    tentativas = 0
    tempo_de_espera = 5
    tokens_input = contar_tokens(prompt)
    print(f"Entrada: {tokens_input}")
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")

            # Criar o template de prompt baseado em chat
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template("{prompt_usuario}")
            ])

            # Gera a resposta do modelo
            resposta = llm.predict(prompt_template.format_prompt(history=memory.load_memory_variables({}), prompt_usuario=prompt_usuario))

            # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs=[HumanMessage(content=prompt_usuario), AIMessage(content="")], outputs=[HumanMessage(content=prompt_usuario), AIMessage(content=resposta)])

            output = ""
            for chunk in resposta:
                output += chunk
            
            print("Resposta feita com sucesso")
            print(resposta)
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            tokens_output = contar_tokens(output)
            print(f"Tokens de saída: {tokens_output}")               

            return
        except TracerException as e:
            print(f"Erro no  módulo de rastreadores: {e}")
        except OutputParserException as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except LangChainException as e:
            print(f"Erro geral: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2



def respostaErro (prompt_usuario, historico):
    prompt=erro
    # prompt += historico
    tokens_input= contar_tokens(prompt)
    print(f"Entrada:{tokens_input}")
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")
            
            # Criar o template de prompt baseado em chat
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template("{prompt_usuario}")
            ])

            # Gerar a resposta do modelo de linguagem
            resposta = llm.invoke(prompt_template.format_prompt(history=memory.load_memory_variables({})["history"], prompt_usuario=prompt_usuario))
            
            print("Resposta feita com sucesso")
            print(resposta)
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            tokens_output = contar_tokens(output)
            print(f"Tokens de saída: {tokens_output}") 

            return
        except TracerException as e:
            print(f"Erro no  módulo de rastreadores: {e}")
        except OutputParserException as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except LangChainException as e:
            print(f"Erro geral: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2

def substituidorNormas (resp,historico,pergunta_usuario,norma):
    prompt=normas
    # prompt += historico
    prompt += ''.join(resp)  # junta todas as strings geradas por 'resp'
    prompt += open(f"./bases_normas/{norma}.txt","r",encoding="utf8").read() 
    tokens_input= contar_tokens(prompt)
    print(f"Entrada:{tokens_input}")
    tentativas = 0
    tempo_de_espera = 5
    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            print(f"Iniciando a análise")
            
            # Criar o template de prompt baseado em chat
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template("{pergunta_usuario}")
            ])

            # Gerar a resposta do modelo de linguagem
            resposta = llm.predict(prompt_template.format_prompt(history=memory.load_memory_variables({})["history"], pergunta_usuario=pergunta_usuario))
            
            print("Resposta feita com sucesso")
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            tokens_output = contar_tokens(output)
            print(f"Tokens de saída: {tokens_output}") 

            return
        except TracerException as e:
            print(f"Erro no  módulo de rastreadores: {e}")
        except OutputParserException as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except LangChainException as e:
            print(f"Erro geral: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2

arquivos=[]
for arq in (os.listdir("./bases")):
        arquivos.append(arq) 



@app.route("/submit", methods=["POST"])
 
def submit():
    
    try:
    
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
    
        base = categorizador(pergunta_usuario)
        resposta_sem_normas = resposta(pergunta_usuario, historico, base)
        if ( base and base in arquivos ):
            print("Base encontrada")
            string_sem_espacos = ''.join(parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas)

            norma = re.search(r'(IN|M)-.*[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                print(regra)
                
                return Response(stream_with_context(substituidorNormas(resposta_sem_normas, historico, pergunta_usuario,regra,)), content_type='text/plain')
            
            else:
                print("nope")
                print(type(resposta_sem_normas))
            
                return Response(stream_with_context(resposta(pergunta_usuario, historico, base)), content_type='text/plain')
            
           
     
        else: 
            return Response(stream_with_context(respostaErro(pergunta_usuario,historico)), content_type='text/plain')
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000, host="0.0.0.0")