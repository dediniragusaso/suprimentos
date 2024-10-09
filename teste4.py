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

openai.api_key = api_key

# variáveis globais
categorizador_prompt= open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
escritor= open('./prompts/escritor_prompt.txt',"r",encoding="utf8").read() 
erro = open('./erro.txt',"r",encoding="utf8").read() 
normas= open('./prompts/prompt_normas.txt', "r", encoding="utf8").read()

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

def contar_tokens(texto):
    return len(encoding.encode(texto))

def categorizador(prompt_usuario):
    prompt=categorizador_prompt
    print (type(prompt))
    for arq in (os.listdir("./bases")):
        prompt += open(f"./bases/{arq}","r",encoding="utf8").read()  
    tentativas = 0
    tempo_de_espera = 5
    tokens_input= contar_tokens(prompt)
    print(f"Entrada:{tokens_input}")
    while tentativas <3:
        tentativas+=1
        try:
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
                temperature=0.7,
                max_tokens=100,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            
            print("Análise realizada com sucesso")
            return resposta.choices[0].message.content
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2


def resposta (prompt_usuario, historico, nome_arquivo):
    prompt=escritor
    prompt+= open(f"./bases/{nome_arquivo}","r",encoding="utf8").read()
    prompt += historico
    tentativas = 0
    tempo_de_espera = 5
    tokens_input= contar_tokens(prompt)
    print(f"Entrada:{tokens_input}")
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

            tokens_output = contar_tokens(output)
            print(f"Tokens de saída: {tokens_output}")               

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
    tokens_input= contar_tokens(prompt)
    print(f"Entrada:{tokens_input}")
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
            print(f"Tokens de saída: {tokens_output}") 

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
    tokens_input= contar_tokens(prompt)
    print(f"Entrada:{tokens_input}")
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
            print(f"Tokens de saída: {tokens_output}") 

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
        # custo_input = 0.0025
        # custo_output = 0.01
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        base = categorizador(pergunta_usuario)
        resposta_sem_normas = resposta(pergunta_usuario, historico, base)
        print(base)
        # model ='gpt-4o-2024-08-06'
        # enc = tiktoken.encoding_for_model(model)
        
        if ( base in arquivos ):
            print("Base encontrada")
            prompt = historico + pergunta_usuario
            for arq in (os.listdir("./bases")):
                prompt += open(f"./bases/{arq}","r",encoding="utf8").read() 
            string_sem_espacos = ''
            
            for parte in resposta_sem_normas:
                string_sem_espacos += parte.replace(" ", "").replace("\n", "")
            norma = re.search(r'(IN|M)-.*[0-9]{4}', string_sem_espacos, re.IGNORECASE)
            if norma:
                print("Baseado em norma")
                regra = norma.group()  
                print(regra)
                
                return Response(stream_with_context(substituidorNormas(resposta_sem_normas, historico, pergunta_usuario,regra)), content_type='text/plain')
            
            else:
                print("nope")
                print(type(resposta_sem_normas))
                return Response(stream_with_context(resposta(pergunta_usuario, historico, base)), content_type='text/plain')
     
        else: 
            return Response(stream_with_context(respostaErro(pergunta_usuario,historico)), content_type='text/plain')
    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)

