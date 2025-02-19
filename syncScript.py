from flask import Flask, request, jsonify
import psycopg2
import segredos
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        database = segredos.database,
        user = segredos.user,
        password = segredos.passwd,
        host = segredos.host,
        port = segredos.port
    )
    return conn

@app.route('/sync', methods=['POST'])

def authenticate():
    data = request.json
    user = data.get('user')
    passwd = data.get('passwd')


    if not user or not passwd:
        return jsonify({'error': 'Por Favor, insira usuario e senha'}), 400
    

    conn = get_db_connection()
    cur = conn.cursor()

    query = sql.SQL("SELECT EXISTS(SELECT 1 FROM usuarios WHERE username = {} AND password = {})").format(
    sql.Literal(user),
    sql.Literal(passwd)
)
    
    cur.execute(query)
    result = cur.fetchone()[0]

    cur.close()
    conn.close()


    if result:
        return jsonify({'authorized': result}), 200
    else:
        return jsonify({'error': 'unauthorized'}), 400




if __name__ == 'main':
    app.run(host = '0.0.0.0', port=5000)