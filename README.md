
# Chat de Suprimentos

Um chatbot desenvolvido para que os colaboradores das empresas do Grupo J&F possam tirar dúvidas de forma rápida e prática sobre a área de Suprimentos da JBS. Por meio deste chat, será possível obter respostas sobre os procedimentos da área e as normas envolvidas.


## Demonstração

Segue um vídeo com uma breve demonstração do chat em funcionamento e, logo abaixo, uma imagem de como está o front do chat atualmente.

https://institutogerminare-my.sharepoint.com/:v:/g/personal/sophia_ragusa_germinare_org_br/EQrBp5eUFGRLqTmwGs3TRgEBUTePl7TWxIfEoJtPrtjekQ

No vídeo, a primeira pergunta é relacionada diretamente com um dos documentos. Já a segunda pergunta é baseada em uma norma. Por fim, a terceira pergunta não está relacionada ao objetivo principal da ferramenta, ou seja, não deve ser respondida.

![Descrição da imagem](https://drive.google.com/uc?id=10vBjFOgrmwkd51Y9MCb2UVeljR_MAXT8)



## Estrutura

![Chat Suprimentos Arquitetura](https://drive.google.com/uc?id=1_U0IZdCc3NibzK8gozaAGJX425OQteoF)



## Informações importantes


Inicialmente, são 16 bases relacionadas aos procedimentos de Suprimentos. Para reduzir o uso de tokens, cada procedimento é representado por cem palavras-chave, que são utilizadas pelo primeiro agente para tomar sua decisão. Com a identificação do procedimento relacionado à pergunta do usuário, outro agente responde à pergunta com base exclusivamente no documento correspondente.

Dentro do sistema, é verificado se a resposta apresenta alguma norma em sua composição, uma vez que os nomes das normas seguem um padrão. Caso uma norma seja identificada, um último chatbot analisa o documento da norma para complementar a resposta criada, enviando, então, a resposta final ao usuário.
