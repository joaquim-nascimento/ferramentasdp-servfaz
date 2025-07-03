import os
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import pandas as pd
import re
import json
import sys
import io

import logging
logging.basicConfig(filename='processamento.log', level=logging.INFO)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extrair_cabecalho(texto):
    campos = {
        "Nome do Colaborador": "",
        "CPF": "",
        "Matrícula": "",
        "Cargo": "",
        "Período": "",
        "Escala": "",
        "Posto": "",
        "Empresa": "",
        "Cliente": ""
    }
    
    linhas = texto.split("\n")
    for linha in linhas:
        if 'Colaborador:' in linha:
            partes = linha.split('Colaborador:')[1].split('Matrícula:')
            campos['Nome do Colaborador'] = partes[0].strip()
            if len(partes) > 1:
                campos['Matrícula'] = partes[1].strip()
        if 'CPF:' in linha and not campos['CPF']:
            campos['CPF'] = linha.split('CPF:')[-1].split()[0].strip()
        if 'Cargo:' in linha and not campos['Cargo']:
            campos['Cargo'] = linha.split('Cargo:')[-1].strip()
        if 'Período:' in linha and not campos['Período']:
            campos['Período'] = linha.split('Período:')[-1].strip()
        if 'Escala:' in linha and not campos['Escala']:
            campos['Escala'] = linha.split('Escala:')[-1].strip()
        if 'Posto:' in linha and not campos['Posto']:
            campos['Posto'] = linha.split('Posto:')[-1].strip()
        if 'Empresa:' in linha and not campos['Empresa']:
            campos['Empresa'] = linha.split('Empresa:')[-1].strip()
        if 'Cliente:' in linha and not campos['Cliente']:
            campos['Cliente'] = linha.split('Cliente:')[-1].strip()
    if not campos['Escala']:
        for linha in linhas:
            esc = re.findall(r"(\d{2}:\d{2}.*[A-Z]{3,4})", linha)
            if esc:
                campos['Escala'] = esc[0]
                break
            elif '12X36' in linha.upper():
                campos['Escala'] = linha.strip()
                break
    return campos

def tipo_escala(escala_texto):
    escala = escala_texto.upper()
    if '12X36' in escala:
        return '12x36', None, None
    horarios = re.findall(r'(\d{2}:\d{2})', escala)
    if len(horarios) >= 4:
        return 'expediente_duplo', horarios[:2], horarios[2:4]
    elif len(horarios) == 2:
        return 'expediente_simples', horarios[:2], None
    else:
        return 'desconhecida', None, None

def dias_validos_escala(escala_texto):
    escala = escala_texto.upper()
    if 'SEG/SEX' in escala or 'SEG-SEX' in escala or 'SEG À SEX' in escala or 'SEGUNDA A SEXTA' in escala:
        return ['SEG', 'TER', 'QUA', 'QUI', 'SEX']
    dias = []
    if 'SEG' in escala: dias.append('SEG')
    if 'TER' in escala: dias.append('TER')
    if 'QUA' in escala: dias.append('QUA')
    if 'QUI' in escala: dias.append('QUI')
    if 'SEX' in escala: dias.append('SEX')
    if 'SAB' in escala: dias.append('SAB')
    if 'DOM' in escala: dias.append('DOM')
    if not dias:
        dias = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
    return dias

def is_feriado(motivo):
    motivo = motivo.lower()
    return 'feriado' in motivo or 'ponto facultativo' in motivo

def minutos(hhmm):
    """Converte string HH:MM em minutos inteiros"""
    try:
        h, m = map(int, hhmm.split(":"))
        return h*60 + m
    except Exception:
        return None

def horas_para_minutos(horas):
    try:
        if not horas or ":" not in horas:
            return None
        h, m = horas.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None

