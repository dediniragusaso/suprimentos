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

# definindo llm
llm = ChatOpenAI(api_key = api_key,
                 temperature=0.,
                 max_tokens=5000,
                 top_p=1,
                 frequency_penalty=0,
                 presence_penalty=0,
                 streaming=True,
                 model="gpt-4o-2024-08-06")

# Método para conectar no banco
def conexao_banco():
    try:
        db_link = os.getenv("DB_LINK")
        if not db_link:
            raise ValueError("Variável de ambiente DB_LINK não definida.")
        
        # Adicionar parâmetros de SSL
        conn = psycopg2.connect(
            db_link,
            sslmode='require',
            sslrootcert='/etc/secrets/ca.pem'
        )
        print("Conexão feita com sucesso!")
        return conn
    except Exception as e:
        print(f"Erro ao conectar no banco de dados: {e}")
    

# variáveis globais
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()
chat_id = 0
custo = 0
respostaFinal = ""

# Inicializar a memória de conversação
memory = ConversationBufferMemory(memory_key="history")

encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

app = Flask(__name__)

# Página Raíz
@app.route('/')
def index():
    global chat_id
    
    conn = None
    cursor = None
    try:
        conn = conexao_banco()
        cursor = conn.cursor()
        
        cursor.execute("CALL prc_inserir_chat(%s)", (None,))
        chat_id = cursor.fetchone()[0]
        conn.commit()       
        
    except Exception as e:
        abort(500)
        conn.rollback()
        print(f"Erro: {e}")
    else:
        cursor.close()
        conn.close()
        
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
def algo_ocorreu_de_errado():
    yield "Ocorreu um erro. Por favor, tente novamente mais tarde ou entre em contato com um de nossos desenvolvedores pelo e-mail: gedaijef@gmail.com."

def procure_seu_gestor():
    yield "Desculpe! Não consegui responder sua pergunta com as informações infornecidas. Procure seu gestor ou o RH mais próximo."


