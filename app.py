# funções
import time
import tiktoken
from dotenv import load_dotenv
import os
import re
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context, abort
import PyPDF2
import psycopg2

# configurações para os comportamentos dos logs
from logging import ERROR
from logging import basicConfig
from logging import error
from logging import getLogger

# para langchain
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain_core.exceptions import LangChainException, OutputParserException, TracerException
from langchain_core.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.prompts.chat import MessagesPlaceholder

# mongo
from mongo import *

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
    raise ValueError("Password não encontrada. Verifique se 'GEMINI_API_KEY' está definida no ambiente.")



# definindo prompts
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()

# definindo variáveis globais
respostaFinal = ""
client = Client(12345,"Teste","Teste","Teste")
chat = None


# definindo llm
llm = ChatOpenAI(api_key = api_key,
                 temperature=0.,
                 max_tokens=5000,
                 top_p=1,
                 frequency_penalty=0,
                 presence_penalty=0,
                 streaming=True,
                 model="gpt-4o-2024-08-06")
memory = ConversationBufferMemory(memory_key="history")
encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

app = Flask(__name__)

# Página Raíz
@app.route('/')
def index():
    global chat
    
    chat = Chat(client.id)
    chat.setChat()
        
    return render_template('index.html')

# Forms de Login
@app.route('/login', methods=["POST"])
def login():
    try:
        # verificação de senha
        password = request.json["password"]
        if password == correct_password:
            return jsonify({"status": "success"}),200
         
        else:
            return jsonify({"status": "error"}),401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Recarregar página
@app.route("/limparTerminal", methods=["POST"])
def limparTerminal():
    global cont_requisicao
    reiniciar = request.json["recarregadoPorBotao"]
    if reiniciar == True:
        cont_requisicao = 0
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "success"})
    
# Mensagem de erro para o usuário
def algo_ocorreu_de_errado(prompt_usuario):
    resposta =  "Ocorreu um erro. Por favor, tente novamente mais tarde ou entre em contato com um de nossos desenvolvedores pelo e-mail: gedaijef@gmail.com."
    chat.setPerguntaResposta(prompt_usuario, "erro", resposta)
    yield resposta
    
def procure_seu_gestor(prompt_usuario):
    resposta =  "Desculpe! Não consegui responder sua pergunta com as informações infornecidas. Procure seu gestor ou o RH mais próximo."
    chat.setPerguntaResposta(prompt_usuario, "erro", resposta)
    yield resposta

def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario):
    global custo
    
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
    
    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()

    prompt_100 += prompt_usuario
    
    # categoria
    categoria = llm.invoke([HumanMessage(content=prompt_100)]).content
    
    tokens_input = contar_tokens(prompt_100)/1000*0.0025
    tokens_output = contar_tokens(categoria)/1000*0.01
    custo = tokens_input + tokens_output
    chat.setValorCusto(custo)
    
    print(categoria)
    return categoria

def resposta (prompt_usuario, nome_arquivo):
    global respostaFinal
    
    prompt=escritor
    
    arquivoInput = (f"./pdfs_bases/procedimentos/{nome_arquivo}")
    pdf = open(arquivoInput, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf)
    total_paginas=len(pdf_reader.pages)
    for i in range (total_paginas):
        pagina = pdf_reader.pages[i]
        prompt+=pagina.extract_text()
    
    #prompt += historico
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

            # Gera a resposta do modelo
            resposta = llm.stream(prompt_template.format_prompt(history=memory.buffer_as_messages, prompt_usuario=prompt_usuario))

            print("Resposta feita com sucesso")
            
            output = ""
            for chunk in resposta:
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    output += text_chunk
                    yield text_chunk
                          
             # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs={"human": prompt_usuario}, outputs={"ai": output})    
            
            # salvar no banco
            tokens_input = (contar_tokens(prompt) + contar_tokens(prompt_usuario))/1000*0.0025
            tokens_output = contar_tokens(output)/1000*0.01
            custo = tokens_input + tokens_output
            chat.setValorCusto(custo)   
            
            chat.setPerguntaResposta(prompt_usuario,nome_arquivo[:-4],output)
       

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


def respostaErro (prompt_usuario):
    global respostaFinal
    
    prompt=erro
    
    # prompt += historico
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

            # Gera a resposta do modelo
            resposta = llm.stream(prompt_template.format_prompt(history=memory.buffer_as_messages, prompt_usuario=prompt_usuario))

            print("Resposta feita com sucesso")
            
            output = ""
            for chunk in resposta:
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    output += text_chunk
                    yield text_chunk

            
            # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs={"human": prompt_usuario}, outputs={"ai": output})
            
            # salvar no banco
            tokens_input = (contar_tokens(prompt) + contar_tokens(prompt_usuario))/1000*0.0025
            tokens_output = contar_tokens(output)/1000*0.01
            custo = tokens_input + tokens_output
            chat.setValorCusto(custo)  
            
            chat.setPerguntaResposta(prompt_usuario,"erro",output)

            
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
            
def substituidorNormas (resp, prompt_usuario, norma):
    prompt=normas
    prompt += resp
    
    arquivoInput = (f"./pdfs_bases/politicas/{norma}.pdf")
    pdf = open(arquivoInput, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf)
    total_paginas=len(pdf_reader.pages)
    for i in range (total_paginas):
        pagina = pdf_reader.pages[i]
        prompt+=pagina.extract_text()
    
    # prompt += historico    
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

            # Gera a resposta do modelo
            resposta = llm.stream(prompt_template.format_prompt(history=memory.buffer_as_messages, prompt_usuario=prompt_usuario))
            print("Resposta feita com sucesso")
            
            output = ""
            for chunk in resposta:
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    output += text_chunk
                    yield text_chunk

            # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs={"human": prompt_usuario}, outputs={"ai": output})
            
            # salvar no banco
            tokens_input = (contar_tokens(prompt) + contar_tokens(prompt_usuario))/1000*0.0025
            tokens_output = contar_tokens(output)/1000*0.01
            custo = tokens_input + tokens_output
            chat.setValorCusto(custo)  
            
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
for arq in (os.listdir("./pdfs_bases/procedimentos")):
        arquivos.append(arq) 
 

@app.route("/submit", methods=["POST"])
def submit():
    try:
    
        
        # historico = request.form['historico']
        print("P 1")
        # obter pergunta do usuário
        prompt_usuario = request.form['inputMessage']
        print("P 2")
        # Categorizar a pergunta
        base = categorizador(prompt_usuario)
        print("P 3")
        print(base)
       
        
        if chat.isErro():
            return Response(stream_with_context(procure_seu_gestor(prompt_usuario)),content_type='text/plain')
        

        if (base in arquivos):
            print("Base encontrada")
            
            resposta_sem_normas = "".join(resposta(prompt_usuario, base))
            respostaFinal = resposta_sem_normas

            string_sem_espacos = ''.join(
                parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas
            )
            
            # Verificar se há norma
            string_sem_espacos = ''.join(parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas)
            

            norma = re.search(r'(IN|M)-.{5,9}-[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                
                return Response(stream_with_context(substituidorNormas(string_sem_espacos, prompt_usuario,regra)), content_type='text/plain')
            
            else: 
                return Response(stream_with_context(respostaFinal), content_type='text/plain')
        else: 
            
            return Response(stream_with_context(respostaErro(prompt_usuario)), content_type='text/plain')
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado(prompt_usuario)), content_type='text/plain')

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
def handle_error(error):
    return render_template('error.html',error=error), error.code
    
app.run(debug=True, port=5000, host="0.0.0.0")

