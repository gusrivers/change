from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
from werkzeug.security import check_password_hash
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)

# Configuração do banco de dados
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'crm'

# Configuração da chave secreta
app.secret_key = 'sua_chave_secreta'


# Função para criar uma conexão com o banco de dados
def get_db_connection():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor  # Retorna resultados como dicionários
    )


# Rota de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']  # Senha enviada pelo formulário
        
        # Conectar ao banco e verificar credenciais
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)  # Corrigido aqui
        cursor.execute('SELECT * FROM atendentes WHERE email = %s', (email,))
        atendente = cursor.fetchone()
        conn.close()
        
        # Comparar senha diretamente
        if atendente and atendente['senha'] == senha:  # Senha simples (texto puro)
            # Login bem-sucedido
            session['atendente_id'] = atendente['id']
            session['atendente_nome'] = atendente['nome']
            return redirect(url_for('index'))  # Redireciona para a página principal
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')

    return render_template('login.html')




# Página principal após login
@app.route('/index')
def index():
    if 'atendente_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', atendente_nome=session['atendente_nome'])


# Página de chat
@app.route('/chat')
def chat():
    if 'atendente_id' not in session:
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    connection.close()

    return render_template('chat.html', clientes=clientes)


# API para buscar mensagens
@app.route('/api/mensagens/<int:cliente_id>', methods=['GET'])
def get_mensagens(cliente_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT texto, tipo, data_envio FROM mensagens WHERE cliente_id = %s ORDER BY data_envio",
        (cliente_id,)
    )
    mensagens = cursor.fetchall()
    connection.close()

    mensagens_json = [
        {
            "texto": mensagem['texto'],
            "tipo": mensagem['tipo'],
            "data_envio": mensagem['data_envio'].strftime('%d/%m/%Y %H:%M') if mensagem['data_envio'] else None
        }
        for mensagem in mensagens
    ]
    return jsonify(mensagens_json)


# Rota para enviar mensagem
@app.route('/enviar', methods=['POST'])
def enviar_mensagem():
    if 'atendente_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    data = request.json
    cliente_id = data.get('cliente_id')
    texto = data.get('texto')

    if not cliente_id or not texto:
        return jsonify({"error": "Dados inválidos"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO mensagens (cliente_id, texto, tipo, data_envio) VALUES (%s, %s, %s, NOW())",
            (cliente_id, texto, 'atendente')  # 'tipo' marcado como 'atendente'
        )
        connection.commit()
    except Exception as e:
        print("Erro ao enviar mensagem:", e)
        return jsonify({"error": "Erro ao enviar mensagem"}), 500
    finally:
        connection.close()

    return jsonify({"success": True})


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Iniciar o servidor
if __name__ == '__main__':
    socketio.run(debug=True)
