import streamlit as st
import pandas as pd
import math
import re
import psycopg2
from psycopg2 import sql
import folium
import simplekml
from exif import Image
import os
import segredos



def open_conn():
    conn = psycopg2.connect(database = segredos.database,
                        user = segredos.usuario,
                        host = segredos.endereco,
                        password = segredos.password,
                        port = 5432)
    return conn

@st.cache_data
def leitor_med(arquivo):


#Função que lê o arquivo e puxa as sheets
    def get_list(file):
        xl = pd.ExcelFile(file)
        list = xl.sheet_names
        return(list)


    def getitem(df, busca):
            for i, row in df.iterrows():
                list = df.loc[i, :].values.flatten().tolist()
                column = 0
                linha = -1
                for item in list:
                    column +=1
                    if str(item).find(busca)>=0:
                        linha = i
                        coluna = column
                        break
                if linha != -1:
                    break
            dado_cell = df.iloc[linha,coluna-1]
            if dado_cell.find("/20")>=0 and busca == "Contrato":
                return(dado_cell)
            dado_cell = df.iloc[linha,coluna]
            try:
                while math.isnan(dado_cell):
                    coluna += 1
                    dado_cell = df.iloc[linha,coluna]
            except:
                pass
            return(dado_cell)


    #acha qual a planilha correta para trabalhar
    def find_sheet(sheet_list):
        i = 0
        resumos = []
        sheet_name = ""
        for sheet in sheet_list:
            if sheet.find("CONSOLIDADA PI") >=0:
                sheet_name = "CONSOLIDADA PI"
            if sheet.find("RESUMO")>=0 or sheet.find("Resumo")>=0 or sheet.find("MEDIÇÃO")>=0:
                resumos.append(sheet)
        if len(resumos) == 1:
            sheet_name = resumos[0]
        elif len(resumos) > 0:
            sheet_name_reserva = resumos[0]
            for sheet in sheet_list:
                if sheet.find("REAJ")!=-1 or sheet.find("reaj") != -1:
                    try:
                        resumos.remove(sheet)
                    except:
                        pass
            for sheet in sheet_list:
                if sheet.find("Diário")!=-1 or sheet.find("DIÁRIO")!= -1:
                    try:
                        resumos.remove(sheet)
                    except:
                        pass           
        if len(resumos) == 1:
            sheet_name = resumos[0]
        else:
            for sheet in sheet_list:
                if sheet.find("MEDIÇÃO")<0 and sheet.find("medição")<0:
                    try:
                        resumos.remove(sheet)
                    except:
                        pass
        if len(resumos) == 1:
            sheet_name = resumos[0]   
        if sheet_name == "" :
            for sheet in sheet_list:
                if sheet.find("MEDIÇÃO")>0:
                    resumos.append(sheet)
        if sheet_name == "" :
            try:
                sheet_name = resumos[0]
            except: 
                print(file)
                sheet_name = sheet_name_reserva
        return(sheet_name)


    def find_start(df):
        linha = -1
        for i, row in df.iterrows():
            list = df.loc[i,:].values.flatten().tolist()
            for item in list:
                if linha != -1:
                    break
                if str(item).find("CÓDIGO")>=0 or str(item).find("NID")>=0 or str(item).find("UND.")>=0 or str(item).find("Cód")>=0:
                    linha = i
                    break
        return(linha)

    #arruma o cabeçalho
    def find_header(df, linha):
        quant = 0
        df2 = df.iloc[linha:,:]
        header = df.iloc[0]
        header = header.tolist()
        return([df2,header])

    #arruma as quantidades mescladas
    def fix_quant(df, header):
        header2 = header
        quant = 0
    #corrige a parte das quantidades se estiver mesclada
        for i in range(len(header)-1):
            valor = str(header[i]).upper()
            n=i+1
            if (valor.find("QUANT")>=0 or valor.find("FÍSICO")>=0 or valor.find("F  Í  S  I  C  O")>=0 or valor.find("RPFO")>=0) and quant == 0  and header[i+1] == "Vazio":
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":                 
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                header2[i] = f"{header[i]}_{df.iloc[1,i]}"
                i = i+4
                quant = 1
        return(header2)


    def fix_valor(df, header):
        header2 = header
        value = 0


    #corrige a parte dos qvalores se estiver mesclada
        for i in range(len(header)-1):
            valor = str(header[i]).upper()
            n=i+1
            if (valor.find("VALOR")>=0 or valor.find("Valor")>=0 or valor.find("PREÇO")>=0) and value == 0  and header[i+1] == "Vazio":
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":                 
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                header2[i] = f"{header[i]}_{df.iloc[1,i]}"
                i = i+4
                value = 1
        return(header2)

    #ajeita os nomes todos
    def rename_columns(header):
        header2 = header
        quant = 0
        cod = 0
        value = 0 
        print('começou----------------')
        print(header2)
        for i in range(len(header)):
            quanttemp = 0
            valor = str(header[i]).upper()
            if valor.find("CÓD")>=0 or valor.find("COD")>=0  or valor.find("Cod")>=0 and cod == 0:
                header2[i] = "COD"
                cod = 1
            if valor.find("DISC")>=0 or valor.find("DESC")>=0 or valor.find("SERVI")>=0:
                header2[i] = "DESCRICAO"
            if valor.find("UNID")>=0 or valor.find("UND")>=0:
                header2[i] = "UNID"
            if valor.find("VALOR")== -1 and (valor.find("CONTRAT")>=0 or valor.find("TOTAL")>=0) and quant == 0 and (valor.find("QUANT")>=0 or valor.find("QTD")>=0 or valor.find("F  Í  S  I  C  O")>=0):
                header2[i] = "QUANT_TOTAL"
                quant = 1
                quanttemp = 1
            if quant == 0 and valor.find("QUANT")>=0 and valor.find("1°")<0:
                header2[i] = 'QUANT_TOTAL'
            if valor.find("VALOR")== -1 and (valor.find("NESTA")>=0 or valor.find("ATUAL")>=0 or valor.find("PRESENTE")>=0) and quanttemp == 0:
                header2[i] = "QUANT_MED_ATUAL"
            if valor.find("VALOR")== -1 and (valor.find("ANT.")>=0 or valor.find("ANTERIOR")>=0):
                header2[i] = "QUANT_ANTERIOR"
            if valor.find("VALOR")== -1 and (valor.find("ACUM")>=0 or valor.find("CONFEÊNCIA")>=0) and valor.find("ANTERIOR") == -1:
                header2[i] = "QUANT_ACUMULADA"
            if (valor.find("PREÇO")>=0) and valor.find("UNIT")>=0:
                header2[i] = "VALOR_UNIT"
                value = 1
            elif valor.find("VALOR")>=0 and valor.find("UNIT)")>=0 and value == 0:
                header2[i] = "VALOR UNIT"
        if cod == 0:
            for i in range(len(header)):
                valor = valor = str(header[i]).upper()
                if valor.find("ITEM")>=0:
                    header2[i] = "COD"
        print('------------antiga------------')
        print(header)
        print('-----------nova------------')
        print(header2)
        return(header2)

    #cria a lista de colunas que vamos puxar da medição
    def create_table(df,header):
        valid_columns = ['COD','DESCRICAO','UNID','QUANT_TOTAL','QUANT_MED_ATUAL','QUANT_ANTERIOR','QUANT_ACUMULADA','VALOR_UNIT']
        df2 = df[1:]
        df2.columns = header
        if 'COD' not in df2.columns:
            df2['COD'] = 'S/Cod'
        resumo_med = df2[valid_columns]
        resumo_med = resumo_med.loc[:,~resumo_med.columns.duplicated(keep='first')]
        return(resumo_med)
        
       

    #pegar a etapa do serviço
    def get_stage(df):
        resumo_med = df
        etapa1 = "Vazio"
        etapa = "Vazio"
        data=[]
        colunas_checar = ['QUANT_MED_ATUAL','QUANT_ANTERIOR','QUANT_ACUMULADA','VALOR_UNIT']
        
        for i, row in resumo_med.iterrows():
            if row["QUANT_TOTAL"] == "Vazio":
                check = 0
                if row["DESCRICAO"] != "Vazio":
                    for col in colunas_checar:
                        if row[col] != 'Vazio':
                            check += 1
                    if check == 0:
                        etapa1 = resumo_med.loc[i,"DESCRICAO"]
                elif row['COD'] != 'Vazio' and 'fiscal' not in row['COD'].lower():
                    for col in colunas_checar:
                        if row[col] != 'Vazio':
                                check += 1
                    if check == 0:
                        etapa1 = resumo_med.loc[i,"COD"]


            data.append(etapa1)


        resumo_med["ETAPA"] = data
        return(resumo_med)

    def table_filter(df):
        resumo_med = df
        resumo_med = resumo_med.query('QUANT_TOTAL != "Vazio"')
        resumo_med = resumo_med.query('UNID != "Vazio"')
        resumo_med["MES"] = mes
        resumo_med["CONTRATO"] = ic
        resumo_med["DATA_BASE"] = data_base
        #resumo_med["FILE"] = file
        return(resumo_med)


    #tab daqui pra cima
    file = arquivo

    #busca a lista de sheets
    list = get_list(file)


    #acha a sheet certa
    try:
        sheet = find_sheet(list)
    except ValueError as e:
        print(f"{file} erro na na hora de achar a lista")
        #print(e)



    #cria a tabela
    try:
        df = pd.read_excel(file,sheet)
        print(sheet)
    except:
        print(f"{arquivo}erro pra criar a tabela")


    #busca os itens no cabeçalho
    try:
        ic = getitem(df, "Contrato")
        if "115/2022" in ic:
            sheet = "CONSOLIDADA PI"
            df = pd.read_excel(file,sheet)
        data_base = getitem(df, "Data")
        mes = getitem(df, "Simp")

        #arruma o ic
        ic = re.sub("[^0-9]", "",ic)
        ic = ic[:3]+"/"+ic[3:]
        ic = ic.replace("0000","")


        if isinstance(mes,str):
            index = mes.find('/') - 2
            mes = mes[index:]
            mes = mes[:10]
        try:
            mes = pd.to_datetime(mes, format="%d/%m/%Y")
        except:
            print(f'{ic} {mes} mes errado')



    except ValueError as e:
        print(f"{file} erro achando dados")
        print(e)
        

    #acha a linha certa
    try:
        linha = find_start(df)
    except:
        print(f"{file} erro achando linha certa")
        

    #trocando os vazios por string para facilitar comparações
    try:
        df = df.fillna("Vazio")
    except:
        print(f"{file} erro trocando vazios")
        

    #corta o cabeçalho e acha os titulos
    try:
        df = find_header(df, linha)[0]
        header = find_header(df, linha)[1]
    except:
        print(f"{file} erro na parte de cortar o cabeçalho")
        

    #arruma a parte mesclada das quantidades 
    try:
        header = fix_quant(df,header)
    except:
        print(f"{file} erro ajeitando a parte das quantidades que vem mesclada")
        #print(e)
        

    #arruma a parte mesclada do valor 
    try:
        header = fix_valor(df,header)
    except:
        print(f"{file} erro ajeitando a parte dos valores que vem mesclada")
        #print(e)
        
    #renomeia as colunas
    try:
        header = rename_columns(header)
    except:
        print(f"{file} erro renomeando as colunas")
    
    #cria a nova tabela, já apenas com as colunas corretas
    try:
        resumo_med = create_table(df, header)
    except Exception as e:
        print(f"{file} erro filtrando as colunas - {e}")
        exit()
    


    #separa a etapa do serviço num canto
    try:
        resumo_med = get_stage(resumo_med)
    except ValueError as e:
        print(f"{file} erro na parte de buscar a etapa do serviço")
        print(e)
    

    #filtra só que a gente quer da tabela
    try:
        resumo_med = table_filter(resumo_med)
    except:
        print(f"{file} erro na parte de filtrar as linhas úteis")
        
    resumo_med['VALOR_UNIT']=pd.to_numeric(resumo_med['VALOR_UNIT'], errors='coerce')
    resumo_med['QUANT_TOTAL']=pd.to_numeric(resumo_med['QUANT_TOTAL'], errors='coerce')
    resumo_med['QUANT_MED_ATUAL']=pd.to_numeric(resumo_med['QUANT_MED_ATUAL'], errors='coerce')
    resumo_med['QUANT_ANTERIOR']=pd.to_numeric(resumo_med['QUANT_ANTERIOR'], errors='coerce')
    resumo_med['QUANT_ACUMULADA']=pd.to_numeric(resumo_med['QUANT_ACUMULADA'], errors='coerce')
    resumo_med['CONTRATO'] = resumo_med['CONTRATO'].str.replace('399/2014','399/2014 (PT02465)')
    return([resumo_med,ic,mes])


