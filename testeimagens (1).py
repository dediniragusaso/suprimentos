import openai
import time
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import google.generativeai as genai
import logging
import base64
import requests
import json

# Logging configuration
logging.basicConfig(
    level=logging.ERROR,
    filename="logs.log",
    filemode="a",
    format='%(levelname)s->%(asctime)s->%(message)s->%(name)s'
)

logging.getLogger('openai').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Load environment variables
load_dotenv()
api_key = os.getenv("openai_api_key")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
if not api_key:
    raise ValueError("API key not found. Make sure 'openai_api_key' is set in the environment.")

# Global variables
indicador = 
escritor = open('./prompts/escritor_prompt.txt', "r", encoding="utf8").read()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/limparTerminal", methods=["POST"])
def limparTerminal():
    global cont_requisicao
    reiniciar = request.json.get("recarregadoPorBotao", False)
    if reiniciar:
        cont_requisicao = 0
    return jsonify({"status": "success"})

# Function for error message
def algo_ocorreu_de_errado():
    yield "Um erro ocorreu. Por favor, tente novamente ou entre em contato conosco se o problema persistir por meio do e-mail <a href='mailto:gedaijef@gmail.com' class='link_resposta'>gedaijef@gmail.com</a>"

# Function to identify file based on user input
def identificaArquivo(prompt_usuario):
    
    model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    )
    
    prompt = indicador
    for arq in os.listdir("./bases"):
        prompt += "\n\n" + open(f"./bases/{arq}", "r", encoding="utf8").read()

    tentativas = 0
    tempo_de_espera = 5
    while tentativas < 3:
        tentativas += 1
        try:
            messages = [
            {'role':'model','parts': [prompt]},
            {'role':'user', 'parts':[prompt_usuario]}
            ]
            response = model.generate_content(messages)
            print(response.text)
            return response.text
        except openai.error.AuthenticationError as e:
            logging.error(f"Authentication error: {e}")
        except openai.error.APIError as e:
            logging.error(f"API error: {e}")
            time.sleep(5)
        except openai.error.RateLimitError as e:
            logging.error(f"Rate limit error: {e}")
            time.sleep(tempo_de_espera)
            tempo_de_espera *= 2
    return "erro"

def imagem_para_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to handle the response from the identified file
def respostaArquivo(prompt_usuario, arquivo, historico):
    if arquivo == "erro":
        yield "Please provide more details so I can assist you!"

    prompt = escritor
    prompt += "\n\n" + open(f"./bases/{arquivo}", "r", encoding="utf8").read()
    prompt += historico

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Constructing the payload according to the provided structure
    payload = {
        "model": "gpt-4o-2024-08-06",
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": [
                    {"type":"text",
                     "text":prompt_usuario
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "stream": True,
        "seed": 42
    }

    # Adding images to the payload if they exist
    if os.path.exists(f"imagens/{arquivo.replace('.txt', '')}"):
        imagens = os.listdir(f"imagens/{arquivo.replace('.txt', '')}")
        
        imagens_map = map(lambda x: 
            {
            "type": "image_url",
            "image_url": {"url": "data:image/jpeg;base64,"+imagem_para_base64(f'imagens/{arquivo.replace(".txt", "")}/'+x)}
            },imagens)
        print(imagens_map)
        payload["messages"][1]["content"].extend(list(imagens_map))
        
        print(payload)

    try:
        # Make the request with the payload as JSON, with streaming enabled
        resposta = requests.post("https://api.openai.com/v1/chat/completions",
                                 headers=headers, json=payload, stream=True)
        print(resposta)
        print(resposta.json())

        for line in resposta.iter_lines(decode_unicode=True):
            if line:
                if line.startswith('data: '):
                    line = line[len('data: '):]
                    if line.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(line)
                        # Extract the content from the response
                        delta = chunk.get('choices', [])[0].get('delta', {}).get('content', '')
                        if delta:
                            yield delta
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decoding error: {e}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        yield from algo_ocorreu_de_errado()

@app.route("/submit", methods=["POST"])
def submit():
    try:
        historico = request.form['historico']
        pergunta_usuario = request.form['inputMessage']
        arquivo = identificaArquivo(pergunta_usuario)
        
        return Response(stream_with_context(respostaArquivo(pergunta_usuario, arquivo, historico)), content_type='text/plain')

    except Exception as e:
        logging.error(e)


app.run(debug=True, port=5000)

