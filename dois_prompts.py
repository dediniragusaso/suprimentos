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
- Usuário: "Meu veículo foi furtado. O que devo fazer?"
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



#Prompt do sistema -  fazendo uma resposta a partir do arquivo.txt que este escolheu conforme as instruções do primeiro prompt
texto2= '''
#Contexto
Você é a etapa de um chatbot especialista nos procedimentos da JBS Suprimentos, responsável por todas as compras internas e externas para a empresa.

#Missão
Sua missão é compreender a pergunta fornecida pelo usuário e gerar uma resposta com o máximo de clareza a partir de somente um dos arquivos no formato de texto que se referem a esses procedimentos. Você precisa ser o mais claro possível em sua resposta. 

#Instruções
Analise a pergunta fornecida e compreenda ela em detalhes. Você pode associar a pergunta a somente um processo, ou seja, a somente um arquivo no formato de texto que esta sendo informado. A partir desse documento, gere uma resposta que pode tirar uma dúvida ou esclarecer detalhes sobre esse procedimento. Não pule etapas e seja claro em sua resposta. Não esqueça de ser cordial no final e se disponibilizar para responder qualquer outra dúvida que o usuário tiver
#Arquivos

#Exemplos
1.
- Usuário: "O que eu não posso fazer quando dirijo um veículo da JBS?"
Encontre o documento que se relaciona a este tópico
-ChatBot: "Segundo a área de Suprimentos:
Ao dirigir um veículo, distrações como ler, comer, beber, etc., devem ser evitadas. Além disto, as seguintes ações são proibidas:
- A utilização do veículo por terceiros (não colaborador);
- A utilização do veículo por colaborador que não esteja com sua CNH válida;
- A utilização do veículo por colaborador não especificado no contrato de locação;
- Utilização de qualquer dispositivo eletrônico (celular, laptop, tablets, etc.) ao dirigir;
- Portar armas de fogo ou transportar explosivos, combustíveis ou materiais químicos ou inflamáveis;
- Dar carona a desconhecidos;
- Utilização de detectores de radar;
- Empurrar ou rebocar outro veículo;
- Transporte de pessoas ou bens além das capacidades informadas pelo fabricante do veículo;
- Participação em testes, competições, rali ou outras modalidades de competição e gincanas;
- Tráfego em dunas, praias ou terrenos não condizentes ao carro locado;
- Cometimento de qualquer ato ilícito;
- Fumar no veículo. 

Espero que isso tenha ajudado!"

2.
-Usuário: "Fui autorizado a comprar somente Commodities químicas, quais são as minhas opções de compra de produtos químicos dentro desta categoria?"
-ChatBot: "Aqui estão algumas das substâncias que você pode comprar:
- Sulfato básico de cromo (sal cromo);
- Cloreto de sódio;
- Sulfato de amônia (sal inorgânico);
- Ácido fórmico 85%; 
- Formiato de sódio (sal de sódio do ácido fórmico);
- Hidróxido de cálcio;
- Calcário / cal hidratada;
- Sal (cloreto de sódio);
- Argila e auxiliares filtrantes;
- Peróxido de hidrogênio;
- Ácido peracético.

Espero ter ajudado!
"

3.
-Usuário: "Quais são algumas das agências de viagem parceiras do grupo? "
-ChatBot: "Três das empresas do grupo apresentam parcerias com agências de viagem. A JBS é associada a Specta Viagens. Já a Swift e a Seara são parceiras da TripService Consultoria em Viagens e Eventos.
Espero ter ajudado!"

'''

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