@st.cache_data
def ler_ind():
    conn = psycopg2.connect(database = segredos.database,
                user = segredos.usuario,
                host = segredos.endereco,
                password = segredos.password,
                port = 5432)

    cur = conn.cursor()
    cur.execute('SELECT * FROM public.contr_indicadores')
    colunas = ['ic', 'mes', 'valor_pi', 'valor_r', 'valor_recebido', 'data_recebido', 'data_entrega', 'valor_entrega_pi', 'periodo','ano','dias','valor_entrega_r']
    data = cur.fetchall()
    df = pd.DataFrame(data, columns=colunas)
    df['periodo'] = df['periodo'].str.title()
    df['mes'] = df['mes'].str.lower()
    cur.close()
    conn.close()
    return(df)

@st.cache_data
def ler_aprov():
    conn = psycopg2.connect(database = segredos.database,
                user = segredos.usuario,
                host = segredos.endereco,
                password = segredos.password,
                port = 5432)

    cur = conn.cursor()

    colunas = ["ic",'mes','data','status']

    cur.execute('SELECT * FROM public.aprovacoes')
    data = cur.fetchall()
    df = pd.DataFrame(data, columns = colunas)
    cur.close()
    conn.close()
    return(df)

@st.cache_data
def ler_check():
    conn = psycopg2.connect(database = segredos.database,
                user = segredos.usuario,
                host = segredos.endereco,
                password = segredos.password,
                port = 5432)
    cur = conn.cursor()

    colunas = ["receb", "contrato", "nao-conf", "cronograma", "boletim", "canteiro", "adm_local", "taxa_betume", "ensaios", "jazidas", "drenagem", "contr.ambiental", "controle_geometrico", "obs", "mes", "data", "valor", "aceito", "valor_nosso", "ano"]

    cur.execute('SELECT * FROM public.med_check')
    data = cur.fetchall()
    df = pd.DataFrame(data, columns = colunas)
    cur.close()
    conn.close()
    return(df)

