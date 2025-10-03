from flask import Flask, request, jsonify, make_response, send_file, abort
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
import pandas as pd
import treatments
import db_connector as db
from PIL import Image
import io

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

api_token = segredos.api_token

def get_db_connection():
    conn = psycopg2.connect(
        database = segredos.database,
        password = segredos.passwd,
        host = segredos.host,
        port = segredos.port,
        user = segredos.user
    )
    return conn



def authenticate(user, passwd):
  
    conn = get_db_connection()
    cur = conn.cursor()

    query = sql.SQL('SELECT EXISTS(SELECT 1 FROM public.usuarios WHERE "user" = {} AND senha = {})').format(
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

@app.route('/get_med_ind-hashrandom1234', methods = ['GET'])
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


@app.route('/get_contr-hashrandom1234', methods = ['GET'])
def get_contr():
    try:
        conn = get_db_connection()

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT ic, fantasia, rodovia FROM public.contratos WHERE ativo = true')

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error':str(e)}), 500



@app.route('/get_people-hashrandom1234', methods = ['GET'])
def get_people():
    try:
        conn = get_db_connection()

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT id, nome, cargo, primeiro_nome, "user" FROM public.usuarios')

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@app.route('/post_ensaiotsd-hashrandom1234', methods = ['POST'])
def post_ensaiotsd():

    data = request.json

    if not data:
        return jsonify({'error': 'sem dados recebidos'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        for item in data:
            item['data_ensaio'] = pd.to_datetime(item['data_ensaio'], dayfirst=True)
            item['data_ensaio'] = item['data_ensaio'].strftime('%Y-%m-%d')
            if 'Brita' in item['etapa']:
                item['material'] = 'BRITA'
            elif 'Imprima' in item['etapa']:
                item['material'] = 'EAI'
            cur.execute(
                '''
                INSERT INTO public.ensaiostsd (
                contrato, 
                "data", 
                longitude, 
                latitude, 
                estaca_inicial, 
                estaca_final, 
                etapa, 
                material, 
                largura, 
                posicao, 
                largura_bandeja, 
                comprimento_bandeja, 
                peso_inicial, 
                peso_final, 
                taxa)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (item['contrato'], item['data_ensaio'], item['longitude'], item['latitude'], item['estaca_inicial'], item['estaca_final'], item['etapa'], item['material'], item['largura'], item['posicao'],
                item['largura_badeja'], item['comprimento_bandeja'], item['peso_inicial'], item['peso_final'], item['taxa'])
            )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Dados sincronizados com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/post_lev-especial-hashrandom1234', methods = ['POST'])
def post_lev_esp():
    data = request.json

    if not data:
        return jsonify({'error':'sem dados recebidos'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        for item in data:
            cur.execute(
                '''
                INSERT INTO public.lev_especial(
                    "id",
                    km,
                    panelas,
                    remendos,
                    trincamentos,
                    drenagem,
                    sin_horizontal,
                    sin_vertical,
                    rocada,
                    erosao,
                    interferencia,
                    oae,
                    latitude,
                    longitude
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (item['id'],
                      item['km'],
                      item['panelas'],
                      item['remendos'],
                      item['trincamento'],
                      item['drenagem'],
                      item['horizontal'],
                      item['vertical'],
                      item['rocada'],
                      item['erosao'],
                      item['interferencia'],
                      item['oae'],
                      item['latitude'],
                      item['longitude'])
            )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Dados enviados'}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app.route('/post_ocorrencia-hashrandom1234', methods = ['POST'])
def post_ocorrencia():

    data = request.json

    if not data:
        return jsonify({'error': 'sem dados recebidos'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        for item in data:
            cur.execute(
                '''
                INSERT INTO public.levantamentos (
                latitude,
                longitude,
                tipo,
                contrato,
                responsavel,
                problema,
                fotos,
                date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (item['latitude'], item['longitude'], item['tipo'], item['contrato'], item['responsavel'], item['ocorrencia'], item['fotos'], item['data'])
            )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Dados sincronizados com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/post_pictures-hashrandom1234', methods = ['POST'])
def post_pictures():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error':'Nome de arquivo vazio'}), 400
    
    if file and file.filename.endswith('.jpg'):
        image_folder = '/home/guilherme/sistemas/checklist_engevvia/images_ocorrencias'
        filepath = os.path.join(image_folder, file.filename)
        file.save(filepath)
        return jsonify({'message': 'Arquivo Salvo com sucesso', 'filepath': filepath}), 200
    else:
        return jsonify({'error':'Formato de arquivo invalido'})

@app.route('/get_levantamentos_retro-hashrandom1234', methods = ['GET'])
def get_lev_retro():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
                    SELECT id, rodovia, crescente, decrescente, vertical, horizontal
                    FROM public.retro_levantamentos
                    WHERE ativo = true'''
                    )

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_placas_retro-hashrandom1234', methods = ['GET'])
def get_placas():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
                    SELECT id, km, posicao, mensagem, sentido, fabricacao, fabricante, largura, altura, formato, imagem, id_levantamento, obs, latitude, longitude
                    FROM public.retro_placas
                    '''
                    )

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_leituras_retro-hashrandom1234', methods = ['GET'])
def get_leituras():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
                    SELECT id, id_placa, cor, tipo, m1, m2, m3, m4, m5, "data"
                    FROM public.retro_leituras
                    '''
                    )

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_diario-demandas-hashrandom1234', methods = ['GET'])
def diarioDemandas():
    try:
        print('lendo')
        fluxo = db.ler_tabela('demandas_transferencias')
        demandas = db.ler_tabela('demandas')
        demandas = demandas.set_index('id')
        status = db.ler_tabela('demandas_status')
        dados = treatments.reorganizarTabela(demandas,fluxo,status).to_json(orient='table')

        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_demandas-hashrandom1234', methods = ['GET'])
def demandas():
    try:
        dados = db.ler_tabela('demandas')
        dados['id'] = dados['id'].astype(str)
        dados = dados.to_json(orient = 'table')
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_demandas-status-hashrandom1234', methods = ['GET'])
def demandas_status():
    try:
        dados = db.ler_tabela('demandas_status')
        dados['id_demanda'] = dados['id_demanda'].astype(str)
        dados = dados.to_json(orient = 'table')
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_demandas-fluxo-hashrandom1234', methods = ['GET'])
def demandas_fluxo():
    try:
        dados = db.ler_tabela('demandas_transferencias')
        dados['demanda'] = dados['demanda'].astype(str)
        dados = dados.to_json(orient = 'table')
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == 'main':
    app.run(host = '0.0.0.0', port=5000)

@app.route('/get_ensaios_solos-hashrandom1234', methods = ['GET'])
def get_ensaios_solos():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
                    SELECT *
                    FROM public.ensaios_solos
                    '''
                    )

        result = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/get_ensaios_cbuq-hashrandom1234', methods = ['GET'])
def get_ensaios_cbuq():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
                    SELECT *
                    FROM public.ensaios_cbuq
                    '''
                    )

        result = cur.fetchall()
        print(result)
        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_ensaios_concreto-hashrandom1234', methods = ['GET'])
def get_ensaios_concreto():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
                    SELECT *
                    FROM public.ensaios_concreto
                    '''
                    )

        result = cur.fetchall()
        print(result)
        cur.close()
        conn.close()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/placas-<placa>', methods = ['GET'])
def get_image(placa):
    image_path = os.path.join('images/placas', placa)
    if not os.path.exists(image_path):
        return abort(404)
    try:
        with Image.open(image_path) as img:
            img.thumbnail((300,200))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality = 75)
            buffer.seek(0)
            return send_file(buffer, mimetype = 'image/jpeg')
    except Exception as e:
        return abort(500, description=str(e))


def check_token():
    token = request.args.get('token') or request.headers.get('Authorization')
    return token == api_token

@app.route('/ler_tabela', methods = ['GET'])
def get_tabela():
    if not check_token:
        return jsonify({'error': 'Token Inválido'})
    
    tabela = request.args.get('tabela')
    if not tabela:
        return jsonify ({'error': 'insira a tabela'})
    
    df = db.ler_tabela(tabela)

    df = df.fillna('null')

    df = df.to_json(orient='table', default_handler=str)

    return jsonify(df)

@app.route('/postar_coisas_020', methods = ['POST'])
def post020():
    data = request.json
    if not data:
        abort(400, description = "Bad Requeste: JSON body is required")
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('''
        INSERT INTO public.lev_020(
                    levantamento, numero, foto)
                    VALUES(%s, %s, %s)
    ''', data['tipo'], data['numero'], data['foto']
    )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message':'Ocorrencia cadastrada com sucesso'}), 200
    except psycopg2.Error as e:
        print(e)
        conn.rollback()
        abort(500, description=f'Database Error {e}')
        return jsonify({'error':'erro no cadastro do ponto'}), 500
