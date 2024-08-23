import openai
import time
import tiktoken
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, redirect, jsonify, Response, stream_with_context

#Constantes
from logging import ERROR #Erro comum  
 
# #Funções
from logging import basicConfig #configurações para os comportamentos dos logs
from logging import error
 
from logging import getLogger
basicConfig(
    level = ERROR  , #Todas as informações com maior ou prioridade igual ao DEBUG serão armazenadas
    filename= "logs.log", #Onde serão armazenadas as informações
    filemode= "a", # Permissões do arquivo [se poderá editar, apenas ler ...]
    format= '%(levelname)s->%(asctime)s->%(message)s->%(name)s' # Formatação da informação
)
 
# Configuração explícita dos loggers das bibliotecas
getLogger('openai').setLevel(ERROR)
getLogger('werkzeug').setLevel(ERROR)

# carregando variáveis de ambiente
load_dotenv()
api_key = os.getenv("openai_api_key")

if not api_key:
    raise ValueError("Chave API não encontrada. Verifique se 'openai_api_key' está definida no ambiente.")

openai.api_key = api_key

# variáveis globais
cont_requisicao = 0
lista_historico = ["","",""]
texto = '''
    #Contexto
    Você é a etapa de um chatbot especialista nos procedimentos da JBS Suprimentos, responsável por todas as compras internas e externas para a empresa. 
    #Missão
    Sua missão é compreender a pergunta fornecida pelo usuário e gerar uma resposta com o máximo de clareza a partir de somente um dos arquivos no formato de texto que se referem a esses procedimentos. Você precisa ser o mais claro possível em sua resposta. 

    #Instruções
    Analise a pergunta fornecida e compreenda ela em detalhes. Você pode associar a pergunta a somente um processo, ou seja,aquele que mais se encaixa na pergunta. Somente um arquivo no formato de texto que vai ser informado no tópico de arquivos deste prompt. A partir desse documento, gere uma resposta que pode tirar uma dúvida ou esclarecer algo sobre esse procedimento, no entanto, responda somente o que o usuário perguntar.Você pode utilizar tópicos para sua resposta, porém não usem caracteres especiais Não pule etapas e seja claro em sua resposta. Não esqueça de ser cordial no final e se disponibilizar para responder qualquer outra dúvida que o usuário tiver
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

# Flask
# configurando o Flask
app = Flask(__name__)

# rotas
@app.route('/')
def index():
    return render_template('index.html')

# quando recarrega a página reseta a contagem de requisições - isso é relacionado ao histórico
@app.route("/limparTerminal", methods=["POST"])
def limparTerminal():
    global cont_requisicao
    reiniciar = request.json["recarregadoPorBotao"]
    if reiniciar == True:
        cont_requisicao = 0
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "success"})

# manda o contexto, pergunta para ChatGpt e retorna a resposta, atualiza também o histórico
@app.route("/submit", methods=["POST"])
def submit():
    
    try:
        global cont_requisicao
        global prompt_sistema_resposta_api
        global lista_historico
        
        # requisição 1
        if(cont_requisicao == 0):
            prompt_sistema_resposta_api = texto
            pergunta_usuario = request.form['inputMessage']
                
            resposta = respostaApi(pergunta_usuario,prompt_sistema_resposta_api)
            cont_requisicao = 0 # == 1
            
            lista_historico[cont_requisicao] = f'''#CONVERSA ANTERIOR {cont_requisicao}
                -Solicitação anterior do usuário: {pergunta_usuario}
                -Resposta anterior: {resposta}""" '''
            
            return Response(stream_with_context(respostaApi(pergunta_usuario,prompt_sistema_resposta_api)), content_type='text/plain')
        
        # requisição 2
        elif(cont_requisicao == 1):
            prompt_sistema_resposta_api = texto
            pergunta_usuario = request.form['inputMessage']

            resposta = respostaApi(pergunta_usuario,prompt_sistema_resposta_api+lista_historico[cont_requisicao])
            cont_requisicao = 1 #== 2
            
            lista_historico[1] = f'''#CONVERSA ANTERIOR {cont_requisicao}
                -Solicitação anterior do usuário: {pergunta_usuario}
                -Resposta do Chat Valores: {resposta}""" '''
                
            return Response(stream_with_context(respostaApi(pergunta_usuario,prompt_sistema_resposta_api)), content_type='text/plain')

        # requisição 3
        else:
            prompt_sistema_resposta_api = texto
            pergunta_usuario = request.form['inputMessage']
                
            resposta = respostaApi(pergunta_usuario,prompt_sistema_resposta_api+lista_historico[cont_requisicao] + lista_historico[cont_requisicao-1])
            cont_requisicao = 2 #== 3
            
            lista_historico[2] = f'''#CONVERSA ANTERIOR {cont_requisicao}
                -Solicitação anterior do usuário: {pergunta_usuario}
                -Resposta do Chat Valores: {resposta}""" '''
            
            return Response(stream_with_context(respostaApi(pergunta_usuario,prompt_sistema_resposta_api)), content_type='text/plain')

    except Exception as e:
        error(e)
        return Response(stream_with_context(algo_ocorreu_de_errado()), content_type='text/plain')

# função quando dá erro
def algo_ocorreu_de_errado():
    yield "Algo ocorreu de errado, tente novamente"

# função que retorna a resposta do chatGpt sobre a pergunta
def respostaApi(pergunta_usuario, prompt_sistema_resposta_api):
    load_dotenv()
    
    for arq in (os.listdir("./bases")):
        prompt_sistema_resposta_api += f"{arq}" + open(f"./bases/{arq}","r",encoding="utf8").read() 
    
    tempo_de_espera = 5
    tentativas = 0
    try:
        while tentativas <3:
            tentativas+=1
            
            try:
            
                resposta = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": prompt_sistema_resposta_api
                        },
                        {
                            "role": "user",
                            "content": "Sua mensagem: " + pergunta_usuario
                        }
                    ],
                    temperature=1,
                    stream=True
                )
                
                print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
                print("Resposta feita com sucesso")
                print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

                for chunk in resposta:
                    if 'choices' in chunk and 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                        text = chunk['choices'][0]['delta']['content']
                        if text:
                            print(text, end="")
                            yield text

                return
            except openai.error.RateLimitError as e:
                error(e)
                print(f"Erro de limite de taxa: {e}")
                time.sleep(tempo_de_espera)
                tempo_de_espera *=2
            except openai.AuthenticationError as e:
                error(e)
                print(f"Erro de autentificação {e}")
            except openai.APIError as e:
                error(e)
                print(f"Erro de API {e}")
                time.sleep(5)
            
    except Exception as e:
        error(e)
        yield str(e)

if __name__ == '__main__':
    app.run(debug=True, port=5000)