@st.cache_data
def ler_nao_conf():
    conn = psycopg2.connect(database = segredos.database,
                user = segredos.usuario,
                host = segredos.endereco,
                password = segredos.password,
                port = 5432)
    cur = conn.cursor()

    colunas = ['N','Data','Contrato','NATUREZA','GRAU','ARQUIVO DO RELATÓRIO','ATENDIDA','PROBLEMA','REGIAO','TIPO_VIA','CAUSA','MED_CORRETIVA','LAT','LON']
    cur.execute('SELECT * FROM public.nao_conf')
    data = cur.fetchall()
    df = pd.DataFrame(data, columns = colunas)
    cur.close()
    conn.close()
    return(df)

@st.cache_data
def ler_contr():
    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)
    cur = conn.cursor()

    colunas = ["IC", "EMPRESA", "RODOVIA", "EMPRESA2", "REEF", "RPFO", "PREV", "ATIVO"]

    cur.execute('SELECT * FROM public.contratos')
    data = cur.fetchall()

    df = pd.DataFrame(data, columns= colunas)
    cur.close()
    conn.close()
    return(df)

@st.cache_data
def ler_periodos():
    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)
    cur = conn.cursor()

    colunas = ['m','inicio','fim','nmes','ano','periodo']

    cur.execute('SELECT * FROM public.periodos')
    data = cur.fetchall()
    df = pd.DataFrame(data, columns = colunas)
    cur.close()
    conn.close()
    return(df)

def aprovar_med(ic,mes,data):
    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)
    cur = conn.cursor()
    mes = mes.lower()
    cur.execute(f""" INSERT INTO public.aprovacoes(
                ic, mes, data, status)
                VALUES ('{ic}', '{mes}', '{data}', 'aprovada');
                """)
    cur.close()
    conn.commit()
    conn.close()

def desaprovar_med(ic,mes,data):
    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)
    cur = conn.cursor()

    cur.execute(f""" INSERT INTO public.aprovacoes(
                ic, mes, data, status)
                VALUES ('{ic}', '{mes}', '{data}', 'aguardando aprovação');
                """)
    cur.close()
    conn.commit()
    conn.close()


def up_med(df):
    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)
    print('conectado')
    cur = conn.cursor()
    print(df)

    for i, row in df.iterrows():
        cod = row['COD']
        descricao = row['DESCRICAO']
        descricao = descricao.replace("'"," ")
        unid = row['UNID']
        quant_total = row['QUANT_TOTAL']
        quant_med_atual = row['QUANT_MED_ATUAL']
        quant_anterior = row['QUANT_ANTERIOR']
        quant_acumulada = row['QUANT_ACUMULADA']
        valor_unit = row['VALOR_UNIT']
        etapa = row['ETAPA']
        mes = row['MES']
        contrato = row['CONTRATO']
        contrato = contrato.replace('/','-')
        data_base = row['DATA_BASE']
        cur.execute(f"""INSERT INTO public.medicoes(
	                                                cod, contrato, descricao, etapa, mes, quant_acum, quant_ant, quant_med, quant_total, unid, valur_unit) 
                    VALUES('{cod}','{contrato}','{descricao}','{etapa}','{mes}','{quant_acumulada}','{quant_anterior}','{quant_med_atual}','{quant_total}','{unid}','{valor_unit}')""");
                                                                                                                                                    

    print('lançado')

    conn.commit()
    cur.close()
    conn.close()

    print('feito')

@st.cache_data
def ler_cron():
    conn = psycopg2.connect(database = segredos.database,
                user = segredos.usuario,
                host = segredos.endereco,
                password = segredos.password,
                port = 5432)

    cur = conn.cursor()
    cur.execute('SELECT * FROM public.cronogramas')
    dados = cur.fetchall()
    colunas = ["ic","data","valor","etapa"]
    df = pd.DataFrame(data = dados, columns = colunas)
    return(df)

