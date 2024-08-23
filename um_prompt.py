import os
import openai
from dotenv import load_dotenv
import json
import requests 
import pandas as pd

load_dotenv()

def resposta (pergunta):

    texto = '''#Contexto
    Você é a etapa de um chatbot especialista nos procedimentos da JBS Suprimentos, responsável por todas as compras internas e externas para a empresa. 
    #Missão
    Sua missão é compreender a pergunta fornecida pelo usuário e gerar uma resposta com o máximo de clareza a partir de somente um dos arquivos no formato de texto que se referem a esses procedimentos. Você precisa ser o mais claro possível em sua resposta. 

    #Instruções
    Analise a pergunta fornecida e compreenda ela em detalhes. Você pode associar a pergunta a somente um processo, ou seja, aquele e precisa mostrar o nome do seu documento, ou seja,aquele que mais se encaixa na pergunta. Somente um arquivo no formato de texto que vai ser informado no tópico de arquivos deste prompt. A partir desse documento, gere uma resposta que pode tirar uma dúvida ou esclarecer algo sobre esse procedimento, no entanto, responda somente o que o usuário perguntar.Você pode utilizar tópicos para sua resposta, porém não usem caracteres especiais Não pule etapas e seja claro em sua resposta. Não esqueça de ser cordial no final e se disponibilizar para responder qualquer outra dúvida que o usuário tiver
    #Arquivos
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

    #Exemplos
    1.
    - Usuário: "O que eu não posso fazer quando dirijo um veículo da JBS?"
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


    for arq in (os.listdir("projeto_chat_suprimentos/bases")):
        texto += "\n\n" + open(f"projeto_chat_suprimentos/bases/{arq}","r",encoding="utf8").read() 

    api_key = os.getenv("openai_api_key")

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
            {"role": "user", "content": pergunta}
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

    return resposta_json['choices'][0]['message']['content']

teste_base= pd.read_excel(r'C:\Users\sophiaragusa-ieg\OneDrive - Instituto Germinare\GEDAI\Suprimentos\projeto_chat_suprimentos\data_test.xlsx')

teste_base['Resposta_IA']= ''
for i in teste_base.index:
    teste_base.loc[i, 'Resposta_IA'] = resposta(teste_base.loc[i,"pergunta"])
    print("Funcionou")
teste_base.to_excel("data_test.xlsx")
    





# import tiktoken

# modelo = "gpt-3.5-turbo-1106"
# codificador = tiktoken.encoding_for_model(modelo)
# lista_tokens = codificador.encode(texto)

# print("Lista de Tokens: ", lista_tokens)
# print("Quantos tokens temos: ", len(lista_tokens))
# print(f"Custo para o modelo {modelo} é de ${(len(lista_tokens)/1000) * 0.001}")
