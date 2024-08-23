import os
import openai
from dotenv import load_dotenv
import json
import requests 
import pandas as pd

load_dotenv()

def resposta (textos):

    texto = '''#Contexto
    Você é a etapa final de um chatbot especialista nos procedimentos da JBS Suprimentos, responsável por todas as compras internas e externas para a empresa. 
    #Missão
    Sua missão é validar a acurácia das respostas que a outra parte do chat gera por meio de documentos. 

    #Instruções
    Analise os as duas respostas que vão ser fornecidas e aponte as diferenças entre elas, analisando se a primeira parte do chat foi eficiente. Verifique também se todas as informações que aparecem no chat IA estão em um dos documentos


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
    - Usuário: Pergunta: Fui autorizado a fazer aquisição de tipos de óleo diesel pela empresa. Quais são as minhas opções?
    Resposta a partir do documento: O óleo diesel subdividido em:
     Tipo A (sem adição de biodiesel) ou tipo B (com adição de biodiesel):
     Óleo diesel A S10 e B S10: combustíveis com teor de enxofre máximo de 10 mg/kg;
     Óleo diesel A S50: combustíveis com teor de enxofre máximo de 50 mg/kg; 
     Óleo diesel A S500 e B S500: combustíveis com teor de enxofre máximo de 500 mg/kg.
   Resposta a partir da primeira parte da IA: Aqui estão algumas das opções de óleo diesel que você pode adquirir:

      Óleo diesel tipo A (sem adição de biodiesel) ou tipo B (com adição de biodiesel)
      Óleo diesel A S10 e B S10: combustíveis com teor de enxofre máximo de 10 mg/kg
      Óleo diesel A S50: combustíveis com teor de enxofre máximo de 50 mg/kg
      Óleo diesel A S500 e B S500: combustíveis com teor de enxofre máximo de 500 mg/kg
      Óleo diesel S10

    -ChatBot: A partir de uma análise, percebi que o chat adicionou um informação a mais. De resto, todas as informações são compatíveis. O chat utlizou todas as informações fornecidas no documento, porém alterando algumas palavras 

    Espero ter ajudado! Caso tenha mais alguma dúvida, estou à disposição.
    
    2.
    - Usuário: Pergunta: De quais instituições minha mercadoria pode sofrer intervenção no processo de importação?
    Resposta a partir do documento: Como atividade diretamente ligada ao interesse econômico do Estado, a atividade de importação sofre intervenção direta de diversos órgãos da administração pública. Dentre eles destacam-se:
    Receita Federal do Brasil – RFB;
    Departamento de Operações de Comércio Exterior – DECEX;
    Ministério da Agricultura, Pecuária e do Abastecimento – MAPA;
    Agência Nacional de Vigilância Sanitária – ANVISA;
    Instituto Brasileiro do Meio Ambiente e dos Recursos Naturais Renováveis – IBAMA;
    Instituto Nacional de Metrologia – INMETRO;
    Departamento de Polícia Federal – DPF;
    Ministério do Exército – ME;
    Agência Nacional do Petróleo – ANP;
    Agência Nacional de Energia Elétrica – ANEEL;
    Comissão Nacional de Energia Nuclear – CNEN;
    Ministério do Desenvolvimento, Indústria e Comercio Exterior – MDIC.

    Resposta a partir da IA: De acordo com o procedimento da JBS para importação, a mercadoria pode sofrer intervenção de várias instituições no processo de importação. Essas instituições são:

     Receita Federal do Brasil (RFB)
     Departamento de Operações de Comércio Exterior (DECEX)
     Ministério da Agricultura, Pecuária e do Abastecimento (MAPA)
     Agência Nacional de Vigilância Sanitária (ANVISA)
     Instituto Brasileiro do Meio Ambiente e dos Recursos Naturais Renováveis (IBAMA)
     Instituto Nacional de Metrologia (INMETRO)
     Departamento de Polícia Federal (DPF)
     Ministério do Exército (ME)
     Agência Nacional do Petróleo (ANP)
     Agência Nacional de Energia Elétrica (ANEEL)
     Comissão Nacional de Energia Nuclear (CNEN)
     Ministério do Desenvolvimento, Indústria e Comércio Exterior (MDIC)

    Espero que isso tenha ajudado! Se tiver qualquer outra dúvida, estou à disposição.

    -ChatBot: As duas respostas estão bem similares, a que foi feita a partir do documento tem um início mais completo e detalhado. No entanto, todas as informações que o Chat gerou estavam no documento.

    

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
            {"role": "user", "content": textos}
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

teste_base= pd.read_excel(r'C:\Users\sophiaragusa-ieg\OneDrive - Instituto Germinare\GEDAI\Suprimentos\data_test.xlsx')

teste_base['Validacao']= ''
for i in teste_base.index:
    p1 = teste_base.loc[i,"pergunta"]
    p2 = teste_base.loc[i,"resposta"]
    p3= teste_base.loc[i,"Resposta_IA"]
    prompt_usuário= p1 + "\n\n" + p2 + "\n\n" + p3
    teste_base.loc[i, 'Validacao'] = resposta(prompt_usuário)
    print("Funcionou")
teste_base.to_excel("data_test.xlsx")