def up_check(df):
    df['valor'] = pd.to_numeric(df['valor'])
    df['valor_nosso'] = pd.to_numeric(df['valor_nosso'])

    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)

    print('conectado')
    cur = conn.cursor()

    for i, row in df.iterrows():
        print(i)
        data_receb = row['receb']
        contrato = row['contrato']
        nao_conf = row['nao-conf']
        cron = row['cronograma']
        boletim = row['boletim']
        canteiro = row['canteiro']
        adm_local = row['adm_local']
        taxa = row['taxa_betume']
        ens = row['ensaios']
        jazidas = row['jazidas']
        drenagem = row['drenagem']
        ca = row['contr.ambiental']
        cg = row['controle_geometrico']
        print(cg)
        obs = row['obs']
        mes = row['mes']
        data = row['data']
        valor_pi = row['valor']
        aceito = bool(True)
        valor_r = row['valor_nosso']
        ano = row['ano']
        cur.execute(f"INSERT INTO public.med_check(data_receb,contrato,nao_conf,cronograma,boletim,canteiro,adm_local,taxa_betume,ensaios,jazidas,drenagem,c_ambiental,c_geometrico,obs,mes,data,valor_pi,aceito,valor_r, ano) VALUES('{data_receb}','{contrato}','{nao_conf}','{cron}','{boletim}','{canteiro}','{adm_local}','{taxa}','{ens}','{jazidas}','{drenagem}','{ca}','{cg}','{obs}','{mes}','{data}',{valor_pi},{aceito},'{valor_r}',{ano})");
                                                                                                                                                    

    print('lançado')

    conn.commit()
    cur.close()
    conn.close()

    print('feito')

# cria o mapa
def map_create(fotos, description, name):
    lat_list = []
    lon_list = []
    fotos_list = []
    kml = simplekml.Kml()
    i = 0
    # pega coordenadas das fotos
    for img in fotos:
        i += 1
        foto = img.read()
        try:
            my_image = Image(foto)
            lat = my_image.gps_latitude
            lon = my_image.gps_longitude
        except:
            continue
        lat_dec = -(((lat[2]/60+lat[1])/60)+lat[0])
        lon_dec = -(((lon[2]/60+lon[1])/60)+lon[0])

        #cria a tabela que vai pro folium
        lat_list.append(lat_dec)
        lon_list.append(lon_dec)
        fotos_list.append(foto)
        # joga as coordenadas pro kmz
        point = kml.newpoint(name = name, coords = [(lon_dec,lat_dec)])
        point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/ltblu-blank.png'
        point.style.balloonstyle.bgcolor= simplekml.Color.lightblue
        with open(f'foto_temp{str(i)}.png','wb') as foto_temp:
            foto_temp.write(img.getbuffer())
        picpath = kml.addfile(f'foto_temp{str(i)}.png')
        point.description = '<img src="' + picpath +'" alt="picture" width="400" height="300" align="left" />' + description

    # joga as coordenadas na tabela
    locs = pd.DataFrame({
        'lat':lat_list,
        'lon':lon_list,
        'desc':foto
    })
    # cria o mapa
    mapa_folium = folium.Map(tiles = 'openstreetmap',
                            zoom_start=11,
                            location=[lat_list[0], lon_list[0]])
                            

    # coloca imagens de satelite
    tile = folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Satelite',
        overlay = False,
        control = True
        ).add_to(mapa_folium)



    for i2, row2 in locs.iterrows():
        folium.Marker(location=(row2['lat'],row2['lon'])).add_to(mapa_folium)
    
    folium.LayerControl().add_to(mapa_folium)
    
    kml.savekmz('kmz.kmz')
    mapa_folium.save('map.html')
    i = 0
    dir = os.getcwd()
    for foto in fotos:
        i += 1
        try:
            os.remove(os.path.join(dir,f'foto_temp{str(i)}.png'))
        except:
            pass
    return(kml, mapa_folium)

