from flask import Flask, request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime
from flask_cors import CORS
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/teste', methods=['GET'])
def teste():
    return "Hello World!"


@app.route('/login', methods=['POST'])
def login():
    try:
        raw = request.get_json()
        email = raw["login"]
        senha = raw["passw"]
        
        # Conexão com o banco de dados
        conn = mysql.connector.connect(host='127.0.0.1',
                                       database='testes',
                                        user='root',
                                    password='Admin123!@#')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM `pessoa` WHERE username = '" + email + "' AND value = '" + senha + "'")
        row = cursor.fetchone()
        
        

        if row:
            cursor.execute("INSERT INTO `radusergroup` (`username`, `groupname`) VALUES (%s, 'ILIMITADO');", (email,))
            conn.commit()
            return "1" #Usuario autenticado
        else: 
           return "0" # Usuário não autenticado
    except Error as e:
        print(e)
    return "Usuário ou senha inválidos!"

@app.route('/register', methods=['POST'])
def register():
    try:
        raw = request.get_json()
        name = raw["name"]
        email = raw["login"]
        senha = raw["passw"]
        now = datetime.now()
        date = now.strftime("%Y/%m/%d %H:%M:%S")

        connection = mysql.connector.connect(host='localhost',
                                        database='testes',
                                        user='root',
                                        password='Admin123!@#')
        if connection.is_connected():
                print("Connected to MySQL database")
                db_Info = connection.get_server_info()
                print("Connected to MySQL Server version ", db_Info)
                cursor = connection.cursor()
                cursor.execute("select database();")
                record = cursor.fetchone()
                print("You're connected to database: ", record)
                cursor.execute("""INSERT INTO `pessoa` (`name`, `login`, `passw`, `date`)
                VALUES (%s, %s, %s, %s)""",  (name, email, senha, date))
                connection.commit()
        return "1"
    except Error as e:
        print("Erro", e)
    return "0"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
