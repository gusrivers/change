from flask import Flask, render_template, jsonify, request
import pymysql
import os

app = Flask(__name__)

# Configuração do banco de dados
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'crm'

# Função para criar uma conexão com o banco de dados
def get_db_connection():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

@app.route('/')
def index():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, nome, ultima_mensagem, ultima_mensagem_tempo FROM clientes")
    clientes = cursor.fetchall()

    connection.close()  # Feche a conexão após o uso

    return render_template('index.html', clientes=clientes)

@app.route('/mensagens/<int:cliente_id>', methods=['GET'])
def mensagens(cliente_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT texto, tipo FROM mensagens WHERE cliente_id = %s ORDER BY data_envio", (cliente_id,))
    mensagens = cursor.fetchall()

    connection.close()  # Feche a conexão após o uso

    return jsonify({'mensagens': [{'texto': msg[0], 'tipo': msg[1]} for msg in mensagens]})

@app.route('/enviar', methods=['POST'])
def enviar_mensagem():
    data = request.get_json()
    cliente_id = data['cliente_id']
    texto = data['texto']

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO mensagens (cliente_id, texto, tipo) VALUES (%s, %s, 'usuario')", (cliente_id, texto))
    connection.commit()

    connection.close()  # Feche a conexão após o uso

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
