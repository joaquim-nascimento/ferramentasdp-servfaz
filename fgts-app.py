import os
import re
import pandas as pd
import zipfile
from flask import request, send_file, redirect
from werkzeug.utils import secure_filename
from io import BytesIO
import sys

def extrai_matricula(bloco):
    linhas = bloco.splitlines()
    idx = -1
    for i, linha in enumerate(linhas):
        if "MATRICULA" in linha:
            idx = i
            break
    if idx >= 0 and idx + 1 < len(linhas):
        prox = linhas[idx + 1]
        m = re.search(r'(\d{6,15})', prox)
        if m:
            return m.group(1)
    m = re.search(r"DATA DE OPCAO.*?\n.*?\n.*?(\d{6,15})", bloco, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"MATRICULA[^\n]*?(\d{6,15})", bloco)
    if m:
        return m.group(1).strip()
    return ""

def extrai_nome(bloco):
    m = re.search(r"NOME DO TRABALHADOR[^\n]*\n\s*([^\n\d]+)", bloco)
    return m.group(1).strip() if m else ""

def extrai_pis(bloco):
    m = re.search(r"PIS/PASEP[^\n]*\n\s*(\d{11})", bloco)
    return m.group(1).strip() if m else ""

def extrai_dtadm(bloco):
    linhas = bloco.splitlines()
    for i, linha in enumerate(linhas):
        if "DTA.ADM." in linha:
            if i + 1 < len(linhas):
                prox_linha = linhas[i + 1]
                m = re.search(r"(\d{2}/\d{2}/\d{4})", prox_linha)
                if m:
                    return m.group(1)
    return ""

def extrai_competencias_nao_localizadas(bloco):
    m = re.search(r"COMPETENCIAS NAO LOCALIZADAS[^\n]*\n(.*?)(?:\n{2,}|MOVIMENTACAO DA CONTA|#EXTERNO|SALDO|OBS.:)", bloco, re.DOTALL | re.IGNORECASE)
    if m:
        comp_text = m.group(1)
        comp_lista = re.findall(r"\d{2}/\d{4}", comp_text)
        return " ".join(ordenar_competencias(comp_lista)) 
    return ""

def ordenar_competencias(competencias):
    if not competencias:
        return []
    
    def parse_competencia(comp):
        mes, ano = comp.split('/')
        return (int(ano), int(mes))
    
    competencias_ordenadas = sorted(competencias, key=parse_competencia)
    
    return competencias_ordenadas

def extrai_depositos_em_atraso(bloco):
    padrao_principal = re.findall(
        r"\d{2}/\d{2}/\d{4}\s+DEPOSITO EM ATRASO\s+([A-ZÇ]{3,})\/?(\d{4})\s+([\d.,]+)", 
        bloco
    )
    
    padrao_alternativo = re.findall(
        r"DEPOSITO EM ATRASO\s+([A-ZÇ]{3,})\/?(\d{4})\s+([\d.,]+)", 
        bloco
    )
    
    padrao_slash = re.findall(
        r"DEPOSITO EM ATRASO\s+([A-ZÇ]{3,}\/\d{4})\s+([\d.,]+)", 
        bloco
    )
    
    competencias_valores = []
    
    for match in padrao_principal + padrao_alternativo:
        if len(match) == 3:
            mes_str, ano, valor = match
            mes_str = mes_str.strip().upper()
            ano = ano.strip()
            
            meses = {
                'JAN': '01', 'JANEIRO': '01',
                'FEV': '02', 'FEVEREIRO': '02',
                'MAR': '03', 'MARÇO': '03',
                'ABR': '04', 'ABRIL': '04',
                'MAI': '05', 'MAIO': '05',
                'JUN': '06', 'JUNHO': '06',
                'JUL': '07', 'JULHO': '07',
                'AGO': '08', 'AGOSTO': '08',
                'SET': '09', 'SETEMBRO': '09',
                'OUT': '10', 'OUTUBRO': '10',
                'NOV': '11', 'NOVEMBRO': '11',
                'DEZ': '12', 'DEZEMBRO': '12'
            }
            
            mes_num = None
            for nome_mes, num_mes in meses.items():
                if mes_str.startswith(nome_mes):
                    mes_num = num_mes
                    break
            
            if mes_num and ano.isdigit() and len(ano) == 4:
                try:
                    valor_float = float(valor.replace('.', '').replace(',', '.'))
                    competencias_valores.append((f"{mes_num}/{ano}", valor_float))
                except ValueError:
                    continue
    
    for match in padrao_slash:
        if len(match) == 2:
            competencia, valor = match
            mes_str = competencia.split('/')[0].strip().upper()
            ano = competencia.split('/')[1]
            
            mes_num = meses.get(mes_str)
            if mes_num and ano.isdigit() and len(ano) == 4:
                try:
                    valor_float = float(valor.replace('.', '').replace(',', '.'))
                    competencias_valores.append((f"{mes_num}/{ano}", valor_float))
                except ValueError:
                    continue
    
    return competencias_valores

