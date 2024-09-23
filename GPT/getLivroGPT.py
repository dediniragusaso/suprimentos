import os
import base64
import requests
import json

#Chave API
api_key = "sk-proj-q280AmFYCfGVL6pu1tqnT3BlbkFJ23Zg15iSf4MI13ZqBFtF"

#Converte as imagens em Base64
def imagem_para_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

imagens = os.listdir("GPT\images")
payload = '''{
  "model": "gpt-4o-2024-08-06",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "conte quantas imagens eu passar, independente de serem iguais ou não e no final diga quanto gastou de tokens por imagem"
        }'''

for img in imagens:
  base64_img =imagem_para_base64("GPT/images/"+img)
  payload+=f'''
   ,{{
          "type": "image_url",
          "image_url": {{
            "url": "data:image/jpeg;base64,{base64_img}"
          }}
        }}
  '''

payload+= '''        
      ]
    }
  ],
  "max_tokens": 300
}'''

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

print(json.loads(payload))
response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json.loads(payload))
retornoGPT = response.json()['choices'][0]['message']['content']
print(retornoGPT)