def analisar_jornada(jornada, campos, tipo, periodos, dias_validos, feriados_linha):
    inconsistencias = []
    dias = jornada.reset_index(drop=True)
    if tipo == '12x36':
        dias_de_plantao = []
        for idx, row in dias.iterrows():
            marcacoes = str(row.get("Marcações", "")).strip()
            motivo = str(row.get("Motivo", "")).strip().upper()
            data = str(row.get("Data", "")).strip()
            dia_semana = data[-3:].replace('À', 'A').upper()
            if dia_semana not in dias_validos:
                continue
            if is_feriado(motivo):
                continue
            if marcacoes:
                dias_de_plantao.append(idx)
        for idx, row in dias.iterrows():
            marcacoes = str(row.get("Marcações", "")).strip()
            motivo = str(row.get("Motivo", "")).strip().upper()
            data = str(row.get("Data", "")).strip()
            horas_trab = str(row.get("Horas trab.", "")).strip()
            dia_semana = data[-3:].replace('À', 'A').upper()
            if dia_semana not in dias_validos:
                continue
            if is_feriado(motivo):
                continue
            pontos = [h for h in marcacoes.split() if h and ':' in h]
            num_pontos = len(pontos)
            minutos_trab = horas_para_minutos(horas_trab) if horas_trab else None
            descricao = None
            if marcacoes:
                # Regras de quantidade de marcações pelo tempo trabalhado
                if minutos_trab is not None:
                    if minutos_trab <= 240:  # até 4h
                        if num_pontos < 2:
                            descricao = f"Marcação incompleta em plantão 12x36 (apenas {num_pontos}, esperado 2)"
                    elif minutos_trab > 240:
                        if num_pontos < 4:
                            descricao = f"Marcação incompleta em plantão 12x36 (apenas {num_pontos}, esperado 4)"
                        if minutos_trab > 360 and num_pontos >= 4:
                            # Checa intervalo de almoço
                            try:
                                saida_almoco = minutos(pontos[1])
                                retorno_almoco = minutos(pontos[2])
                                if saida_almoco is not None and retorno_almoco is not None:
                                    intervalo = retorno_almoco - saida_almoco
                                    if intervalo < 60:
                                        descricao = "Intervalo de almoço inferior a 1 hora (mínimo legal para jornada superior a 6h)"
                            except Exception:
                                pass
                else:
                    # Não conseguiu ler horas, aplica regra padrão
                    if num_pontos < 4:
                        descricao = f"Marcação incompleta em plantão 12x36 (apenas {num_pontos}, esperado 4)"
            else:
                is_folga = False
                if idx > 0 and idx-1 in dias_de_plantao:
                    is_folga = True
                if idx < len(dias)-1 and idx+1 in dias_de_plantao:
                    is_folga = True
                if not is_folga:
                    if not motivo:
                        descricao = "Ausência de marcação em plantão 12x36 (possível falta de comparecimento)"
            if motivo and not is_feriado(motivo):
                descricao = motivo.title()
            if descricao:
                registro = campos.copy()
                registro.update({
                    "Data": data,
                    "Marcações": marcacoes,
                    "Motivo": motivo,
                    "Descrição do problema": descricao,
                    "Horas trabalhadas": horas_trab
                })
                inconsistencias.append(registro)
    else:
        for idx, row in dias.iterrows():
            data = str(row.get("Data", "")).strip()
            marcacoes = str(row.get("Marcações", "")).strip()
            motivo = str(row.get("Motivo", "")).strip().upper()
            horas_trab = str(row.get("Horas trab.", "")).strip()
            dia_semana = data[-3:].replace('À', 'A').upper()
            if dia_semana not in dias_validos:
                continue
            if is_feriado(motivo):
                continue
            pontos = [h for h in marcacoes.split() if h and ':' in h]
            num_pontos = len(pontos)
            minutos_trab = horas_para_minutos(horas_trab) if horas_trab else None
            descricao = None
            if motivo and not is_feriado(motivo):
                descricao = motivo.title()
            elif not marcacoes and not motivo:
                descricao = "Ausência de marcação"
            else:
                if minutos_trab is not None:
                    if minutos_trab <= 240:  # até 4h
                        if num_pontos < 2:
                            descricao = f"Marcação incompleta (apenas {num_pontos}, esperado 2)"
                    elif minutos_trab > 240:
                        if num_pontos < 4:
                            descricao = f"Marcação incompleta (apenas {num_pontos}, esperado 4)"
                        if minutos_trab > 360 and num_pontos >= 4:
                            # Checa intervalo de almoço
                            try:
                                saida_almoco = minutos(pontos[1])
                                retorno_almoco = minutos(pontos[2])
                                if saida_almoco is not None and retorno_almoco is not None:
                                    intervalo = retorno_almoco - saida_almoco
                                    if intervalo < 60:
                                        descricao = "Intervalo de almoço inferior a 1 hora (mínimo legal para jornada superior a 6h)"
                            except Exception:
                                pass
                else:
                    if tipo == 'expediente_duplo':
                        if num_pontos < 4:
                            descricao = f"Marcação incompleta (apenas {num_pontos}, esperado 4)"
                    elif tipo == 'expediente_simples':
                        if num_pontos < 2:
                            descricao = f"Marcação incompleta (apenas {num_pontos}, esperado 2)"
                    elif tipo == 'desconhecida':
                        if num_pontos < 2:
                            descricao = "Marcação incompleta (escala desconhecida)"
            if descricao:
                registro = campos.copy()
                registro.update({
                    "Data": data,
                    "Marcações": marcacoes,
                    "Motivo": motivo,
                    "Descrição do problema": descricao,
                    "Horas trabalhadas": horas_trab
                })
                inconsistencias.append(registro)
    return inconsistencias

UPLOAD_FOLDER = "uploads"  

def salvar_status(task_id, progresso, mensagem="", erro=""):
    status_path = os.path.join(UPLOAD_FOLDER, f"status_{task_id}.json")
    
    temp_path = status_path + ".tmp"
    
    try:
        with open(temp_path, "w", encoding='utf-8') as f:
            json.dump({"progress": progresso, "message": mensagem, "error": erro}, f)
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(temp_path, status_path)
    except Exception as e:
        print(f"Erro ao salvar status: {str(e)}")
        try:
            os.unlink(temp_path)
        except:
            pass

