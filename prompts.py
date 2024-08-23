import os
import openai
from dotenv import load_dotenv
import json
import requests 

load_dotenv()

texto = '''
   # Contexto

Você é uma etapa de um chatbot especialista nos procedimentos da JBS Suprimentos, responsável por todas as compras internas e externas para a empresa. Seu objetivo é indicar qual o procedimento correto de acordo com o a pergunta do usuário, indicando apenas o nome do arquivo para posteriormente outra etapa extrair a resposta, qual não é sua função.

# Missão

Sua missão é entender o contexto do usuário e fazer uma conexão com um e somente um arquivo. É de extrema importância que a conexão seja feita de maneira correta, fazendo sentido com a pergunta do usuário, pois caso o nome do arquivo enviado seja errado, isto pode prejudicar o funcionário, então tenha calma e pense bem, leve o tempo que precisar.

# Instruções

Envie apenas e somente o nome do arquivo do qual você fez a ligação, ou seja, você deve enviar o nome do procedimento + .txt caso já não haja uma extensão no arquivo. Cuidado para não adicionar a extensão duas vezes e prejudicar os dados do arquivo

# Arquivos

Seguem abaixo os nomes dos arquivos de texto que contêm todos os procedimentos da JBS Suprimentos:

-adiantamento_fornecedores_de_materiais_servicos.txt
-combustíveis.txt
-compra_produtos_quimicos.txt
-compra_recebimento_biomassa.txt
-contratacao_material_servico.txt
-contratacao_servico_rh.txt
-importação.txt
-locacao_veiculo.txt
-operacao_marketing_midia.txt
-recebimento_amostra_exterior.txt
-retorno_mercadoria_exportada.txt
-solicitacao_vistos_tecnicos.txt
-solicitacoes_despesas_viagens.txt

# Exemplos 

1.
- Usuário: "Meu veículo foi furtado. O que devo fazer"
-ChatBot: "locacao_veiculo.txt"

2.
-Usuário: "Fui autorizado a comprar somente Commodities químicas, quais são as minhas opções de compra de produtos químicos dentro desta categoria?"
-ChatBot: "compra_produtos_quimicos.txt"

3.
-Usuário: "Preciso de um atendimento emergencial em minha viagem, porém já está fora do horário comercial. Quem devo contatar?"
-ChatBot: "solicitacoes_despesas_viagens.txt"



'''


for arq in (os.listdir("projeto_chat_suprimentos/bases")):
    texto += "\n\n" + open(f"projeto_chat_suprimentos/bases/{arq}","r",encoding="utf8").read() 

api_key = os.getenv("openai_api_key")
print(api_key)


if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")


headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}




parameters = {
    "model": "gpt-4o",
    "messages": [
        {"role": "system", "content": texto},
        {"role": "user", "content": input("Sua mensagem: ")}
    ],
    "temperature": 1
}


url_chat = "https://api.openai.com/v1/chat/completions"

try:
    print("Iniciando a análise...\n\n")

   
    resposta = requests.post(url_chat, headers=headers, json=parameters)
    resposta.raise_for_status()    

    resposta_json = resposta.json()

    
    if 'choices' in resposta_json:
        print("Resposta feita com sucesso")
        print(resposta_json['choices'][0]['message']['content'])
    else:
        print("Erro: 'choices' não encontrado na resposta.")

except requests.exceptions.HTTPError as e:
    print(f"Erro HTTP: {e.response.status_code} - {e.response.text}")
except requests.exceptions.RequestException as e:
    print(f"Erro na requisição: {e}")
except Exception as e:
    print(f"Erro inesperado: {e}")



# import tiktoken

# modelo = "gpt-3.5-turbo-1106"
# codificador = tiktoken.encoding_for_model(modelo)
# lista_tokens = codificador.encode(texto)

# print("Lista de Tokens: ", lista_tokens)
# print("Quantos tokens temos: ", len(lista_tokens))
# print(f"Custo para o modelo {modelo} é de ${(len(lista_tokens)/1000) * 0.001}")
