const socket = io(); // Conecta ao servidor WebSocket
let clienteIdAtual = null;

// Carrega mensagens de um cliente
async function carregarMensagens(clienteId, element) {
    try {
        clienteIdAtual = clienteId;
        document.getElementById('enviar-btn').disabled = false;

        // Atualiza visualmente o cliente selecionado
        document.querySelectorAll('#clientes-list li').forEach(li => li.classList.remove('selected'));
        element.classList.add('selected');

        // Fetch de mensagens
        const response = await fetch(`/api/mensagens/${clienteId}`);
        const mensagens = await response.json();
        const mensagensContainer = document.querySelector('.messages');
        mensagensContainer.innerHTML = '';

        mensagens.forEach(msg => {
            const div = document.createElement('div');
            div.className = `message ${msg.tipo}`;
            div.innerHTML = `
                <span class="timestamp">${msg.data_envio}</span>
                <p><b>${msg.tipo === 'usuario' ? 'Cliente' : 'Atendente'}:</b> ${msg.texto}</p>
            `;
            mensagensContainer.appendChild(div);
        });

        // Atualiza o nome do cliente
        document.getElementById('cliente-nome').textContent = element.textContent;

    } catch (error) {
        console.error('Erro ao carregar mensagens:', error);
    }
}

// Envia mensagem pelo WebSocket
function enviarMensagem() {
    const input = document.getElementById('mensagem-input');
    const texto = input.value;

    if (texto.trim() === '') return;

    socket.emit('enviar_mensagem', { cliente_id: clienteIdAtual, texto });

    // Adiciona a mensagem localmente
    const mensagensContainer = document.querySelector('.messages');
    const div = document.createElement('div');
    div.className = 'message usuario';
    div.innerHTML = `<span class="timestamp">Agora</span><p><b>Você:</b> ${texto}</p>`;
    mensagensContainer.appendChild(div);

    input.value = '';
}

// Atualiza clientes em tempo real
socket.on('atualizar_clientes', (data) => {
    const clientesList = document.getElementById('clientes-list');
    clientesList.innerHTML = '';

    data.clientes.forEach(cliente => {
        const listItem = document.createElement('li');
        listItem.textContent = `${cliente.nome} - Última mensagem: ${cliente.ultima_mensagem}`;
        listItem.onclick = () => carregarMensagens(cliente.id, listItem);
        clientesList.appendChild(listItem);
    });
});

// Configurações de inicialização
document.getElementById('enviar-btn').onclick = enviarMensagem;