import os
from PyPDF2 import PdfReader, PdfWriter

def dividir_pdf_em_partes(caminho_pdf, tamanho_bloco=200):
    if not os.path.exists(caminho_pdf):
        raise FileNotFoundError(f"O arquivo PDF '{caminho_pdf}' não foi encontrado.")

    if not caminho_pdf.lower().endswith('.pdf'):
        raise ValueError(f"O arquivo fornecido '{caminho_pdf}' não é um PDF.")

    try:
        leitor = PdfReader(caminho_pdf)
        total_paginas = len(leitor.pages)

        if total_paginas == 0:
            raise ValueError("O PDF está vazio ou corrompido (sem páginas).")

        caminhos_divididos = []
        base, ext = os.path.splitext(caminho_pdf)

        for i in range(0, total_paginas, tamanho_bloco):
            escritor = PdfWriter()
            for j in range(i, min(i + tamanho_bloco, total_paginas)):
                try:
                    escritor.add_page(leitor.pages[j])
                except Exception as e:
                    raise RuntimeError(f"Erro ao adicionar página {j + 1}: {str(e)}")

            saida = f"{base}_parte_{i//tamanho_bloco + 1}{ext}"
            try:
                with open(saida, "wb") as f:
                    escritor.write(f)
            except Exception as e:
                raise IOError(f"Erro ao salvar a parte do PDF '{saida}': {str(e)}")

            caminhos_divididos.append(saida)

        return caminhos_divididos

    except Exception as e:
        raise RuntimeError(f"Erro ao dividir o PDF '{caminho_pdf}': {str(e)}")

def processar_um_pdf(caminho_pdf, task_id=None, parte_index=None, total_paginas=None):
    registros = []

    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page_index, pagina in enumerate(pdf.pages):
                if task_id and parte_index and total_paginas:
                    salvar_status(task_id, min(98, int((page_index / total_paginas) * 100)), f"[Parte {parte_index}] Processando página {page_index + 1}/{total_paginas}")

                texto = pagina.extract_text() or ""
                if not texto.strip():
                    continue

                campos = extrair_cabecalho(texto)
                escala = campos.get('Escala', '')
                tipo, manha, tarde = tipo_escala(escala)
                dias_validos = dias_validos_escala(escala)

                tabelas = pagina.extract_tables()
                if not tabelas:
                    continue

                for tabela in tabelas:
                    for idx, linha in enumerate(tabela):
                        if linha and len(linha) >= 4 and all(x in str(linha) for x in ['Data', 'Marcações', 'Motivo']):
                            headers = [str(cell).strip() if cell else "" for cell in linha]
                            dados = tabela[idx + 1:]

                            has_horas = any('hora' in h.lower() for h in headers)
                            if has_horas:
                                df = pd.DataFrame([ln[:5] for ln in dados if ln], columns=(headers[:5]))
                            else:
                                df = pd.DataFrame([ln[:4] for ln in dados if ln], columns=(headers[:4]))
                                df["Horas trab."] = ""

                            registros.extend(analisar_jornada(df, campos, tipo, (manha, tarde), dias_validos, None))
                            break
    except Exception as e:
        return [{
            "Erro": f"Falha ao processar arquivo: {str(e)}",
            "Arquivo": os.path.basename(caminho_pdf)
        }]
    except pdfplumber.PDFSyntaxError:
        return [{"Erro": "PDF corrompido ou formato inválido"}]

    return registros

def processar_partes(task_id, caminho_pdf, output_path):
    try:
        print("INICIANDO PROCESSAMENTO...")

        salvar_status(task_id, 0, "Iniciando processamento...")
        partes = dividir_pdf_em_partes(caminho_pdf)
        todos = []
        total_partes = len(partes)

        for i, parte in enumerate(partes):
            parte_index = f"{i+1}/{total_partes}"
            salvar_status(task_id, int((i / total_partes) * 100), f"[Divisão] Processando parte {parte_index}")
            num_paginas = len(PdfReader(parte).pages)

            registros = processar_um_pdf(parte, task_id=task_id, parte_index=parte_index, total_paginas=num_paginas)
            todos.extend(registros)

        salvar_status(task_id, 99, "[Finalização] Salvando resultado final...")
        df = pd.DataFrame(todos)
        df.to_excel(output_path, index=False, encoding='utf-8')
        salvar_status(task_id, 100, "[Concluído] Arquivo de inconsistências salvo com sucesso.")

    except Exception as e:
        print(f"[ERRO FATAL] {str(e)}")
        salvar_status(task_id, 100, f"Erro: {str(e)}")
        raise

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("RECEBENDO DADOS...")

        task_id = sys.argv[1]
        input_path = sys.argv[2]
        output_path = sys.argv[3]

        try:
            processar_partes(task_id, input_path, output_path)
        except Exception as e:
            salvar_status(task_id, 0, f"Erro: {str(e)}")
            raise
    else:
        print("Modo de execução inválido ou argumentos ausentes.")
        sys.exit(1)