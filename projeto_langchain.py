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
import psycopg2

# langchain
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

# Método para conectar no banco
def conexao_banco():
    try:
        db_link = os.getenv("DB_LINK")
        if not db_link:
            raise ValueError("Variável de ambiente DB_LINK não definida.")
        
        # Adicionar parâmetros de SSL
        conn = psycopg2.connect(
            db_link
            # sslmode='require',
            # sslrootcert='/etc/secrets/ca.pem'
        )
        print("Conexão feita com sucesso!")
        return conn
    except Exception as e:
        print(f"Erro ao conectar no banco de dados: {e}")
        return None

# variáveis globais
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()
chat_id = 0

# Inicializar a memória de conversação
memory = ConversationBufferMemory(memory_key="history")

encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

app = Flask(__name__)

# Página Raíz
@app.route('/')
def index():
    global chat_id
    
    try:
        conn = conexao_banco()
        cursor = conn.cursor()
        
        # inserindo um novo chat
        cursor.execute("""INSERT INTO CHATS(DT_CHAT, NR_PERGUNTAS, NR_RESPOSTAS) 
                        VALUES (NOW(), 0, 0)
                        RETURNING ID_CHAT;""")
        chat_id = cursor.fetchone()[0]
        
        cursor.execute("""INSERT INTO CONTROLE(CD_CHAT, NR_TOKENS_PERG, NR_TOKENS_RESP, VL_DOLAR)
                        VALUES(%s, 0, 0, 0)""",(chat_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro: {e}")
    finally:
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

def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario):
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()

    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()
        
    prompt_100 += prompt_usuario
    
    # tokens do input
    tokens_input = contar_tokens(prompt_100)
    print(f"Entrada: {tokens_input}")
    
    # categoria
    categoria = llm.invoke([HumanMessage(content=prompt_100)])
    print("tipo: " + categoria.content)
    
    # tokens do retorno da api
    output = categoria.content     
    tokens_output = contar_tokens(output)
    print(tokens_output)
    
    # custo do chat
    chat_custo = (tokens_input/1000*0.0025) + (tokens_output/1000*0.01)
    print(chat_custo)
    
    try:
        conn = conexao_banco()
        cursor = conn.cursor()
    
        #Atualizar custo do chat
        cursor.execute("""UPDATE CONTROLE SET 
                        NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                        NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                        VL_DOLAR = VL_DOLAR + %s
                        WHERE CD_CHAT = %s;""", (tokens_input, tokens_output, chat_custo, chat_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro: {e}")
    finally:
        cursor.close()
        conn.close()
    
    return categoria.content


def resposta (prompt_usuario, nome_arquivo):
    global chat_id
    prompt=escritor
    prompt+= open(f"./bases/{nome_arquivo}","r",encoding="utf8").read()
    #prompt += historico
    
    tentativas = 0
    tempo_de_espera = 5
    
    # tokens do input
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
                cursor.execute("""UPDATE CONTROLE SET 
                                NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                                NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                                VL_DOLAR = VL_DOLAR + %s
                                WHERE CD_CHAT = %s;""", (tokens_input, tokens_output, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            finally:
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
    prompt=erro
    # prompt += historico
    
    # tokens de entrada
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
                cursor.execute("""UPDATE CONTROLE SET 
                                NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                                NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                                VL_DOLAR = VL_DOLAR + %s
                                WHERE CD_CHAT = %s;""", (tokens_input, tokens_output, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            finally:
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
    # prompt += historico
    prompt += ''.join(resp)  # junta todas as strings geradas por 'resp'
    prompt += open(f"./bases_normas/{norma}.txt","r",encoding="utf8").read() 
    
    # tokens do input
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
                cursor.execute("""UPDATE CONTROLE SET 
                                NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                                NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                                VL_DOLAR = VL_DOLAR + %s
                                WHERE CD_CHAT = %s;""", (tokens_input, tokens_output, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            finally:
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
for arq in (os.listdir("./bases")):
        arquivos.append(arq) 

@app.route("/submit", methods=["POST"])
 
def submit():
    
    try:
    
        global chat_id
        
        # historico = request.form['historico']
        
        # obter pergunta do usuário
        pergunta_usuario = request.form['inputMessage']
    
        # Categorizar a pergunta
        base = categorizador(pergunta_usuario)
        
        # Gerar a resposta
        resposta_sem_normas = resposta(pergunta_usuario, base)
        if (base in arquivos ):
            print("Base encontrada")
            
            # Verificar se há norma
            string_sem_espacos = ''.join(parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas)
            norma = re.search(r'(IN|M)-.*[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                print(regra)
                
                return Response(stream_with_context(substituidorNormas(resposta_sem_normas, pergunta_usuario,regra)), content_type='text/plain')
            
            else:
                print("nope")
                print(type(resposta_sem_normas))
            
                return Response(stream_with_context(resposta(pergunta_usuario, base)), content_type='text/plain')
        else: 
            return Response(stream_with_context(respostaErro(pergunta_usuario)), content_type='text/plain')
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    finally:
        try:
            conn = conexao_banco()
            cursor = conn.cursor()
            # Atualizar fluxo do chat
            cursor.execute("""UPDATE CHATS SET 
                            NR_PERGUNTAS = NR_PERGUNTAS + %s,  
                            NR_RESPOSTAS = NR_RESPOSTAS + %s 
                            WHERE ID_CHAT = %s;""", (1,1,chat_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Erro: {e}")
        finally:
            cursor.close()
            conn.close()
    
app.run(debug=True, port=5000, host="0.0.0.0")