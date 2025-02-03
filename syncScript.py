from flask import Flask, request, jsonify
import psycopg2
import segredos

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

def sync_data():
    data = request.json

    if not data:
        return jsonify({'error': 'sem dados recebidos'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for item in data:
            cursor.execute(
                '''
                INSERT INTO levantamentos (id, date, latitude, longitude, tipo, contrato, responsavel, problema, fotos)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET date = EXCLUDED.date, latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude, tipo = EXCLUDED.tipo, contrato = EXCLUDED.contrato, responsavel = EXCLUDED.responsavel, problema = EXCLUDED.problema, fotos = EXCLUDED.fotos
                ''', (item['id'], item['date'], item['latitude'], item['longitude'], item['tipo'], item['contrato'], item['resposavel'], item['problema'], item['fotos'])
            )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Dados Sincronizados com sucesso'}), 200
    except Exception as e:
        return jsonify({'error':str(e)}), 500

if __name__ == 'main':
    app.run(host = '0.0.0.0', port=5000)