def up_pont_crit(df1):
    df = df1[['MÊS',
         'Nº P.C.',
         'REGIÃO',
         'DATA EXPEDIDA',
         'RODOVIA',
         'COORDENADAS',
         'Unnamed: 13',
         'VIA',
         'DISCIPLINA',
         'GRAU',
         'PONTE',
         'OCORRÊNCIA',
         'POSSÍVEL CAUSA ',
         'MEDIDA CORRETIVA E/OU PREVENTIVA',
         'IMPACTOS GERADOS',
         'SITUAÇÃO']]

    df.columns = ['MÊS',
            'Nº P.C.',
            'REGIÃO',
            'DATA EXPEDIDA',
            'RODOVIA',
            'LATITUDE',
            'LONGITUDE',
            'VIA',
            'DISCIPLINA',
            'GRAU',
            'PONTE',
            'OCORRÊNCIA',
            'POSSÍVEL CAUSA ',
            'MEDIDA CORRETIVA E/OU PREVENTIVA',
            'IMPACTOS GERADOS',
            'SITUAÇÃO']
    #df = df[['DATA DA EXPEDIÇÃO', 'Nº NC','REGIÃO','VIA','I.C.','DISCIPLINA','GRAU','PROBLEMA IDENTIFICADO','POSSÍVEL CAUSA','MEDIDA CORRETIVA','LATITUDE','LONGITUDE']]


    df['LATITUDE'] = df['LATITUDE'].str.replace(' ','')
    df['LATITUDE'] = df['LATITUDE'].str.replace('º',';')
    df['LATITUDE'] = df['LATITUDE'].str.replace('°',';')
    df['LATITUDE'] = df['LATITUDE'].str.replace('’',';')
    df['LATITUDE'] = df['LATITUDE'].str.replace('”',';')
    df['LATITUDE'] = df['LATITUDE'].str.replace("'",';')
    df['LATITUDE'] = df['LATITUDE'].str.replace('"',';')


    df['LATITUDE'] = df['LATITUDE'].str.split(';')

    lat_dec_list = []

    for i, row in df.iterrows():
        try:
            grau = abs(pd.to_numeric(row['LATITUDE'][0]))
        except:
            grau = 0

        try:    
            m = pd.to_numeric(row['LATITUDE'][1])
        except:
            m = 0

        try:
            s = pd.to_numeric(row['LATITUDE'][2])
        except:
            s = 0
        dec = (grau + m/60 + s/3600)*-1
        if dec == 0:
            try:
                dec = row['LATITUDE'][0]
                dec = dec.replace('S','')
                dec = dec.replace(',','.')
                dec = pd.to_numeric(dec)
            except:
                pass
        lat_dec_list.append(dec)

    df['latitude_decimal'] = lat_dec_list


    df['LONGITUDE'] = df['LONGITUDE'].str.replace(' ','')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('º',';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace("'",';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('"',';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('°',';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('’',';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('”',';')


    df['LONGITUDE'] = df['LONGITUDE'].str.split(';')

    lon_dec_list = []

    for i, row in df.iterrows():
        try:
            grau = abs(pd.to_numeric(row['LONGITUDE'][0]))
        except:
            grau = 0

        try:    
            m = pd.to_numeric(row['LONGITUDE'][1])
        except:
            m = 0

        try:
            s = pd.to_numeric(row['LONGITUDE'][2])
        except:
            s = 0
        dec = (grau + m/60 + s/3600)*-1
        if dec == 0:
            try:
                dec = row['LONGITUDE'][0]
                dec = dec.replace('W','')
                dec = dec.replace(',','.')
                dec = pd.to_numeric(dec)
            except:
                pass
        lon_dec_list.append(dec)

    df['LONGITUDE_decimal'] = lon_dec_list

    df = df.dropna(thresh=5)

    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)

    print('conectado')
    cur = conn.cursor()

    print(df)
    for i, row in df.iterrows():
        id_pc = row['Nº P.C.']
        reg = row['REGIÃO']
        data = row['DATA EXPEDIDA']
        rod = row['RODOVIA']
        lat = row['latitude_decimal']
        lon = row['LONGITUDE_decimal']
        tipo_via = row['VIA']
        nat = row['DISCIPLINA']
        nat = nat.replace("'",' ')
        grau = row['GRAU']
        ponte = row['PONTE']
        oco = row['OCORRÊNCIA']
        oco = oco.replace("'",'')
        causa = row['POSSÍVEL CAUSA ']
        try:
            causa = causa.replace("'",' ')
        except:
            pass
        correcao = row['MEDIDA CORRETIVA E/OU PREVENTIVA']
        try:
            correcao = correcao.replace("'", ' ')
        except:
            pass
        impact = row['IMPACTOS GERADOS']
        sit = row['SITUAÇÃO']

        cur.execute(f"""INSERT INTO public.ponto_crit(
        id, regiao, data, rodovia, lat, lon, tipo_via, natureza, grau, ponte, ocorrencia, causa, correcao, impactos, situacao)
        VALUES ('{id_pc}', '{reg}', '{data}', '{rod}', '{lat}', '{lon}', '{tipo_via}', '{nat}', '{grau}', '{ponte}', '{oco}', '{causa}', '{correcao}', '{impact}', '{sit}')""");


    cur.close()
    conn.commit()
    conn.close()

def up_nao_conf(df1):
    df = df1[['DATA DA EXPEDIÇÃO', 'Nº NC','REGIÃO','VIA','I.C.','DISCIPLINA','GRAU','PROBLEMA IDENTIFICADO','POSSÍVEL CAUSA','MEDIDA CORRETIVA','LATITUDE','LONGITUDE','SITUAÇÃO']]


    df['LATITUDE'] = df['LATITUDE'].str.replace(' ','')
    df['LATITUDE'] = df['LATITUDE'].str.replace('º',';')
    df['LATITUDE'] = df['LATITUDE'].str.replace("'",';')
    df['LATITUDE'] = df['LATITUDE'].str.replace('"',';')


    df['LATITUDE'] = df['LATITUDE'].str.split(';')

    lat_dec_list = []

    for i, row in df.iterrows():
        try:
            grau = abs(pd.to_numeric(row['LATITUDE'][0]))
        except:
            grau = 0

        try:    
            m = pd.to_numeric(row['LATITUDE'][1])
        except:
            m = 0

        try:
            s = pd.to_numeric(row['LATITUDE'][2])
        except:
            s = 0
        dec = (grau + m/60 + s/3600)*-1
        
        lat_dec_list.append(dec)

    df['latitude_decimal'] = lat_dec_list


    df['LONGITUDE'] = df['LONGITUDE'].str.replace(' ','')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('º',';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace("'",';')
    df['LONGITUDE'] = df['LONGITUDE'].str.replace('"',';')


    df['LONGITUDE'] = df['LONGITUDE'].str.split(';')

    lon_dec_list = []

    for i, row in df.iterrows():
        try:
            grau = abs(pd.to_numeric(row['LONGITUDE'][0]))
        except:
            grau = 0

        try:    
            m = pd.to_numeric(row['LONGITUDE'][1])
        except:
            m = 0

        try:
            s = pd.to_numeric(row['LONGITUDE'][2])
        except:
            s = 0
        dec = (grau + m/60 + s/3600)*-1
        lon_dec_list.append(dec)

    df['LONGITUDE_decimal'] = lon_dec_list

    conn = psycopg2.connect(database = segredos.database,
                            user = segredos.usuario,
                            host = segredos.endereco,
                            password = segredos.password,
                            port = 5432)

    print('conectado')
    cur = conn.cursor()

    print(df)

    for i, row in df.iterrows():
        data_da_expedicao = row['DATA DA EXPEDIÇÃO']
        num_nc = row['Nº NC']
        regiao = row['REGIÃO']
        via = row['VIA']
        ic = row['I.C.']
        ic = ic.replace("/",'-')
        ic = ic.replace("013-2018","113-2022")
        ic = ic.replace("399-2014",'399-2014 (PT02465)')
        disciplina = row['DISCIPLINA']
        grau = row['GRAU']
        problema_identificado = row['PROBLEMA IDENTIFICADO'].replace("'",'')
        try:
            possivel_causa = row['POSSÍVEL CAUSA'].replace("'",'')
        except:
            pass
        try:
            medida_corretiva = row['MEDIDA CORRETIVA'].replace("'",'')
        except:
            pass
        latitude = row['LATITUDE']
        longitude = row['LONGITUDE']
        latitude_decimal = row['latitude_decimal']
        longitude_decimal = row['LONGITUDE_decimal']
        situacao = row['SITUAÇÃO']
        if situacao == 'RESOLVIDO':
            atend = bool(True)
        else:
            atend = bool(False)
        


        cur.execute(f"""INSERT INTO public.nao_conf(
                                                    id, data, contrato, natureza, grau, arquivo, atendida, problema, regiao, tipo_via, causa, med_corretiva, lat, lon)
                                                    VALUES ('{num_nc}', '{data_da_expedicao}', '{ic}', '{disciplina}', '{grau}', 'file', '{atend}', '{problema_identificado}', '{regiao}','{via}', '{possivel_causa}', '{medida_corretiva}', '{latitude_decimal}', '{longitude_decimal}')""");

    cur.close()
    conn.commit()
    conn.close()

def leitor_med_cba(arquivo):


#Função que lê o arquivo e puxa as sheets
    def get_list(file):
        xl = pd.ExcelFile(file)
        list = xl.sheet_names
        return(list)


    def getitem(df, busca):
            for i, row in df.iterrows():
                list = df.loc[i, :].values.flatten().tolist()
                column = 0
                linha = -1
                for item in list:
                    column +=1
                    if str(item).find(busca)>=0:
                        linha = i
                        coluna = column
                        break
                if linha != -1:
                    break
            dado_cell = df.iloc[linha,coluna-1]
            if dado_cell.find("/20")>=0 and busca == "Contrato":
                return(dado_cell)
            dado_cell = df.iloc[linha,coluna]
            try:
                while math.isnan(dado_cell):
                    coluna += 1
                    dado_cell = df.iloc[linha,coluna]
            except:
                pass
            return(dado_cell)


    #acha qual a planilha correta para trabalhar
    def find_sheet(sheet_list):
        i = 0
        resumos = []
        sheet_name = ""
        if 'MEDIÇÃO' in sheet_list:
            return('MEDIÇÃO')
        for sheet in sheet_list:
            sheet2 = sheet.upper()
            if sheet2.find("MEDIÇÃO")>=0:
                resumos.append(sheet)
        if len(resumos) == 1:
            sheet_name = resumos[0]
        elif len(resumos) > 0:
            sheet_name_reserva = resumos[0]
            for sheet in sheet_list:
                sheet2 = sheet.upper()
                if "PM" in sheet2:
                    return(sheet)
                if sheet.find("REAJ")!=-1 or sheet.find("ATRATIVA") != -1:
                    try:
                        resumos.remove(sheet)
                    except:
                        pass
            for sheet in sheet_list:
                if sheet.find("Diário")!=-1 or sheet.find("DIÁRIO")!= -1:
                    try:
                        resumos.remove(sheet)
                    except:
                        pass           
        if len(resumos) == 1:
            sheet_name = resumos[0]
        else:
            for sheet in sheet_list:
                if sheet.find("MEDIÇÃO")<0:
                    try:
                        resumos.remove(sheet)
                    except:
                        pass
        if len(resumos) == 1:
            sheet_name = resumos[0]   
        if sheet_name == "" :
            for sheet in sheet_list:
                if sheet.find("MEDIÇÃO")>0:
                    resumos.append(sheet)
        if sheet_name == "" :
            try:
                sheet_name = resumos[0]
            except: 
                print(file)
                sheet_name = sheet_name_reserva
        return(sheet_name)


    def find_start(df):
        linha = -1
        for i, row in df.iterrows():
            list = df.loc[i,:].values.flatten().tolist()
            for item in list:
                if linha != -1:
                    break
                if str(item).find("CÓDIGO")>=0 or str(item).find("NID")>=0 or str(item).find("UND.")>=0 or str(item).find("Cód")>=0:
                    linha = i
                    break
        return(linha)

    #arruma o cabeçalho
    def find_header(df, linha):
        quant = 0
        df2 = df.iloc[linha:,:]
        header = df.iloc[0]
        header = header.tolist()
        return([df2,header])

    #arruma as quantidades mescladas
    def fix_quant(df, header):
        header2 = header
        quant = 0
    #corrige a parte das quantidades se estiver mesclada
        for i in range(len(header)-1):
            valor = str(header[i]).upper()
            n=i+1
            if (valor.find("QUANT")>=0 or valor.find("FÍSICO")>=0 or valor.find("F  Í  S  I  C  O")>=0 or valor.find("RPFO")>=0) and quant == 0  and header[i+1] == "Vazio":
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":                 
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                header2[i] = f"{header[i]}_{df.iloc[1,i]}"
                i = i+4
                quant = 1
        return(header2)


    def fix_valor(df, header):
        header2 = header
        value = 0


    #corrige a parte dos qvalores se estiver mesclada
        for i in range(len(header)-1):
            valor = str(header[i]).upper()
            n=i+1
            if (valor.find("VALOR")>=0 or valor.find("Valor")>=0 or valor.find("PREÇO")>=0) and value == 0  and header[i+1] == "Vazio":
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":                 
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                while True:
                    if n >= len(header):
                        break
                    sub = df.iloc[1,n]
                    n += 1
                    if sub != "Vazio":
                        break
                header2[n-1] = f"{header[i]}_{sub}"
                sub = "Vazio"
                header2[i] = f"{header[i]}_{df.iloc[1,i]}"
                i = i+4
                value = 1
        return(header2)

    #ajeita os nomes todos
    def rename_columns(header):
        header2 = header
        quant = 0
        cod = 0
        value = 0 
        print(header2)
        for i in range(len(header)):
            valor = str(header[i]).upper()
            if valor.find("CÓD")>=0 or valor.find("COD")>=0  or valor.find("Cod")>=0 and cod == 0:
                header2[i] = "COD"
                cod = 1
            if valor.find("DISC")>=0 or valor.find("DESC")>=0 or valor.find("SERVI")>=0:
                header2[i] = "DESCRICAO"
            if valor.find("UNID")>=0 or valor.find("UND")>=0:
                header2[i] = "UNID"
            if valor.find("VALOR")== -1 and (valor.find("CONTRATO")>=0 or valor.find("TOTAL")>=0) and quant == 0 and (valor.find("QUANT")>=0 or valor.find("QTD")>=0 or valor.find("F  Í  S  I  C  O")>=0):
                header2[i] = "QUANT_TOTAL"
                quant = 1
            if quant == 0 and valor.find("QUANT")>=0 and valor.find("1°")<0:
                header2[i] = 'QUANT_TOTAL'
            if valor.find("VALOR")== -1 and (valor.find("NESTA")>=0 or valor.find("ATUAL")>=0 or valor.find("PRESENTE")>=0):
                header2[i] = "QUANT_MED_ATUAL"
            if valor.find("VALOR")== -1 and (valor.find("ANT.")>=0 or valor.find("ANTERIOR")>=0):
                header2[i] = "QUANT_ANTERIOR"
            if valor.find("VALOR")== -1 and (valor.find("ACUM")>=0 or valor.find("CONFEÊNCIA")>=0) and valor.find("ANTERIOR") == -1:
                header2[i] = "QUANT_ACUMULADA"
            if (valor.find("PREÇO")>=0) and valor.find("UNIT")>=0:
                header2[i] = "VALOR_UNIT"
                value = 1
            elif valor.find("VALOR")>=0 and valor.find("UNIT")>=0 and value == 0:
                header2[i] = "VALOR_UNIT"
        if cod == 0:
            for i in range(len(header)):
                valor = valor = str(header[i]).upper()
                if valor.find("ITEM")>=0:
                    header2[i] = "COD"
        print(header2)
        return(header2)

    #cria a lista de colunas que vamos puxar da medição
    def create_table(df,header):
        valid_columns = ['COD','DESCRICAO','UNID','QUANT_MED_ATUAL','VALOR_UNIT']
        df2 = df[1:]
        df2.columns = header
        resumo_med = df2[valid_columns]
        resumo_med = resumo_med.loc[:,~resumo_med.columns.duplicated(keep='first')]
        return(resumo_med)
        
       

    #pegar a etapa do serviço
    def get_stage(df):
        resumo_med = df
        etapa1 = "Vazio"
        etapa = "Vazio"
        data=[]
        colunas_checar = ['QUANT_MED_ATUAL','VALOR_UNIT']
        
        for i, row in resumo_med.iterrows():
            if row["VALOR_UNIT"] == "Vazio":
                check = 0
                if row["DESCRICAO"] != "Vazio":
                    for col in colunas_checar:
                        if row[col] != 'Vazio':
                            check += 1
                    if check == 0:
                        etapa1 = resumo_med.loc[i,"DESCRICAO"]
                elif row['COD'] != 'Vazio' and 'fiscal' not in row['COD'].lower():
                    for col in colunas_checar:
                        if row[col] != 'Vazio':
                                check += 1
                    if check == 0:
                        etapa1 = resumo_med.loc[i,"COD"]


            data.append(etapa1)


        resumo_med["ETAPA"] = data
        return(resumo_med)

    def table_filter(df):
        resumo_med = df

        resumo_med = resumo_med.query('UNID != "Vazio"')
        resumo_med["MES"] = mes
        resumo_med["CONTRATO"] = ic
        resumo_med["DATA_BASE"] = data_base
        #resumo_med["FILE"] = file
        return(resumo_med)


    #tab daqui pra cima
    file = arquivo

    #busca a lista de sheets
    list = get_list(file)


    #acha a sheet certa
    try:
        sheet = find_sheet(list)
        st.markdown(sheet)
    except ValueError as e:
        print(f"{file} erro na na hora de achar a lista")
        #print(e)



    #cria a tabela
    df = pd.read_excel(file,sheet)
    print(sheet)



    #busca os itens no cabeçalho
    try:
        ic = getitem(df, "Contrat")
        print('contrato')
        print(ic)
        print('fim ic')
        data_base = "1/1/1900"
        mes = getitem(df, "Período")


        if isinstance(mes,str):
            index = mes.find('/') - 2
            mes = mes[index:]
            mes = mes[:10]
        try:
            mes = pd.to_datetime(mes, format="%d/%m/%Y")
        except:
            print(f'{ic} {mes} mes errado')



    except ValueError as e:
        print(f"{file} erro achando dados")
        print(e)
        

    #acha a linha certa
    try:
        linha = find_start(df)
    except:
        print(f"{file} erro achando linha certa")
        

    #trocando os vazios por string para facilitar comparações
    try:
        df = df.fillna("Vazio")
    except:
        print(f"{file} erro trocando vazios")
        

    #corta o cabeçalho e acha os titulos
    try:
        df = find_header(df, linha)[0]
        header = find_header(df, linha)[1]
    except:
        print(f"{file} erro na parte de cortar o cabeçalho")
        

    #arruma a parte mesclada das quantidades 
    try:
        header = fix_quant(df,header)
    except:
        print(f"{file} erro ajeitando a parte das quantidades que vem mesclada")
        #print(e)
        

    #arruma a parte mesclada do valor 
    try:
        header = fix_valor(df,header)
    except:
        print(f"{file} erro ajeitando a parte dos valores que vem mesclada")
        #print(e)
        
    #renomeia as colunas
    try:
        header = rename_columns(header)
    except:
        print(f"{file} erro renomeando as colunas")
    
    #cria a nova tabela, já apenas com as colunas corretas
    resumo_med = create_table(df, header)
    


    #separa a etapa do serviço num canto
    try:
        resumo_med = get_stage(resumo_med)
    except Exception as e:
        print(f"{file} erro na parte de buscar a etapa do serviço")
        print(e)
    

    #filtra só que a gente quer da tabela
    try:
        resumo_med = table_filter(resumo_med)
    except:
        print(f"{file} erro na parte de filtrar as linhas úteis")
        
    resumo_med['VALOR_UNIT']=pd.to_numeric(resumo_med['VALOR_UNIT'], errors='coerce')

    resumo_med['QUANT_MED_ATUAL']=pd.to_numeric(resumo_med['QUANT_MED_ATUAL'], errors='coerce')
    resumo_med['file'] = str(file)
    st.dataframe(resumo_med)
    resumo_med.to_csv('teste.csv')
    return([resumo_med,ic,mes])
    

def cadastrarObra(obra):
    conn = open_conn()
    cur = conn.cursor()

    ic = obra['ic']
    fantasia = obra['fantasia']
    rodovia = obra['rodovia']
    empresa = obra['razao_social']

    cur.execute(f'''
                INSERT INTO public.contratos(
                ic, fantasia, rodovia, empresa, ativo) VALUES(
                '{ic}','{fantasia}','{rodovia}','{empresa}', true)''')
    cur.close()
    conn.commit()
    conn.close()


def cadastrarUsuario(user):
    conn = open_conn()
    cur = conn.cursor()


    nome = user['nome']
    cargo = user['cargo']
    senha = user['senha']
    primeiro_nome = user['primeiro_nome']
    username = user['username']
    email = user['email']
    nivel = user['nivel']

    cur.execute(f'''
                INSERT INTO public.usuarios(
                nome, cargo, senha, primeiro_nome, "user", email, nivel) VALUES(
                '{nome}','{cargo}','{senha}','{primeiro_nome}','{username}', '{email}', '{nivel}') ''')
    cur.close()
    conn.commit()
    conn.close()
    
@st.cache_data
def readEnsaiosTsd():
    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT * FROM public.ensaiostsd')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()
    df = pd.DataFrame(dados, columns=colunas)

    cur.close()
    conn.close()
    return df

@st.cache_data
def readOcorrencias():
    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT * FROM public.levantamentos')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()
    df = pd.DataFrame(dados, columns=colunas)

    cur.close()
    conn.close()
    return df

@st.cache_data
def readUsers():
    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT id, nome, cargo, primeiro_nome, email, nivel, "user" FROM public.usuarios')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()
    df = pd.DataFrame(dados, columns=colunas)
    df = df.sort_values('nome')

    cur.close()
    conn.close()
    return df

def authenticate(user, passwd):
    conn = open_conn()
    cur = conn.cursor()

    query = sql.SQL('SELECT EXISTS(SELECT 1 FROM public.usuarios WHERE "user" = {} AND senha ={})').format(
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
    
def mudaSenha(user, senha):
    conn = open_conn()
    cur = conn.cursor()

    query = sql.SQL('UPDATE public.usuarios SET senha = {} WHERE "user" = {}').format(
        sql.Literal(senha),
        sql.Literal(user)
    )

    cur.execute(query)

    cur.close()
    conn.commit()
    conn.close()

def cadastrarDemanda(demanda):
    
    conn = open_conn()
    cur = conn.cursor()

    query = sql.SQL('''INSERT INTO public.demandas ("id", id_responsavel, titulo, descricao, os, n_os, tipo, contrato, n_contrato, criador)
                    VALUES({},{},{},{},{},{},{},{},{},{})''').format(
                        sql.Literal(demanda['id']),
                        sql.Literal(demanda['id_responsavel']),
                        sql.Literal(demanda['titulo']),
                        sql.Literal(demanda['descricao']),
                        sql.Literal(demanda['os']),
                        sql.Literal(demanda['n_os']),
                        sql.Literal(demanda['tipo']),
                        sql.Literal(demanda['contrato']),
                        sql.Literal(demanda['n_contrato']),
                        sql.Literal(demanda['criador'])
                    )
    
    cur.execute(query)

    cur.close()
    conn.commit()
    conn.close()

@st.cache_data
def readDemandas():
    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT * from public.demandas')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()

    df = pd.DataFrame(dados, columns=colunas)
    return(df)

def transferirDemanda(demanda, transferencia, new = False):
    conn = open_conn()
    cur = conn.cursor()

    #atualiza os dados da demanda na tabela
    if not new:
        query = sql.SQL('UPDATE public.demandas SET id_responsavel = {} WHERE id = {}').format(
            sql.Literal(demanda['responsavel_id']),
            sql.Literal(demanda['id'])
        )

        cur.execute(query)

    #gera a linha da tabela de trasnferencias
    query = sql.SQL('''INSERT INTO public.demandas_transferencias
                    (remetente, destinatario, demanda, descricao) VALUES(
                    {},{},{},{})''').format(
                        sql.Literal(transferencia['remetente']),
                        sql.Literal(transferencia['destinatario']),
                        sql.Literal(transferencia['demanda']),
                        sql.Literal(transferencia['descricao'])
                    )
    
    cur.execute(query)
    cur.close()
    conn.commit()
    conn.close()

def alterarStatusDemanda(demanda, mudanca):
    conn = open_conn()
    cur = conn.cursor()

    #atualiza na tabela de demandas
    query = sql.SQL('UPDATE public.demandas SET status = {} WHERE id = {}').format(
        sql.Literal(demanda['status']),
        sql.Literal(demanda['id'])
    )

    cur.execute(query)

    #atualiza na tabela de andamento
    query = sql.SQL('''INSERT INTO public.demandas_status
                    (id_demanda, status_antigo, status_novo, causa_pausa, comentario) VALUES(
                    {}, {}, {}, {}, {})''').format(
                        sql.Literal(mudanca['id_demanda']),
                        sql.Literal(mudanca['status_antigo']),
                        sql.Literal(mudanca['status_novo']),
                        sql.Literal(mudanca['causa_pausa']),
                        sql.Literal(mudanca['comentario'])
                    )
    cur.execute(query)

    cur.close()
    conn.commit()
    conn.close()

@st.cache_data
def readDemandasStatus():
    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT * from public.demandas_status')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()

    df = pd.DataFrame(dados, columns=colunas)
    return(df)

@st.cache_data
def readDemandasTransferencias():
    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT * from public.demandas_transferencias')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()

    df = pd.DataFrame(dados, columns=colunas)
    return(df)

def postOcorrencia(item):
    conn = open_conn()
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO public.levantamentos(
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

def createRetro(item):
    conn = open_conn()
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO public.levantamentos_retro(
        rodovia,
        crescente,
        decrescente,
        vertical,
        horizontal
        )
        VALUES (%s, %s, %s, %s, %s)
        ''', (item['rodovia'], item['crescente'], item['decrescente'], item['vertical'], item['horizontal'])
    )

    conn.commit()
    cur.close()
    conn.close()

def lerContratosNossos():

    conn = open_conn()
    cur = conn.cursor()

    cur.execute('SELECT * FROM public.nossos_contratos')
    dados = cur.fetchall()

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    df = pd.DataFrame(dados, columns = colunas)

    return(df)

def upMedicaoNossa(item):
    conn = open_conn()
    cur = conn.cursor()

    cur.execute(
                '''
                INSERT INTO public.nossas_medicoes(
                id_contrato,
                periodo,
                n_med,
                valor_pi,
                valor_r
                qtd_produtos) VALUES(%s,%s,%s,%s,%s,%s)
                ''', (item['id_contrato'], item['periodo'], item['n_med'], item['valor_pi'], item['valor_r'], item['qtd_produtos']) 
                ) 
    cur.close()
    conn.commit()
    conn.close()

def upPrevisao(item):
    conn = open_conn()
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO public.previsoes_med(
        contrato,
        periodo,
        valor
        ) VALUES(%s,%s,%s)
        ''', (item['contrato'], item['periodo'], item['valor'])
    )

    cur.close()
    conn.commit()
    conn.close()

def LerTabelaBancoDados(tabela):

    conn = open_conn()
    cur = conn.cursor()

    cur.execute(f'SELECT * FROM {tabela}')

    colunas = []
    for i in cur.description:
        colunas.append(i[0])

    dados = cur.fetchall()

    df = pd.DataFrame(dados, columns = colunas)

    return(df)