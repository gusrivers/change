from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import pymysql
import os
import requests

# Configuração do Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Conexão ao banco de dados
db = pymysql.connect(host='localhost', user='root', password='', database='crm')

# Variáveis da API do WhatsApp
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
WHATSAPP_URL = "https://graph.facebook.com/v17.0/YOUR_PHONE_NUMBER_ID/messages"

# Webhook para receber mensagens do WhatsApp
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data.get('entry'):
        for entry in data['entry']:
            for message in entry.get('changes', []):
                if 'messages' in message['value']:
                    for msg in message['value']['messages']:
                        cliente_id = msg['from']  # Número do cliente
                        mensagem = msg['text']['body']  # Conteúdo da mensagem
                        
                        # Salvar no banco de dados
                        cursor = db.cursor()
                        sql = "INSERT INTO mensagens (cliente_id, mensagem, enviado_por) VALUES (%s, %s, %s)"
                        cursor.execute(sql, (cliente_id, mensagem, 'cliente'))
                        db.commit()

                        # Emitir mensagem para o atendente
                        socketio.emit('mensagem', {
                            'cliente_id': cliente_id,
                            'mensagem': mensagem,
                            'usuario': 'cliente'
                        })
    return jsonify({"status": "success"}), 200

@app.route('/simular-mensagem', methods=['POST'])
def simular_mensagem():
    data = request.json
    cliente_id = data['cliente_id']
    mensagem = data['mensagem']

    # Salva a mensagem no banco como se viesse do WhatsApp
    cursor = db.cursor()
    sql = "INSERT INTO mensagens (cliente_id, mensagem, enviado_por) VALUES (%s, %s, %s)"
    cursor.execute(sql, (cliente_id, mensagem, 'cliente'))
    db.commit()

    # Atualiza atendente em tempo real
    socketio.emit('mensagem', {
        'cliente_id': cliente_id,
        'mensagem': mensagem,
        'usuario': 'Cliente'
    })
    return jsonify({"status": "success"}), 200


# Endpoint para enviar mensagens do atendente via WhatsApp
@app.route('/enviar-mensagem', methods=['POST'])
def enviar_mensagem():
    data = request.json
    cliente_id = data['cliente_id']
    mensagem = data['mensagem']

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": cliente_id,
        "type": "text",
        "text": {"body": mensagem}
    }

    response = requests.post(WHATSAPP_URL, json=payload, headers=headers)

    if response.status_code == 200:
        cursor = db.cursor()
        sql = "INSERT INTO mensagens (cliente_id, mensagem, enviado_por) VALUES (%s, %s, %s)"
        cursor.execute(sql, (cliente_id, mensagem, 'atendente'))
        db.commit()

        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "failed", "error": response.json()}), 400

# Página do atendente
@app.route('/atendente')
def atendente():
    return render_template('atendente.html')

# Histórico de mensagens de um cliente
@app.route('/historico/<cliente_id>')
def historico(cliente_id):
    cursor = db.cursor()
    sql = "SELECT mensagem, enviado_por, data_envio FROM mensagens WHERE cliente_id = %s ORDER BY data_envio"
    cursor.execute(sql, (cliente_id,))
    mensagens = cursor.fetchall()
    return jsonify(mensagens)

if __name__ == '__main__':
    socketio.run(app, debug=True)
