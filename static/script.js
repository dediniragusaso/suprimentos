document.addEventListener('DOMContentLoaded', function () {
    // Verificar se o login já foi feito na sessão atual
    if (!sessionStorage.getItem('loggedIn')) {
        document.getElementById('loginOverlay').classList.remove('hidden');
        document.body.classList.add('blurred');
    }
 
    // Evento de envio do formulário de login
    document.getElementById('loginForm').addEventListener('submit', function (e) {
        e.preventDefault();
       
        let password = document.getElementById('password').value;
 
        fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json', // Mantenha o tipo de conteúdo como JSON
        },
        body: JSON.stringify({ password: password }), // Enviando como JSON
        }).then(response => {
            if (response.ok) { // Verifica se a resposta foi bem-sucedida
                sessionStorage.setItem('loggedIn', true); // Usa sessionStorage para expirar com o fechamento da aba
                document.getElementById('loginOverlay').classList.add('hidden');
                document.body.classList.remove('blurred'); // Remove o efeito de blur ao fazer login
            } else {
                return response.json().then(err => { // Captura o erro detalhado do servidor
                throw new Error(err.status || 'Falha ao fazer login'); // Lança erro com mensagem detalhada
            });
        }
        }) .catch((error) => {
            document.getElementById('errorMessage').style.display = 'block';
            console.error(error); // Log do erro para depuração
            });
        });
});
<<<<<<< HEAD


let isResponseIncreased = false;
let cont_requisicao = 0


=======
 
 
let isResponseIncreased = false;
let cont_requisicao = 0
 
 
>>>>>>> 752240aa043eb639969f0d57f13efecb27e33ace
// Ajusta a altura do input de mensagem conforme o conteúdo
document.getElementById("messageInput").addEventListener("input", function() {
    this.style.height = "auto";
    this.style.height = (this.scrollHeight) + "px";
});
 
// Verifica se a página foi recarregada por um botão específico
document.getElementById("novo_chat").addEventListener("click", function() {
    localStorage.setItem("recarregadoPorBotao", "true");
    window.location.reload();
});
 
// Verifica o recarregamento da página
function verificarRecarregamento() {
    if (localStorage.getItem("recarregadoPorBotao") === "true") {
        console.log("A página foi recarregada devido ao clique no botão.");
        localStorage.removeItem("recarregadoPorBotao");
        enviarResultadoParaBackend(true);
    } else {
        console.log("A página não foi recarregada devido ao clique no botão.");
        enviarResultadoParaBackend(false);
    }
}
 
// Envia o resultado do recarregamento para o backend
function enviarResultadoParaBackend(resultado) {
    fetch('/limparTerminal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ recarregadoPorBotao: resultado }),
    })
    .then(response => response.json())
    .then(data => console.log('Sucesso:', data))
    .catch((error) => {
        console.error('Erro:', error);
    });
}
 
// Executa a verificação de recarregamento quando o DOM é carregado
document.addEventListener("DOMContentLoaded", function() {
    verificarRecarregamento();
});
 
// Alterna a visibilidade da sidebar
document.getElementById("closeBtn").addEventListener("click", function() {
    var sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("-translate-x-full");
});
 
// Esconde o loader quando o DOM é carregado
document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("loanding_container").style.display = "none";
});
 
// Alterna a visibilidade do spinner (loader)
function toggleSpinnerVisibility() {
    var spinner = document.getElementById("loanding_container");
    spinner.style.display = spinner.style.display === "none" ? "flex" : "none";
}
 
// Desabilita a entrada de mensagem
function disableMessageInput() {
    document.getElementById("messageInput").disabled = true;
    document.getElementById("sendMessageButton").disabled = true;
}
 
// Habilita a entrada de mensagem
function enableMessageInput() {
    document.getElementById("messageInput").disabled = false;
    document.getElementById("sendMessageButton").disabled = false;
}
 
