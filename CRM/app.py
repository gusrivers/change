from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import pymysql
import os
import requests
import mysql

app = Flask(__name__)

# Configuração do banco de dados
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'crm'

@app.route('/')
def index():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, nome, ultima_mensagem, ultima_mensagem_tempo FROM clientes")
    clientes = cursor.fetchall()

    return render_template('index.html', clientes=clientes)

@app.route('/mensagens/<int:cliente_id>', methods=['GET'])
def mensagens(cliente_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT texto, tipo FROM mensagens WHERE cliente_id = %s ORDER BY data_envio", (cliente_id,))
    mensagens = cursor.fetchall()

    return jsonify({'mensagens': [{'texto': msg[0], 'tipo': msg[1]} for msg in mensagens]})

@app.route('/enviar', methods=['POST'])
def enviar_mensagem():
    data = request.get_json()
    cliente_id = data['cliente_id']
    texto = data['texto']

    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO mensagens (cliente_id, texto, tipo) VALUES (%s, %s, 'usuario')", (cliente_id, texto))
    mysql.connection.commit()

    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(debug=True)