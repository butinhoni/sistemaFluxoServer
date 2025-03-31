import pandas as pd
import datetime

def reorganizarTabela(tabelaDemandas, tabelaFluxo, tabelaStatus):
    dados_tabela = {
        'demanda':[],
        'data':[],
        'status':[],
        'responsavel':[]
    }

    #data do dia
    today = datetime.datetime.now().date()

    for i, row in tabelaDemandas.iterrows():
        changes = tabelaStatus[tabelaStatus['id_demanda'] == i]
        people = tabelaFluxo[tabelaFluxo['demanda'] == i]
        data = row['data']
        status = 'A Iniciar'
        print(people)
        try:
            responsavel = people['destinatario'].iloc[0]
        except:
            responsavel = row['id_responsavel']
        while data <= today:
            _people = people[people['data'] == data]
            _changes = changes[changes['data'] == data]
            try:
                responsavel = _people['destinatario'].iloc[0]
            except:
                pass
            try:
                status = _changes['status_novo'].iloc[0]
            except:
                pass
            dados_tabela['data'].append(data)
            dados_tabela['demanda'].append(i)
            dados_tabela['responsavel'].append(responsavel)
            dados_tabela['status'].append(status)
            data = data + datetime.timedelta(1)

    dfFinal = pd.DataFrame(dados_tabela)
    print(dfFinal)
                
