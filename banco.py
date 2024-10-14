import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
import re
from flask import Flask, render_template,  request, jsonify, Response, stream_with_context
from logging import ERROR
# #Funções
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
from logging import getLogger
import tiktoken
import requests 
import psycopg2

basicConfig(
    level = ERROR  , #Todas as informações com maior ou prioridade igual ao DEBUG serão armazenadas
    filename= "logs.log", #Onde serão armazenadas as informações
    filemode= "a", # Permissões do arquivo [se poderá editar, apenas ler ...]
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' # Formatação da informação
)
getLogger('openai').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
correct_password = os.getenv("CORRECT_PASSWORD")
if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

openai.api_key = api_key

def conexao_banco():

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

    return conn, conn.cursor()

    
# def add_sala():
#     conn = get_connection()
#     cursor = conn.cursor()

#     data = request.get_json()
#     titulo = data["titulo"]

#     cursor.execute("INSERT INTO sala (titulo) VALUES (%s) RETURNING id",(titulo,))
#     sala_id = cursor.fetchone()[0]
#     #fechar
#     conn.commit()
#     cursor.close()
#     conn.close() 
#     return {"sala_id": sala_id, "message:": "Sala criada com sucesso"}


# variáveis globais
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./prompts/erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()
chat_id = 0

encoding = tiktoken.encoding_for_model("gpt-4o-2024-08-06")

app = Flask(_name_)

@app.route('/')
def index():
    global chat_id
    
    try:
        conn, cursor = conexao_banco()
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
    yield "Algo ocorreu de errado, tente novamente"

def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario, api_key):
    global chat_id
    prompt_100 = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()


    for arq in os.listdir("./prompts/palavras_chaves/bases_100"):
        prompt_100 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chaves/bases_100/{arq}", "r", encoding="utf8").read()


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
    
    try:
        conn, cursor = conexao_banco()
        
        cursor.execute("""SELECT ID_PROCEDIMENTO FROM PROCEDIMENTOS
                            WHERE NM_PROCEDIMENTO = %s;""", (resposta.replace(".txt",""))) 
        procedimento_id =  cursor.fetchone()[0]
        cursor.execute("""INSERT INTO PROCEDIMENTOS_CHATS(CD_CHAT, ID_PROCEDIMENTO)
                            VALUES (%s, %s);""", (chat_id, procedimento_id))
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
            output=""
            for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            output+=text
                            yield text

            nr_tokens_resp = contar_tokens(output)
            chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
            
            try:
                conn, cursor = conexao_banco()
            
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

            tokens_output = contar_tokens(output)
            
            nr_tokens_resp = contar_tokens(output)
            chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
            
            try:
                conn, cursor = conexao_banco()
            
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

            tokens_output = contar_tokens(output)
            
            nr_tokens_resp = contar_tokens(output)
            chat_custo = (nr_tokens_perg/1000*0.0025) + (nr_tokens_resp/1000*0.01)
            
            try:
                conn, cursor = conexao_banco()
            
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



@app.route("/submit", methods=["POST"])
 
def submit():
    
    try:
        
        global chat_id
        
        try:
            conn, cursor = conexao_banco()
            cursor.execute("""UPDATE CHATS SET 
                            NR_PERGUNTAS = NR_PERGUNTAS + 1,  
                            NR_RESPOSTAS = NR_RESPOSTAS + 1 
                            WHERE ID_CHAT = %s;""", (chat_id,))
            chat_id = cursor.fetchone()[0]
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Erro: {e}")
        finally:
            cursor.close()
            conn.close()
        
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
    
        base = categorizador(pergunta_usuario, api_key)
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
    
app.run(debug=True, port=5000, host="0.0.0.0")