# Importações
import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
import re
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context
import tiktoken
import requests 
import psycopg2

# LOG
from logging import ERROR
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
from logging import getLogger

basicConfig(
    level = ERROR  , #Todas as informações com maior ou prioridade igual ao DEBUG serão armazenadas
    filename= "logs.log", #Onde serão armazenadas as informações
    filemode= "a", # Permissões do arquivo [se poderá editar, apenas ler ...]
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' # Formatação da informação
)
getLogger('openai').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

# Variáveis de ambiente
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
correct_password = os.getenv("CORRECT_PASSWORD")
if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

openai.api_key = api_key

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


# Variáveis Globais
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()
chat_id = 0

encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

app = Flask(__name__)

# Página Raiz
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
        print(chat_id)
        
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
        return jsonify({"status": "error", "message": str(e)}),500

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
    yield "Algo ocorreu de errado, tente novamente"

# Contar o número de tokens
def contar_tokens(texto):
    return len(encoding.encode(texto))

# Categorizar mensagem em apenas um procedimento
def categorizador(prompt_usuario, api_key):
    global chat_id
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()


    for arq in os.listdir("./prompts/palavras_chaves"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/{arq}", "r", encoding="utf8").read()


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o-2024-08-06",
        "messages": [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": prompt_usuario
            }
        ],
        "max_tokens": 1000,
        "seed": 42
    }
   

    payload["messages"][0]["content"] = prompt_100
    resposta = requests.post("https://api.openai.com/v1/chat/completions",headers=headers, json=payload)
    
    nr_tokens_perg, nr_tokens_resp = resposta.json()["usage"]["prompt_tokens"], resposta.json()["usage"]["completion_tokens"]
    chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
    resposta = resposta.json()["choices"][0]["message"]["content"]  
    print(chat_custo)   
    print(resposta)
    
    try:
        conn = conexao_banco()
        cursor = conn.cursor()
    
        # Associar o procedimento ao chat
        cursor.execute("""SELECT ID_PROCEDIMENTO FROM PROCEDIMENTOS
                            WHERE NM_PROCEDIMENTO = %s;""", (resposta.replace(".txt",""),)) 
        procedimento_id =  cursor.fetchone()[0]
        cursor.execute("""INSERT INTO PROCEDIMENTOS_CHAT(CD_CHAT, CD_PROCEDIMENTO)
                            VALUES (%s, %s);""", (chat_id, procedimento_id))
        
        # Atualizar o custo do chat
        cursor.execute("""UPDATE CONTROLE SET 
                          NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                          NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                          VL_DOLAR = VL_DOLAR + %s
                          WHERE CD_CHAT = %s;""", (nr_tokens_perg, nr_tokens_resp, chat_custo, chat_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro: {e}")
    finally:
        cursor.close()
        conn.close()

    return resposta

# Responder a pergunta baseado no procedimento       
def resposta (prompt_usuario, historico, nome_arquivo):
    global chat_id
    prompt=escritor
    prompt+= open(f"./bases/{nome_arquivo}","r",encoding="utf8").read()
    prompt += historico
    
    tentativas = 0
    tempo_de_espera = 5
    nr_tokens_perg= contar_tokens(prompt)
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
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            nr_tokens_resp = contar_tokens(output)
            chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
            print(chat_custo)
            
            try:
                conn = conexao_banco()
                cursor = conn.cursor()
            
                #Atualizar custo do chat
                cursor.execute("""UPDATE CONTROLE SET 
                                NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                                NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                                VL_DOLAR = VL_DOLAR + %s
                                WHERE CD_CHAT = %s;""", (nr_tokens_perg, nr_tokens_resp, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            finally:
                cursor.close()
                conn.close()            

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


# Pedir mais informações ao usuário
def respostaErro (prompt_usuario, historico):
    prompt=erro
    prompt += historico
    nr_tokens_perg= contar_tokens(prompt)
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
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text
            
            nr_tokens_resp = contar_tokens(output)
            chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
            print(chat_custo)
            
            try:
                conn = conexao_banco()
                cursor = conn.cursor()

                # Atualizar custo do chat
                cursor.execute("""UPDATE CONTROLE SET 
                                NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                                NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                                VL_DOLAR = VL_DOLAR + %s
                                WHERE CD_CHAT = %s;""", (nr_tokens_perg, nr_tokens_resp, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            finally:
                cursor.close()
                conn.close()    
            

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

# Substituir normas pelo conteúdo correspondente
def substituidorNormas (resp,historico,pergunta_usuario,norma):
    prompt=normas
    prompt += historico
    prompt += ''.join(resp)  # junta todas as strings geradas por 'resp'
    prompt += open(f"./bases_normas/{norma}.txt","r",encoding="utf8").read() 
    nr_tokens_perg= contar_tokens(prompt)
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
                        "content": pergunta_usuario
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
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text
            
            nr_tokens_resp = contar_tokens(output)
            chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
            print(chat_custo)
            
            try:
                conn = conexao_banco()
                cursor = conn.cursor()
            
                # Atualizar custo do chat
                cursor.execute("""UPDATE CONTROLE SET 
                                NR_TOKENS_PERG = NR_TOKENS_PERG + %s, 
                                NR_TOKENS_RESP = NR_TOKENS_RESP + %s,
                                VL_DOLAR = VL_DOLAR + %s
                                WHERE CD_CHAT = %s;""", (nr_tokens_perg, nr_tokens_resp, chat_custo, chat_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Erro: {e}")
            finally:
                cursor.close()
                conn.close()    
        
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

arquivos=[]
for arq in (os.listdir("./bases")):
        arquivos.append(arq) 


# Resposta do usuário
@app.route("/submit", methods=["POST"])
 
def submit():
    
    try:
        
        global chat_id
        
        # Obter historico e pergunta do usuário
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
    
        # Categorizar a pergunta
        base = categorizador(pergunta_usuario, api_key)
        
        # Gerar a resposta
        resposta_sem_normas = resposta(pergunta_usuario, historico, base)
        if ( base and base in arquivos ):
            print("Base encontrada")
            
            # Verificar se há norma
            string_sem_espacos = ''.join(parte.replace(" ", "").replace("\n", "") for parte in resposta_sem_normas)
            norma = re.search(r'(IN|M)-.*[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                
                return Response(stream_with_context(substituidorNormas(resposta_sem_normas, historico, pergunta_usuario,regra)), content_type='text/plain')
            
            else:
            
                return Response(stream_with_context(resposta(pergunta_usuario, historico, base)), content_type='text/plain')
            
        else: 
            return Response(stream_with_context(respostaErro(pergunta_usuario,historico)), content_type='text/plain')
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

# Executar o servidor
app.run(debug=True, port=5000, host="0.0.0.0")
