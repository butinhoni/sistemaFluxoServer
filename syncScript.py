from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import(
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies
)
import psycopg2
import segredos
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from dotenv import load_dotenv
import os

#merged

load_dotenv('.env')

app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY') #chave para assinar os tokens
app.config['JWT_TOKEN_LOCATION'] = ['cookies'] #armazenar tokens em cookies
app.config['JWT_COOKIE_CSRF_PROTECT'] = False #proteger contra csrf - ver se arrumo isso depois
app.config['JWT_COOKIE_SECURE'] = False #depois do certbot mudar para TRUE
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 900 # token de acesso
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 604800 #7 dias para o token de refresh

jwt = JWTManager(app)

def get_db_connection():
    conn = psycopg2.connect(
        database = segredos.database,
        user = segredos.user,
        password = segredos.passwd,
        host = segredos.host,
        port = segredos.port
    )
    return conn



def authenticate(user, passwd):
  
    conn = get_db_connection()
    cur = conn.cursor()

    query = sql.SQL("SELECT EXISTS(SELECT 1 FROM public.usuarios WHERE nome = {} AND passwd = {})").format(
    sql.Literal(user),
    sql.Literal(passwd)
)
    
    cur.execute(query)
    result = cur.fetchone()[0]

    cur.close()
    conn.close()


    if result:
        return True
    else:
        return False

@app.route('/auth', methods=['POST'])
def login():

    data = request.json
    user = data.get('user')
    passwd = data.get('passwd')

    if not user or not passwd:
        return jsonify({'error': 'Por Favor, insira usuario e senha'}), 400


    if authenticate(user, passwd):
        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)

        response = jsonify({'msg':'Usuário Logado'})

        set_access_cookies(response, access_token)
        set_refresh_cookies(response,refresh_token)

        print(response)

        return response

    else:
        return jsonify({'error': 'senha incorreta'}), 401

@app.route('/check_auth', methods = ['GET'])
@jwt_required()
def checar_user():
    current_user = get_jwt_identity()
    return jsonify ({'user':f'{current_user}'})

@app.route('/user_refresh', methods = ['POST'])
@jwt_required(refresh=True)
def refresh_login():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    response = jsonify({'msg':'token de acesso atualizado'})
    set_access_cookies(response, new_access_token)
    return response

@app.route('/get_med_ind', methods = ['GET'])
def get_med_ind():
    try:
        conn = get_db_connection()

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM public.contr_indicadores')

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error':str(e)}), 500


if __name__ == 'main':
    app.run(host = '0.0.0.0', port=5000)