// Envia a mensagem e lida com a resposta contínua do servidor
function sendMessage(event) {
    event.preventDefault();
    isResponseIncreased = false;
    var inputMessage = document.getElementById("messageInput").value;
    if (!inputMessage) {
        return;
    }
 
    document.getElementById("logoContainer").style.display = "none";
    disableMessageInput();
    document.getElementById("loanding_container").style.display = "flex";
 
    var chatBox = document.getElementById("chatBox");
 
    addMessageToChatBox("user", inputMessage);
    document.getElementById("messageInput").value = "";
 
    fetch('/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `inputMessage=${encodeURIComponent(inputMessage)}&historico=${encodeURIComponent(sessionStorage.getItem("Historico"))}`
 
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let responseText = '';
 
        document.getElementById("loanding_container").style.display = "none";
 
        // Cria um novo contêiner para cada nova resposta
        const newChatContainer = document.createElement('div');
        newChatContainer.className = "chat-container";
        chatBox.appendChild(newChatContainer);
 
        function readStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    enableMessageInput();
                    console.log(responseText)
 
                    // atualizar histórico front
 
                    atualizarVariavel(responseText, inputMessage);
                    return;
                }
 
                responseText += decoder.decode(value, { stream: true });
                updateServerResponse(responseText, newChatContainer);
 
                readStream(); // Continue reading the stream
            }).catch(error => {
                console.error('Error reading stream:', error);
                document.getElementById("loanding_container").style.display = "none";
                enableMessageInput();
            });
        }
        readStream(); // Start reading the stream
 
    }).catch(error => {
        console.error('Error:', error);
        document.getElementById("loanding_container").style.display = "none";
        enableMessageInput();
    });
}
 
