from flask import Flask, request
from flask_mysqldb import MySQL
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/testes', methods=['GET'])
def testes():
    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='testes',
                                             user='root',
                                             password='root')
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print("You're connected to database: ", record)
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
    return 'Conexão com o banco de dados realizada com sucesso!'
