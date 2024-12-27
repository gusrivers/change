from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
from werkzeug.security import check_password_hash
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func

# Configuração da aplicação Flask
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configuração do banco de dados com SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/crm'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Instâncias do SQLAlchemy e SocketIO
db = SQLAlchemy(app)

# ------------------ MODELOS DO BANCO DE DADOS ------------------

class Mensagem(db.Model):
    __tablename__ = 'mensagens'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    atendente_id = db.Column(db.Integer, db.ForeignKey('atendente.id'), nullable=False)
    mensagem = db.Column(db.String(500))
    tipo = db.Column(db.String(20))
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Usando backref para referenciar as classes
    cliente = db.relationship('Cliente', backref='mensagens')  # De 'Cliente' para 'Mensagem'
    atendente = db.relationship('Atendente', backref='mensagens')  # De 'Atendente' para 'Mensagem'


class Clientes(db.Model):
    __tablename__ = 'cliente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    origem = db.Column(db.String(50), nullable=True)
    criado_em = db.Column(db.DateTime, default=func.now(), nullable=False)
    ultima_mensagem = db.Column(db.Text, nullable=True)
    ultima_mensagem_tempo = db.Column(db.DateTime, nullable=True)

    # Mensagens são referenciadas aqui
    mensagens = db.relationship('Mensagem', backref='cliente', lazy=True)  # Relacionamento com 'Mensagem'


class Atendente(db.Model):
    __tablename__ = 'atendente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    # Mensagens são referenciadas aqui
    mensagens = db.relationship('Mensagem', backref='atendente', lazy=True)  # Relacionamento com 'Mensagem'

class DistribuicaoDeLeads(db.Model):
    __tablename__ = 'distribuicao_de_leads'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)  # Corrigido para 'clientes.id'
    atendente_id = db.Column(db.Integer, db.ForeignKey('atendente.id'), nullable=False)
    distribuido_em = db.Column(db.DateTime, default=func.now())

class StatusLead(db.Model):
    __tablename__ = 'status_do_lead'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)  # Corrigido para 'clientes.id'
    status = db.Column(db.Enum('Novo', 'Contato Inicial', 'Negociação', 'Vendido', 'Perdido', 'Remarketing'), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

# ------------------ ROTAS ------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']  

        atendente = Atendente.query.filter_by(email=email).first()
        if not email or not senha:
            flash("Preencha todos os campos.", "error")
        elif atendente and check_password_hash(atendente.senha_hash, senha):
            session['atendente_id'] = atendente.id
            session['atendente_nome'] = atendente.nome
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')

    return render_template('login.html')

@app.route('/index')
def index():
    if 'atendente_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', atendente_nome=session['atendente_nome'])

@app.route('/chat')
def chat():
    if 'atendente_id' not in session:
        return redirect(url_for('login'))
    
    clientes = Clientes.query.all()
    lista_clientes = [
        {
            'id': cliente.id,
            'nome': cliente.nome,
            'ultima_mensagem': cliente.ultima_mensagem or "Nenhuma mensagem",
            'ultima_mensagem_tempo': cliente.ultima_mensagem_tempo.strftime('%d/%m/%Y %H:%M') if cliente.ultima_mensagem_tempo else "Não disponível",
            'origem': cliente.origem
        }
        for cliente in clientes
    ]

    print('Emitindo dados para o cliente:', lista_clientes)
    
    # Emitir dentro do evento de conexão
    socketio.emit('atualizar_clientes', {'clientes': lista_clientes})
    
    return render_template('chat.html', clientes=clientes)