def processar_arquivo(txt_path):
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        texto = f.read()

    blocos = re.split(r"(?=NOME DO TRABALHADOR)", texto, flags=re.IGNORECASE)

    dados = {}
    for bloco in blocos:
        if not bloco.strip():
            continue

        nome = extrai_nome(bloco)
        matricula = extrai_matricula(bloco)
        pis = extrai_pis(bloco)
        dtadm = extrai_dtadm(bloco)
        competencias = extrai_competencias_nao_localizadas(bloco)
        depositos_atraso = extrai_depositos_em_atraso(bloco)

        if nome and matricula and dtadm:
            chave = (nome, matricula, dtadm)
            if chave not in dados:
                dados[chave] = {
                    "NOME DO TRABALHADOR": nome,
                    "MATRICULA": matricula,
                    "PIS/PASEP": pis,
                    "DTA.ADM.": dtadm,
                    "COMPETENCIAS_NAO_LOCALIZADAS": set(),
                    "DEPOSITOS_EM_ATRASO": []
                }
            
            if competencias:
                dados[chave]["COMPETENCIAS_NAO_LOCALIZADAS"].update(competencias.split())

            if depositos_atraso:
                dados[chave]["DEPOSITOS_EM_ATRASO"].extend(depositos_atraso)
    
    lista_competencias = []
    lista_depositos = []
    for registro in dados.values():
        competencias_ordenadas = ordenar_competencias(registro["COMPETENCIAS_NAO_LOCALIZADAS"])
        qtd_competencias = len(competencias_ordenadas)
        
        lista_competencias.append({
            "NOME DO TRABALHADOR": registro["NOME DO TRABALHADOR"],
            "MATRICULA": registro["MATRICULA"],
            "PIS/PASEP": registro["PIS/PASEP"],
            "DTA.ADM.": registro["DTA.ADM."],
            "COMPETENCIAS_NAO_LOCALIZADAS": " ".join(competencias_ordenadas),
            "QTD_COMPETENCIAS": qtd_competencias
        })

        for competencia, valor in registro["DEPOSITOS_EM_ATRASO"]:
            lista_depositos.append({
                "NOME DO TRABALHADOR": registro["NOME DO TRABALHADOR"],
                "MATRICULA": registro["MATRICULA"],
                "PIS/PASEP": registro["PIS/PASEP"],
                "DTA.ADM.": registro["DTA.ADM."],
                "COMPETENCIA": competencia,
                "VALOR": valor
            })
    
    df_competencias = pd.DataFrame(lista_competencias)
    df_depositos = pd.DataFrame(lista_depositos)
    
    if not df_competencias.empty:
        df_competencias = df_competencias.sort_values(by="NOME DO TRABALHADOR")
    if not df_depositos.empty:
        df_depositos = df_depositos.sort_values(by="NOME DO TRABALHADOR")
    
    return df_competencias, df_depositos

