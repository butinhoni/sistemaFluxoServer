import psycopg2
import segredos
import pandas as pd


def get_db_connection():
    conn = psycopg2.connect(
        database = segredos.database,
        password = segredos.passwd,
        host = segredos.host,
        port = segredos.port,
        user = segredos.user
    )
    return conn


def ler_tabela(nome):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM public.demandas_{nome}')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()

    df = pd.DataFrame(dados, columns=colunas)
    return(df)