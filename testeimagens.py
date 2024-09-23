import openai
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
import base64
import requests
import json

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
                max_tokens=1000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            print(resposta.choices[0].message.content)
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


def imagem_para_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

""
def respostaArquivo (prompt_usuario, arquivo, historico):
    
    if arquivo=="erro":
        yield "Por favor, informe mais detalhes para que eu possa te ajudar!"
    
    prompt = escritor
    prompt += "\n\n" + open(f"./bases/{arquivo}","r",encoding="utf8").read() 
    
    prompt += historico
    tentativas = 0
    tempo_de_espera = 5
    
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }
    
    payload = '''{{
    "model": "gpt-4o-2024-08-06",
    "messages": [
        {{
        "role": "system",
        "content":[
            {{
            "type": "text",
            "text": "{}"
            }}
        ]}},
        {{
        "role": "user",
        "content": [
            {{
            "type": "text",
            "text": "{}"
            }}'''.format(prompt.replace("\n", "\\n").replace('"', '\\"'), 
                        prompt_usuario.replace("\n", "\\n").replace('"', '\\"'))
    
    if os.path.exists("imagens/"+arquivo.replace(".txt","")):
        imagens = os.listdir("imagens/"+arquivo.replace(".txt",""))
        for img in imagens:
            base64_img =imagem_para_base64("./imagens/"+arquivo.replace(".txt","")+"/"+img)
            payload+=f'''
                ,{{
                        "type": "image_url",
                        "image_url": {{
                            "url": "data:image/jpeg;base64,{base64_img}"
                        }}
                        }}'''
    
    payload+= '''        
        ]
        }
    ],
    "max_tokens": 1000
    }'''

    while tentativas <3:
        tentativas+=1
        print(f"Tentativa {tentativas}")
        try:
            
            
            resposta = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json.loads(payload))
            resposta_json = resposta.json()['choices'][0]['message']['content']
            print(resposta)
            print(resposta_json)

            # model ='gpt-4o-2024-08-06'
            # enc = tiktoken.encoding_for_model(model)
            # print(f"Quantidade de tokens:{len(enc.encode(payload))} - ${len(payload[:payload.find('ai:')])/1000*0.0025+len(payload[:payload.find('ai:')])/1000*0.01}")

            # print("Resposta feita com sucesso")
            # for chunk in resposta:
            #     print(resposta_json)
            #     if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
            #         text = chunk['choices'][0]['delta']['content']
            #         if text:
            #             print(text, end="")
            #             yield text
            return resposta_json
        except openai.error.AuthenticationError as e:
            print(f"Erro de autentificação {e}")
        except openai.error.APIError as e:
            print(f"Erro de API {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            print(f"Erro de limite de taxa: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *=2


@app.route("/submit", methods=["POST"])
def submit():
    
    try:
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        arquivo = identificaArquivo(pergunta_usuario)
        
        print(historico + "\n")
        print("-="*30)
        
        return Response(stream_with_context(respostaArquivo(pergunta_usuario,arquivo, historico)), content_type='text/plain')
        
    except Exception as e:
        print(error)
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')
    
app.run(debug=True, port=5000)