@app.route('/api/mensagens/<int:cliente_id>')
def mensagens(cliente_id):
    try:
        mensagens = Mensagem.query.filter_by(cliente_id=cliente_id).all()
        mensagens_data = [
            {
                'tipo': msg.tipo,
                'texto': msg.mensagem,  # Corrigido o campo de 'texto' para 'mensagem'
                'data_envio': msg.enviado_em.strftime('%d/%m/%Y %H:%M')
            }
            for msg in mensagens
        ]
        return jsonify(mensagens_data)  # Certifique-se de retornar um array JSON válido
    except Exception as e:
        print(f"Erro ao carregar mensagens para o cliente {cliente_id}: {e}")
        return jsonify({'error': 'Erro ao carregar mensagens'}), 500


@app.route('/api/clientes', methods=['GET'])
def get_clientes():
    pagina = request.args.get('pagina', 1, type=int)
    tamanho_pagina = request.args.get('tamanho', 10, type=int)

    clientes_query = Clientes.query.order_by(Clientes.ultima_mensagem_tempo.desc())
    clientes_paginados = clientes_query.paginate(page=pagina, per_page=tamanho_pagina, error_out=False)

    clientes_json = [
        {
            "id": cliente.id,
            "nome": cliente.nome,
            "ultima_mensagem": cliente.ultima_mensagem or "Nenhuma mensagem",
            "ultima_mensagem_tempo": cliente.ultima_mensagem_tempo.strftime('%d/%m/%Y %H:%M') if cliente.ultima_mensagem_tempo else "Não disponível"
        }
        for cliente in clientes_paginados.items
    ]

    return jsonify({
        "clientes": clientes_json,
        "pagina_atual": clientes_paginados.page,
        "total_paginas": clientes_paginados.pages,
        "total_clientes": clientes_paginados.total
    })

@app.route('/enviar', methods=['POST'])
def enviar_mensagem():
    if 'atendente_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    data = request.json
    cliente_id = data.get('cliente_id')
    texto = data.get('texto')

    if not cliente_id or not texto:
        return jsonify({"error": "Dados inválidos"}), 400

    nova_mensagem = Mensagem(cliente_id=cliente_id, mensagem=texto, tipo='atendente')
    db.session.add(nova_mensagem)

    cliente = Clientes.query.get(cliente_id)
    cliente.ultima_mensagem = texto
    cliente.ultima_mensagem_tempo = datetime.now()

    db.session.commit()

    return jsonify({"success": True})

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado ao WebSocket')
    clientes = Clientes.query.all()
    lista_clientes = [
        {
            'id': cliente.id,
            'nome': cliente.nome,
            'ultima_mensagem': cliente.ultima_mensagem or "Nenhuma mensagem",
            'ultima_mensagem_tempo': cliente.ultima_mensagem_tempo.strftime('%d/%m/%Y %H:%M') if cliente.ultima_mensagem_tempo else "Não disponível",
            'origem': cliente.origem
        }
        for cliente in clientes
    ]
    socketio.emit('atualizar_clientes', {'clientes': lista_clientes})


@socketio.on('entrar_fila')
def entrar_fila(data):
    cliente_id = data.get('id')
    cliente_na_fila = StatusLead.query.filter_by(cliente_id=cliente_id, status='na fila').first()
    if not cliente_na_fila:
        novo_status = StatusLead(cliente_id=cliente_id, status='na fila')
        db.session.add(novo_status)
        db.session.commit()
        atualizar_fila()
    emit('confirmacao_fila', {'mensagem': 'Cliente adicionado à fila!'})

def atualizar_fila():
    clientes_na_fila = db.session.query(StatusLead, Clientes).join(Clientes).filter(StatusLead.status == 'na fila').all()
    fila_formatada = [
        {
            'id': status_lead.cliente_id,
            'nome': cliente.nome,
            'hora': status_lead.atualizado_em.strftime('%d/%m/%Y %H:%M')
        }
        for status_lead, cliente in clientes_na_fila
    ]
    socketio.emit('atualizar_fila', {'fila': fila_formatada}, broadcast=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------ INICIAR SERVIDOR ------------------

if __name__ == '__main__':
    socketio.run(app, debug=True)