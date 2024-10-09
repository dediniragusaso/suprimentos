from dotenv import load_dotenv
import os
import logging
import requests

# Load environment variables
load_dotenv()
api_key = os.getenv("openai_api_key")
if not api_key:
    raise ValueError("API key not found. Make sure 'openai_api_key' is set in the environment.")


# prompt_60 = open('./prompts/palavras_chaves.txt', "r", encoding="utf8").read()
prompt_usuario = input("Humano: ")
prompt_60=""

for arq in os.listdir("./prompts/palavras_chave/bases_60"):
    print(arq)
    prompt_60 += f"\n\n{arq}\n" + open(f"./prompts/palavras_chave/bases_60/{arq}", "r", encoding="utf8").read()


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




payload["messages"][0]["content"] = prompt_60
resposta = requests.post("https://api.openai.com/v1/chat/completions",headers=headers, json=payload)
conteudo=resposta.json()["choices"][0]["message"]["content"]
print("Arquivo com 60 palavras :"+ conteudo)