def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario):
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
    global custo
    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()

    prompt_100 += prompt_usuario
    
    # tokens do input
    tokens_input = contar_tokens(prompt_100)
    
    custo = tokens_input*0.0025
    
    # categoria
    categoria = llm.invoke([HumanMessage(content=prompt_100)])
    print("tipo: " + categoria.content)
    
    # tokens do retorno da api
    output = categoria.content     
    tokens_output = contar_tokens(output)
    custo += tokens_output*0.01
    
    # custo do chat
    chat_custo = (tokens_input/1000*0.0025) + (tokens_output/1000*0.01)

  
    
    try:
        conn = conexao_banco()
        cursor = conn.cursor()
    
        # Associar o procedimento ao chat
        cursor.execute("CALL prc_procedimento_chat(%s, %s, %s)",(chat_id,output,prompt_usuario))
        
        # Atualizar o custo do chat
        cursor.execute("SELECT fnc_atualizar_controle(%s,%s,%s,%s)", (tokens_input, tokens_output, chat_custo, chat_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro: {e}")
    else:
        cursor.close()
        conn.close()
    
    return categoria.content


def resposta (prompt_usuario, nome_arquivo):
    global chat_id
    global custo
    global respostaFinal
    
    prompt=escritor
    nome = nome_arquivo.replace(".txt", ".pdf")
    arquivoInput = (f"./pdfs_bases/procedimentos/{nome}")
    pdf = open(arquivoInput, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf)
    total_paginas=len(pdf_reader.pages)
    for i in range (total_paginas):
        pagina = pdf_reader.pages[i]
        prompt+=pagina.extract_text()
    #prompt += historico
    
    tentativas = 0
    tempo_de_espera = 5
    
    # tokens do input
    tokens_input = contar_tokens(prompt)
    tokens_input += contar_tokens(prompt_usuario)
    custo += tokens_input*0.0025
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
            resposta = llm.stream(prompt_template.format_prompt(history=memory.buffer_as_messages, prompt_usuario=prompt_usuario))

            print("Resposta feita com sucesso")
            
            output = ""
            for chunk in resposta:
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    output += text_chunk
                    yield text_chunk
                    
            # tokens do retorno da api
            tokens_output = contar_tokens(output)
            respostaFinal = output
            custo += tokens_output*0.01
            print(tokens_output) 
            
            # valor do chat
            chat_custo = (tokens_input/1000*0.0025) + (tokens_output/1000*0.01)
            print(chat_custo)
            
             # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs={"human": prompt_usuario}, outputs={"ai": output})              
            
            # salva no banco
            try:
                conn = conexao_banco()
                cursor = conn.cursor()
            
                #Atualizar custo do chat
                cursor.execute("SELECT fnc_atualizar_controle(%s,%s,%s,%s)", (tokens_input, tokens_output, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            else:
                cursor.close()
                conn.close()     

            
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
    global custo
    global respostaFinal
    
    prompt=erro
    # prompt += historico
    
    # tokens de entrada
    tokens_input = contar_tokens(prompt)
    tokens_input += contar_tokens(prompt_usuario)
    custo += tokens_input*0.0025
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

            # Gera a resposta do modelo
            resposta = llm.stream(prompt_template.format_prompt(history=memory.buffer_as_messages, prompt_usuario=prompt_usuario))

            print("Resposta feita com sucesso")
            
            output = ""
            for chunk in resposta:
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    output += text_chunk
                    yield text_chunk

            # tokens do retorno da api
            tokens_output = contar_tokens(output)
            respostaFinal = output
            custo += tokens_output*0.01
            print(tokens_output)  
            
            # valor do chat
            chat_custo = (tokens_input/1000*0.0025) + (tokens_output/1000*0.01)
            print(chat_custo)
            
            # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs={"human": prompt_usuario}, outputs={"ai": output})
            
            # salvar no banco
            try:
                conn = conexao_banco()
                cursor = conn.cursor()
            
                #Atualizar custo do chat
                cursor.execute("SELECT fnc_atualizar_controle(%s,%s,%s,%s)", (tokens_input, tokens_output, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            else:
                cursor.close()
                conn.close() 

            
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
            
def substituidorNormas (resp, pergunta_usuario, norma):
    prompt=normas
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

            # Gera a resposta do modelo
            resposta = llm.stream(prompt_template.format_prompt(history=memory.buffer_as_messages, pergunta_usuario=pergunta_usuario))

            print("Resposta feita com sucesso")
            
            output = ""
            for chunk in resposta:
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    output += text_chunk
                    yield text_chunk

            # tokens do retorno da api
            tokens_output = contar_tokens(output)
            custo += tokens_output*0.01
            print(tokens_output) 
            
            # valor do chat
            chat_custo = (tokens_input/1000*0.0025) + (tokens_output/1000*0.01)
            print(chat_custo)
            
            # Atualiza o histórico com a resposta gerada
            memory.save_context(inputs={"human": pergunta_usuario}, outputs={"ai": output})
            
            # salvar no banco
            try:
                conn = conexao_banco()
                cursor = conn.cursor()
            
                #Atualizar custo do chat
                cursor.execute("SELECT fnc_atualizar_controle(%s,%s,%s,%s)", (tokens_input, tokens_output, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            else:
                cursor.close()
                conn.close() 


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
    
        global chat_id 
        
        # historico = request.form['historico']
        print("P 1")
        # obter pergunta do usuário
        pergunta_usuario = request.form['inputMessage']
        print("P 2")
        # Categorizar a pergunta
        base = categorizador(pergunta_usuario)
        print("P 3")
        print(base)
        # Gerar a resposta
        try:
            conn = conexao_banco()
            cursor = conn.cursor()
            # Atualizar fluxo do chat
            cursor.execute("SELECT fnc_atualizar_chat(%s)", (chat_id,))
            array_procedimentos = cursor.fetchone()[0]
            conn.commit()
            print(array_procedimentos)
            
        except Exception as e:
            conn.rollback()
            print(f"Erro: {e}")
        else:
            cursor.close()
            conn.close()
        
        print(array_procedimentos)
        if array_procedimentos:
            for idx,proc in enumerate(array_procedimentos):
                if proc==21:
                    if array_procedimentos[idx-1]==21 and array_procedimentos[idx-2]==21:
                        return Response(stream_with_context(procure_seu_gestor()),content_type='text/plain')
        

        if (base in arquivos ):
            print("Base encontrada")
            
            resposta_sem_normas = resposta(pergunta_usuario, base)
            
            # Verificar se há norma
            string_sem_espacos = ''.join(parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas)
            

            norma = re.search(r'(IN|M)-.{5,9}-[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                print(regra)
                reais= custo * 5.60
                print(f"Custo em dólares: {custo}")
                print(f"Custo: {reais} reais pela pergunta")
                
                return Response(stream_with_context(substituidorNormas(string_sem_espacos, pergunta_usuario,regra)), content_type='text/plain')
            
            else:
                print("nope")
                print(type(resposta_sem_normas))
                reais= custo * 5.60
                print(f"Custo em dólares: {custo}")
                print(f"Custo: {reais} reais pela pergunta")
                
                return Response(stream_with_context(resposta(pergunta_usuario, base)), content_type='text/plain')
        else: 
            reais= custo * 5.60
            print(f"Custo em dólares: {custo}")
            print(f"Custo: {reais} reais pela pergunta")
        

            
            return Response(stream_with_context(respostaErro(pergunta_usuario)), content_type='text/plain')
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
def handle_error(error):
    return render_template('error.html',error=error), error.code
    
app.run(debug=True, port=5000, host="0.0.0.0")


