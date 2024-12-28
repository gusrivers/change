from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
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

class Clientes(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    origem = db.Column(db.String(50), nullable=True)  # Origem do cliente (e.g., redes sociais)
    ultima_mensagem = db.Column(db.Text, nullable=True)  # Última mensagem enviada ou recebida
    ultima_mensagem_tempo = db.Column(db.DateTime, nullable=True)  # Data e hora da última mensagem
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    mensagens = db.relationship('Mensagem', back_populates='cliente', lazy=True)

class Atendente(db.Model):
    __tablename__ = 'atendentes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)  # Senha armazenada como hash
    ativo = db.Column(db.Boolean, default=True)  # Define se o atendente está ativo
    mensagens = db.relationship('Mensagem', back_populates='atendente', lazy=True)

    # Métodos para gerenciar hash da senha
    def set_password(self, senha):
        """Define o hash da senha"""
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        """Verifica se a senha fornecida corresponde ao hash"""
        return check_password_hash(self.senha_hash, senha)

class Mensagem(db.Model):
    __tablename__ = 'mensagens'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    atendente_id = db.Column(db.Integer, db.ForeignKey('atendentes.id'), nullable=True)
    mensagem = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Enum('usuario', 'atendente'), nullable=False)
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente = db.relationship('Clientes', back_populates='mensagens')
    atendente = db.relationship('Atendente', back_populates='mensagens')


class DistribuicaoDeLeads(db.Model):
    __tablename__ = 'distribuicao_de_leads'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)  # Corrigido para 'cliente.id'
    atendente_id = db.Column(db.Integer, db.ForeignKey('atendente.id'), nullable=False)
    distribuido_em = db.Column(db.DateTime, default=func.now())


class StatusLead(db.Model):
    __tablename__ = 'status_do_lead'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)  # Corrigido para 'cliente.id'
    status = db.Column(
        db.Enum('Novo', 'Contato Inicial', 'Negociação', 'Vendido', 'Perdido', 'Remarketing'),
        nullable=False
    )
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

@app.route('/api/mensagens/<int:cliente_id>', methods=['GET'])
def get_mensagens(cliente_id):
    mensagens = (
        Mensagem.query
        .filter_by(cliente_id=cliente_id)
        .order_by(Mensagem.enviado_em)
        .all()
    )
    return jsonify([
        {
            'id': msg.id,
            'cliente_id': msg.cliente_id,
            'atendente_id': msg.atendente_id,
            'texto': msg.mensagem,
            'tipo': 'usuario' if msg.atendente_id is None else 'atendente',
            'data_envio': msg.enviado_em.strftime('%Y-%m-%d %H:%M:%S')
        }
        for msg in mensagens
    ])




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

@app.route('/api/atendentes')
def listar_atendentes():
    atendentes = Atendente.query.all()
    response = [
        {
            'id': atendente.id,
            'nome': atendente.nome,
            'email': atendente.email,
            'ativo': atendente.ativo
        }
        for atendente in atendentes
    ]
    return jsonify({'atendentes': response})


def criar_atendente(nome, email, senha):
    atendente = Atendente(
        nome=nome,
        email=email,
        ativo=True
    )
    atendente.set_password(senha)
    db.session.add(atendente)
    db.session.commit()
    return atendente

def autenticar_atendente(email, senha):
    atendente = Atendente.query.filter_by(email=email).first()
    if atendente and atendente.check_password(senha):
        if not atendente.ativo:
            return {'erro': 'Atendente inativo.'}
        return {'sucesso': 'Login realizado com sucesso!', 'atendente': atendente.nome}
    return {'erro': 'Email ou senha inválidos.'}

def alterar_status_atendente(atendente_id, ativo):
    atendente = Atendente.query.get(atendente_id)
    if atendente:
        atendente.ativo = ativo
        db.session.commit()
        return {'sucesso': f'Status atualizado para {"ativo" if ativo else "inativo"}.'}
    return {'erro': 'Atendente não encontrado.'}


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

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    try:
        cliente_id = data['cliente_id']
        texto = data['texto']
        atendente_id = data['atendente_id']

        # Cria a mensagem no banco de dados
        mensagem = Mensagem(
            cliente_id=cliente_id,
            atendente_id=atendente_id,
            mensagem=texto,
            tipo='atendente'
        )
        db.session.add(mensagem)

        # Atualiza o cliente com a última mensagem
        cliente = Clientes.query.get(cliente_id)
        if cliente:
            cliente.ultima_mensagem = texto
            cliente.ultima_mensagem_tempo = datetime.utcnow()

        db.session.commit()

        # Emite a mensagem para o cliente
        emit('nova_mensagem', {
            'cliente_id': cliente_id,
            'texto': texto,
            'tipo': 'atendente',
            'data_envio': mensagem.enviado_em.strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)
    except Exception as e:
        print("Erro ao enviar mensagem:", e)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------ INICIAR SERVIDOR ------------------

if __name__ == '__main__':
    socketio.run(app, debug=True)