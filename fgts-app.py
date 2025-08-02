import re
import pandas as pd
import tempfile
import zipfile
from io import BytesIO
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

def extrai_matricula(bloco):
    linhas = bloco.splitlines()
    for i, linha in enumerate(linhas):
        if "MATRICULA" in linha and i + 1 < len(linhas):
            m = re.search(r'(\d{6,15})', linhas[i + 1])
            if m:
                return m.group(1)
    for regex in [
        r"DATA DE OPCAO.*?\n.*?\n.*?(\d{6,15})",
        r"MATRICULA[^\n]*?(\d{6,15})"
    ]:
        m = re.search(regex, bloco, flags=re.DOTALL)
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
        if "DTA.ADM." in linha and i + 1 < len(linhas):
            m = re.search(r"(\d{2}/\d{2}/\d{4})", linhas[i + 1])
            if m:
                return m.group(1)
    return ""

def extrai_competencias_nao_localizadas(bloco):
    m = re.search(r"COMPETENCIAS NAO LOCALIZADAS[^\n]*\n(.*?)(?:\n{2,}|MOVIMENTACAO DA CONTA|#EXTERNO|SALDO|OBS.:)",
                  bloco, re.DOTALL | re.IGNORECASE)
    if m:
        comp_text = m.group(1)
        comp_lista = re.findall(r"\d{2}/\d{4}", comp_text)
        return " ".join(ordenar_competencias(comp_lista))
    return ""

def ordenar_competencias(competencias):
    if not competencias:
        return []
    def parse(comp): return (int(comp.split('/')[1]), int(comp.split('/')[0]))
    return sorted(competencias, key=parse)

def gerar_competencias_esperadas(dt_admissao_str, dt_fim=None):
    competencias = []
    dt_ini = datetime.strptime(dt_admissao_str, "%d/%m/%Y")
    dt_fim = dt_fim or datetime.today()
    while dt_ini <= dt_fim:
        competencias.append(dt_ini.strftime("%m/%Y"))
        dt_ini += relativedelta(months=1)
    return competencias

def processar_arquivo(txt_path):
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        texto = f.read()

    blocos = re.split(r"(?=NOME DO TRABALHADOR)", texto, flags=re.IGNORECASE)
    lista_competencias = []

    for bloco in blocos:
        if not bloco.strip():
            continue

        nome = extrai_nome(bloco)
        matricula = extrai_matricula(bloco)
        pis = extrai_pis(bloco)
        dtadm = extrai_dtadm(bloco)
        competencias_raw = extrai_competencias_nao_localizadas(bloco)

        if nome and matricula and dtadm:
            competencias_extraidas = ordenar_competencias(competencias_raw.split())
            competencias_esperadas = gerar_competencias_esperadas(dtadm)
            set_extraidas = set(competencias_extraidas)
            set_esperadas = set(competencias_esperadas)

            competencias_validas = sorted(set_extraidas & set_esperadas, key=lambda x: (int(x.split('/')[1]), int(x.split('/')[0])))
            competencias_nao_pag = sorted(set_esperadas - set_extraidas, key=lambda x: (int(x.split('/')[1]), int(x.split('/')[0])))

            lista_competencias.append({
                "NOME DO TRABALHADOR": nome,
                "MATRICULA": matricula,
                "PIS/PASEP": pis,
                "DTA.ADM.": dtadm,
                "TODAS_COMPETENCIAS": " ".join(competencias_extraidas),
                "COMPETENCIAS_VALIDAS": " ".join(competencias_validas),
                "COMPETENCIAS_NAO_PAGAS": " ".join(competencias_nao_pag),
                "QTD_COMPETENCIAS_LOCALIZADAS": len(competencias_extraidas),
                "QTD_VALIDAS": len(competencias_validas),
                "QTD_NAO_PAGAS": len(competencias_nao_pag)
            })

    df = pd.DataFrame(lista_competencias)
    if not df.empty:
        df = df.sort_values(by="NOME DO TRABALHADOR")
    return df

