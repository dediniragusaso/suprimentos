
# Chat de Suprimentos / Suply chain Chatbot

Um chatbot desenvolvido para que os colaboradores das empresas do Grupo J&F possam tirar dúvidas de forma rápida e prática sobre a área de Suprimentos da JBS. Por meio deste chat, será possível obter respostas sobre os procedimentos da área e as normas envolvidas.

--------------------------------------------------------------------------------------------------------------------------------------------------------------

A chatbot developed so that the employes of the companies from Group J&F can ask questions about the suply chain of JBS in a faster and more pratical way. Through this chat, it is possible to get answers about the procedures and the regulations envolved.


## Demonstração / Demonstration

Segue um vídeo com uma breve demonstração do chat em funcionamento.

https://institutogerminare-my.sharepoint.com/:v:/g/personal/sophia_ragusa_germinare_org_br/EQrBp5eUFGRLqTmwGs3TRgEBUTePl7TWxIfEoJtPrtjekQ

No vídeo, a primeira pergunta é relacionada diretamente com um dos documentos. Já a segunda pergunta é baseada em uma norma. Por fim, a terceira pergunta não está relacionada ao objetivo principal da ferramenta, ou seja, não deve ser respondida.

![Vídeo de demonstração](https://drive.google.com/uc?id=10vBjFOgrmwkd51Y9MCb2UVeljR_MAXT8)

--------------------------------------------------------------------------------------------------------------------------------------------------------------

In this section, there is a video available with a small demonstration of the system working.

The first question shown in the video is directily related to a procedure of the derpatment. The second question is based in a regulation and the third is not related to any of the main objetives of the tool, because of that, the question remains unresponded and the chatbot puts itself at service for any other doubts.

![Demonstration video](https://drive.google.com/uc?id=10vBjFOgrmwkd51Y9MCb2UVeljR_MAXT8)


## Estrutura/ Structure

![Chat Suprimentos Arquitetura](https://drive.google.com/uc?id=1_U0IZdCc3NibzK8gozaAGJX425OQteoF)



## Informações importantes / Important information


Inicialmente, são 16 bases relacionadas aos procedimentos de Suprimentos. Para reduzir o uso de tokens, cada procedimento é representado por cem palavras-chave, que são utilizadas pelo primeiro agente para tomar sua decisão. Com a identificação do procedimento relacionado à pergunta do usuário, outro agente responde à pergunta com base exclusivamente no documento correspondente.

Dentro do sistema, é verificado se a resposta apresenta alguma norma em sua composição, uma vez que os nomes das normas seguem um padrão. Caso uma norma seja identificada, um último chatbot analisa o documento da norma para complementar a resposta criada, enviando, então, a resposta final ao usuário.


--------------------------------------------------------------------------------------------------------------------------------------------------------------


Initially, the system has 16 documents of the supplies procedures. To optimize token usage, each procedure is represented by 100 keywords, which is what the first agent uses to categorize the user's question. After identifying the procedure related to what was asked, another agent responds based fully on the corresponding document.

In the back end of the system, it is checked whether the answer includes any regulations, as regulation names follow a standardized pattern. If a regulation is identified, a final chatbot analyzes its document to enhance the response before delivering it to the user, making it clearer for the employes of the group.
