import os
import google.generativeai as genai
from dotenv import load_dotenv
from google.ai.generativelanguage_v1beta.types import content


load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Read the initial prompt from a file and append the content from additional files
prompt_indicador = open('./prompts/indicador_prompt.txt', "r", encoding="utf8").read()
for arq in os.listdir("./bases"):
    prompt_indicador += "\n\n" + open(f"./bases/{arq}", "r", encoding="utf8").read()

# Add user input to the prompt as a new message
user_input = "Como posso me cadastrar no paytrack"

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_schema": content.Schema(
    type = content.Type.OBJECT,
    properties = {
      "response": content.Schema(
        type = content.Type.STRING,
      ),
    },
  ),
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
  system_instruction=prompt_indicador
)

chat_session = model.start_chat(
  history=[]
)
response = chat_session.send_message(user_input)
print(response)