def formatar_excel(writer, df_pag, df_nao_pag):
    workbook = writer.book

    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': False,
        'valign': 'middle',
        'align': 'center',
        'bg_color': '#D9E1F2',
        'border': 1
    })

    competencias_format = workbook.add_format({
        'text_wrap': True,
        'valign': 'middle'
    })

    def formatar_aba(sheet, df, col_competencias):
        for col_num, col_nome in enumerate(df.columns):
            sheet.write(0, col_num, col_nome, header_format)
            largura = max(15, min(50, df[col_nome].astype(str).map(len).max()))
            sheet.set_column(col_num, col_num, largura)

        col_idx = df.columns.get_loc(col_competencias)
        sheet.set_column(col_idx, col_idx, 40, competencias_format)
        sheet.freeze_panes(1, 0)

    aba_pag = writer.sheets['COMP_PAGAS']
    aba_nao = writer.sheets['COMP_NAO_PAGAS']

    formatar_aba(aba_pag, df_pag, "COMPETENCIAS_PAGAS")
    formatar_aba(aba_nao, df_nao_pag, "TODAS_COMPETENCIAS_NAO_PAGAS")


def process_file(file_paths):
    registros = {}

    for path in file_paths:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            texto = f.read()

        blocos = re.split(r"(?=NOME DO TRABALHADOR)", texto, flags=re.IGNORECASE)

        for bloco in blocos:
            if not bloco.strip():
                continue

            nome = extrai_nome(bloco)
            matricula = extrai_matricula(bloco)
            pis = extrai_pis(bloco)
            dtadm = extrai_dtadm(bloco)
            competencias_raw = extrai_competencias_nao_localizadas(bloco)

            if not (nome and matricula and dtadm):
                continue

            competencias_nao_pagas = set(ordenar_competencias(competencias_raw.split()))
            chave = nome.strip().upper()

            if chave in registros:
                registros[chave]["competencias_nao_pagas"].update(competencias_nao_pagas)

                dt_antiga = datetime.strptime(registros[chave]["dt_admissao"], "%d/%m/%Y")
                dt_nova = datetime.strptime(dtadm, "%d/%m/%Y")
                if dt_nova < dt_antiga:
                    registros[chave]["dt_admissao"] = dtadm
            else:
                registros[chave] = {
                    "nome": nome,
                    "matricula": matricula,
                    "pis": pis,
                    "dt_admissao": dtadm,
                    "competencias_nao_pagas": competencias_nao_pagas
                }

    lista_final = []
    for dados in registros.values():
        dt_admissao = dados["dt_admissao"]
        todas_esperadas = set(gerar_competencias_esperadas(dt_admissao))
        competencias_nao_pagas = dados["competencias_nao_pagas"]
        competencias_pagas = todas_esperadas - competencias_nao_pagas

        lista_final.append({
            "NOME DO TRABALHADOR": dados["nome"],
            "MATRICULA": dados["matricula"],
            "PIS/PASEP": dados["pis"],
            "DTA.ADM.": dt_admissao,
            "TODAS_COMPETENCIAS_NAO_PAGAS": " ".join(sorted(competencias_nao_pagas, key=lambda x: (int(x.split('/')[1]), int(x.split('/')[0])))),
            "COMPETENCIAS_PAGAS": " ".join(sorted(competencias_pagas, key=lambda x: (int(x.split('/')[1]), int(x.split('/')[0])))),
            "QTD_COMPETENCIAS_ESPERADAS": len(todas_esperadas),
            "QTD_PAGAS": len(competencias_pagas),
            "QTD_NAO_PAGAS": len(competencias_nao_pagas)
        })

    df = pd.DataFrame(lista_final)
    if not df.empty:
        df = df.sort_values(by="NOME DO TRABALHADOR")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_pag = df[["NOME DO TRABALHADOR", "MATRICULA", "PIS/PASEP", "DTA.ADM.", "COMPETENCIAS_PAGAS", "QTD_PAGAS"]]
            df_pag.to_excel(writer, sheet_name='COMP_PAGAS', index=False)

            df_nao_pag = df[["NOME DO TRABALHADOR", "MATRICULA", "PIS/PASEP", "DTA.ADM.", "TODAS_COMPETENCIAS_NAO_PAGAS", "QTD_NAO_PAGAS"]]
            df_nao_pag.to_excel(writer, sheet_name='COMP_NAO_PAGAS', index=False)

            formatar_excel(writer, df_pag, df_nao_pag)

        excel_buffer.seek(0)
        zip_file.writestr("relatorio_competencias.xlsx", excel_buffer.read())

    zip_buffer.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
        tmp_zip.write(zip_buffer.read())
        return tmp_zip.name

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Uso: script.py <arquivo1.txt> <arquivo2.txt> ...")

    file_paths = sys.argv[1:]

    try:
        zip_path = process_file(file_paths)
        print(zip_path)
    except Exception as e:
        print(f"Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)