def comparar_planilhas(df1_comp, df2_comp, df1_dep, df2_dep):
    comp_resultados = []
    df1_comp['COMP_SET'] = df1_comp['COMPETENCIAS_NAO_LOCALIZADAS'].apply(lambda x: set(x.split()) if x else set())
    df2_comp['COMP_SET'] = df2_comp['COMPETENCIAS_NAO_LOCALIZADAS'].apply(lambda x: set(x.split()) if x else set())

    for _, row1 in df1_comp.iterrows():
        matricula = row1['MATRICULA']
        dtadm = row1['DTA.ADM.']
        
        matches = df2_comp[(df2_comp['MATRICULA'] == matricula) & (df2_comp['DTA.ADM.'] == dtadm)]
        
        if not matches.empty:
            row2 = matches.iloc[0]
            competencias_comuns = row1['COMP_SET'] & row2['COMP_SET']
            if competencias_comuns:
                comp_resultados.append({
                    'NOME DO TRABALHADOR': row1['NOME DO TRABALHADOR'],
                    'MATRICULA': matricula,
                    'PIS/PASEP': row1['PIS/PASEP'],
                    'DTA.ADM.': dtadm,
                    'COMPETENCIAS_NAO_LOCALIZADAS': ' '.join(ordenar_competencias(competencias_comuns)),
                    'QTD_COMPETENCIAS': len(competencias_comuns)
                })

    df_resultado_comp = pd.DataFrame(comp_resultados)

    matriculas_dtadm_comuns = set(zip(df1_comp['MATRICULA'], df1_comp['DTA.ADM.'])).intersection(
                               set(zip(df2_comp['MATRICULA'], df2_comp['DTA.ADM.'])))
    
    print(f"Total de matrículas com data de admissão comuns encontradas: {len(matriculas_dtadm_comuns)}")

    dep_resultados = []

    df1_filtrado = df1_dep[df1_dep.apply(lambda x: (x['MATRICULA'], x['DTA.ADM.']) in matriculas_dtadm_comuns, axis=1)]
    if not df1_filtrado.empty:
        for _, row in df1_filtrado.iterrows():
            dep_resultados.append({
                'NOME DO TRABALHADOR': row['NOME DO TRABALHADOR'],
                'MATRICULA': row['MATRICULA'],
                'PIS/PASEP': row['PIS/PASEP'],
                'DTA.ADM.': row['DTA.ADM.'],
                'COMPETENCIA': row['COMPETENCIA'],
                'VALOR': row['VALOR'],
                'ORIGEM': 'Arquivo 1'
            })

    df2_filtrado = df2_dep[df2_dep.apply(lambda x: (x['MATRICULA'], x['DTA.ADM.']) in matriculas_dtadm_comuns, axis=1)]
    if not df2_filtrado.empty:
        for _, row in df2_filtrado.iterrows():
            dep_resultados.append({
                'NOME DO TRABALHADOR': row['NOME DO TRABALHADOR'],
                'MATRICULA': row['MATRICULA'],
                'PIS/PASEP': row['PIS/PASEP'],
                'DTA.ADM.': row['DTA.ADM.'],
                'COMPETENCIA': row['COMPETENCIA'],
                'VALOR': row['VALOR'],
                'ORIGEM': 'Arquivo 2'
            })

    if dep_resultados:
        df_dep = pd.DataFrame(dep_resultados)
        df_dep = df_dep.drop_duplicates(subset=['MATRICULA', 'DTA.ADM.', 'COMPETENCIA', 'VALOR'])
        print(f"Total de depósitos encontrados: {len(df_dep)}")
    else:
        df_dep = pd.DataFrame()
        print("Nenhum depósito encontrado para as matrículas com data de admissão comuns.")

    return df_resultado_comp, df_dep