// Atualiza a resposta do servidor no chat
function updateServerResponse(response, container) {
    let serverMessage = container.querySelector('.server-message');
 
    if (!serverMessage) {
        serverMessage = document.createElement('div');
        serverMessage.className = "bg-gray-100 text-black text-left rounded-lg rounded-tl-none p-2 m-2 inline-block server-message";
        container.appendChild(serverMessage);
    }
 
    function replaceAlternatingStrongTags(message) {
        var count = 0;
        return message.replace(/\*\*/g, function() {
            count++;
            return count % 2 === 1 ? '<strong>' : '</strong>';
        });
    }
 
    function replaceHashesWithTitles(message) {
        return message.replace(/^### (.+)$/gm, '<h3>$1</h3>')
                      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
                      .replace(/^# (.+)$/gm, '<h1>$1</h1>');
    }
 
    function replaceHashesWithTitles(message) {
        return message.replace(/^### (.+)$/gm, '<h3>$1</h3>')
                      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
                      .replace(/^# (.+)$/gm, '<h1>$1</h1>');
    }
 
    function replaceLinkWithImg(message) {
        return message.replace(/(\.\/imagens\/[^\s]+)/g, '<img src="$1">');
    }
 
    function replaceMarkdownLinks(message) {
        return message.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a class="link_resposta" href="$2">$1</a>');
    }
 
    function replaceEmailWithLink(message) {
        return message.replace(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/g, '<a class="link_resposta"href="mailto:$1">$1</a>');
    }
   
    function formatMessage(message) {
        message = replaceAlternatingStrongTags(message);
        message = replaceHashesWithTitles(message);
        message = replaceLinkWithImg(message);
        message = replaceMarkdownLinks(message);
        message = replaceEmailWithLink(message);
        return message.replace(/\n/g, '<br>');
    }
 
    serverMessage.innerHTML = formatMessage(response);
 
    container.scrollTop = container.scrollHeight;
    document.getElementById("loanding_container").style.display = "none";
}
 
// Adiciona uma mensagem ao chat box
function addMessageToChatBox(sender, message) {
    var chatBox = document.getElementById("chatBox");
    var messageDiv = document.createElement("div");
    var messageContent = document.createElement("div");
 
    function replaceAlternatingStrongTags(message) {
        var count = 0;
        return message.replace(/\*\*/g, function() {
            count++;
            return count % 2 === 1 ? '<strong>' : '</strong>';
        });
    }
 
    function replaceHashesWithTitles(message) {
        return message.replace(/^### (.+)\n/gm, '<h3>$1</h3>\n')
                      .replace(/^## (.+)\n/gm, '<h2>$1</h2>\n')
                      .replace(/^# (.+)\n/gm, '<h1>$1</h1>\n');
    }
 
    function replaceLinkWithImg(message) {
        return message.replace(/(\.\/imagens\/[^\s]+)/g, '<img src="$1">');
    }
 
    function replaceMarkdownLinks(message) {
        return message.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a class="link_resposta" href="$2">$1</a>');
    }
 
    function replaceEmailWithLink(message) {
        return message.replace(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/g, '<a class="link_resposta" href="mailto:$1">$1</a>');
    }
 
    function formatMessage(message) {
        message = replaceAlternatingStrongTags(message);
        message = replaceHashesWithTitles(message);
        message = replaceLinkWithImg(message)
        message = replaceMarkdownLinks(message);
        message = replaceEmailWithLink(message);
        return message.replace(/\n/g, '<br>');
    }
 
    messageContent.innerHTML = formatMessage(message);
 
    messageDiv.appendChild(messageContent);
 
    if (sender === "user") {
        messageContent.className = "bg-gray-300 text-black text-right rounded-lg rounded-tr-none p-2 m-2 inline-block";
        messageDiv.className = "text-right";
    } else {
        messageContent.className = "bg-gray-100 text-black text-left rounded-lg rounded-tl-none p-2 m-2 inline-block";
        messageDiv.className = "text-left";
    }
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}
 
// Ajusta a altura do input de mensagem conforme o conteúdo
document.getElementById("messageInput").addEventListener("input", function() {
    this.style.height = "auto";
    var scrollHeight = this.scrollHeight;
    var maxHeight = parseInt(window.getComputedStyle(this).maxHeight, 10);
 
    if (scrollHeight > maxHeight) {
        this.style.height = maxHeight + "px";
        this.style.overflowY = "scroll";
    } else {
        this.style.height = scrollHeight + "px";
        this.style.overflowY = "hidden";
    }
});
 
// Adiciona eventos aos botões e inputs
/*document.getElementById("messageInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        atualizarVariavel()
    }
})*/
document.getElementById("sendMessageButton").addEventListener("click", sendMessage);  
 
document.getElementById("messageInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter" && !document.getElementById("messageInput").disabled) {
        event.preventDefault();
        sendMessage(event);
    }
});
 
document.getElementById("hamburgerBtn").addEventListener("click", function() {
    var sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("-translate-x-full");
});
 
document.getElementById("closeBtn").addEventListener("click", function() {
    document.getElementById("sidebar").classList.add("-translate-x-full");
});
 
document.addEventListener("click", function(event) {
    var sidebar = document.getElementById("sidebar");
    var hamburgerBtn = document.getElementById("hamburgerBtn");
    if (!sidebar.contains(event.target) && !hamburgerBtn.contains(event.target)) {
        sidebar.classList.add("-translate-x-full");
    }
});
 
document.getElementById("sidebar").addEventListener("click", function(event) {
    event.stopPropagation();
});
 
function criarVariavel() {
    sessionStorage.setItem('Historico', '')
}
 
function atualizarVariavel(resposta, pergunta) {
    // mensagens do sessionStorage
    let atualPergunta = pergunta
    let atualResposta = resposta
 
    let mensagem = ""
    let historico = sessionStorage.getItem("Historico")
    if (historico != undefined) {
        mensagem += historico
    }
 
    mensagem += "human: " + atualPergunta + "\nai: " + atualResposta + "\n"
    console.log(mensagem)
    sessionStorage.setItem('Historico', mensagem)          
}
 
window.addEventListener('load', criarVariavel())