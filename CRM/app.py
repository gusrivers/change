from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import pymysql
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app)

# Conexão ao banco de dados
db = pymysql.connect(host='localhost', user='root', password='', database='crm')

@app.route('/cliente/<int:cliente_id>')
def cliente(cliente_id):
    return render_template('cliente.html', cliente_id=cliente_id)

@app.route('/atendente')
def atendente():
    return render_template('atendente.html')

@socketio.on('mensagem')
def handle_mensagem(data):
    print(f"Mensagem recebida: {data}")

    # Salvar no banco de dados
    cursor = db.cursor()
    sql = "INSERT INTO mensagens (cliente_id, mensagem, enviado_por) VALUES (%s, %s, %s)"
    cliente_id = data.get('cliente_id', 1)  # Assuma um ID de cliente ou obtenha dinamicamente
    mensagem = data['mensagem']
    enviado_por = data['usuario']
    cursor.execute(sql, (cliente_id, mensagem, enviado_por))
    db.commit()

    # Emitir mensagem para todos os conectados (atendente e cliente)
    emit('mensagem', data, broadcast=True)

@app.route('/historico/<int:cliente_id>')
def historico(cliente_id):
    cursor = db.cursor()
    sql = "SELECT mensagem, enviado_por, data_envio FROM mensagens WHERE cliente_id = %s ORDER BY data_envio"
    cursor.execute(sql, (cliente_id,))
    mensagens = cursor.fetchall()
    return jsonify(mensagens)

if __name__ == '__main__':
    socketio.run(app, debug=True)