def aplicar_formatacao_excel(writer, aba_nome, df, config_colunas=None):
    workbook = writer.book
    worksheet = writer.sheets[aba_nome]
    
    DEFAULT_CONFIG = {
        'width': None,
        'header': {
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
            'text_wrap': True,
            'border': 1,
            'font_size': 12
        },
        'body': {
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1,
            'font_size': 11
        },
        'date': {
            'num_format': 'dd/mm/yyyy',
            'font_size': 11
        },
        'numeric': {
            'num_format': '#,##0.00',
            'font_size': 11
        }
    }
    
    if config_colunas is None:
        config_colunas = {}
    
    header_format = workbook.add_format(DEFAULT_CONFIG['header'])
    body_format = workbook.add_format(DEFAULT_CONFIG['body'])
    date_format = workbook.add_format({**DEFAULT_CONFIG['body'], **DEFAULT_CONFIG['date']})
    numeric_format = workbook.add_format({**DEFAULT_CONFIG['body'], **DEFAULT_CONFIG['numeric']})
    
    for col_num, col_name in enumerate(df.columns):
        if col_name in config_colunas and 'header' in config_colunas[col_name]:
            custom_header = workbook.add_format({**DEFAULT_CONFIG['header'], **config_colunas[col_name]['header']})
            worksheet.write(0, col_num, col_name, custom_header)
        else:
            worksheet.write(0, col_num, col_name, header_format)
    
    for row_num in range(1, len(df)+1):
        for col_num, col_name in enumerate(df.columns):
            valor = df.iloc[row_num-1, col_num]
            
            cell_format = body_format
            
            if 'DATA' in col_name.upper() or 'DTA' in col_name.upper():
                cell_format = date_format
            
            elif 'VALOR' in col_name.upper() or isinstance(valor, (int, float)):
                cell_format = numeric_format
            
            if col_name in config_colunas and 'body' in config_colunas[col_name]:
                custom_format = workbook.add_format({**cell_format.__dict__, **config_colunas[col_name]['body']})
                cell_format = custom_format
            
            if pd.isna(valor):
                worksheet.write_blank(row_num, col_num, None, cell_format)
            elif isinstance(valor, (int, float)):
                worksheet.write_number(row_num, col_num, valor, cell_format)
            else:
                worksheet.write(row_num, col_num, valor, cell_format)
    
    for col_num, col_name in enumerate(df.columns):
        if col_name in config_colunas and 'width' in config_colunas[col_name]:
            width = config_colunas[col_name]['width']
        else:
            max_len = max(
                df[col_name].astype(str).apply(len).max(),
                len(str(col_name)))
            width = min(max_len + 2, 50)
            
            if 'DATA' in col_name.upper() or 'DTA' in col_name.upper():
                width = 15
            elif 'VALOR' in col_name.upper():
                width = 15
            elif 'MATRICULA' in col_name.upper() or 'PIS' in col_name.upper():
                width = 20
            elif 'NOME' in col_name.upper():
                width = 40
            elif 'COMPETENCIA' in col_name.upper():
                width = 20
            elif 'COMPETENCIAS' in col_name.upper():
                width = 90
            elif 'QTD_' in col_name.upper():
                width = 10
        
        worksheet.set_column(col_num, col_num, width)
    
    worksheet.autofilter(0, 0, 0, len(df.columns) - 1)
    
    worksheet.freeze_panes(1, 0)

def process_files(file1_path, file2_path):
    df1_comp, df1_dep = processar_arquivo(file1_path)
    df2_comp, df2_dep = processar_arquivo(file2_path)
    
    df_resultado_comp, df_resultado_dep = comparar_planilhas(df1_comp, df2_comp, df1_dep, df2_dep)
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        comp_buffer = BytesIO()
        with pd.ExcelWriter(comp_buffer, engine='xlsxwriter') as writer:
            df_resultado_comp.to_excel(writer, index=False, sheet_name='Competencias')
            aplicar_formatacao_excel(writer, 'Competencias', df_resultado_comp)
        zip_file.writestr('competencias_nao_localizadas.xlsx', comp_buffer.getvalue())
        
        dep_buffer = BytesIO()
        with pd.ExcelWriter(dep_buffer, engine='xlsxwriter') as writer:
            df_resultado_dep.to_excel(writer, index=False, sheet_name='Depositos')
            aplicar_formatacao_excel(writer, 'Depositos', df_resultado_dep)
        zip_file.writestr('depositos_em_atraso.xlsx', dep_buffer.getvalue())
    
    return zip_buffer

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python fgts-app.py arquivo1.txt arquivo2.txt")
        sys.exit(1)
    
    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    
    try:
        zip_buffer = process_files(file1_path, file2_path)
        sys.stdout.buffer.write(zip_buffer.getvalue())
    except Exception as e:
        print(f"Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)