import pandas as pd
import re
import sys
from datetime import datetime
from pathlib import Path

xlsx_path = sys.argv[1]
txt_path = sys.argv[2]

df = pd.read_excel(xlsx_path, dtype=str)
df['CPF'] = df['CPF'].str.replace(r'\D+', '', regex=True)
df['DOB'] = pd.to_datetime(df['DATA DE NASCIMENTO'], dayfirst=True, errors='coerce') \
              .dt.strftime('%d%m%Y') \
              .fillna('00000000')
df['NAME'] = df['NOME'].fillna('')

with open(txt_path, 'r', encoding='utf-8') as f:
    header = []
    template = None
    for line in f:
        if line.startswith('TA') and 'AE' in line:
            template = line.rstrip('\r\n')
            break
        header.append(line.rstrip('\r\n'))

template_length = len(template)
nome_contrato_len = 27

m_num = re.search(r'0\d{19}', template)
start_num, end_num = m_num.start(), m_num.end()
numeric_width = end_num - start_num

ae_pos = template.find('AE', end_num)
start_name = ae_pos + 2

m_cnt = re.search(r'\d+$', template)
start_cnt, end_cnt = m_cnt.start(), m_cnt.end()
counter_width = end_cnt - start_cnt

static_mid = template[end_num:start_name]
name_width = start_cnt - start_name
suffix = template[end_cnt:]

hoje = datetime.now().strftime('%Y%m%d')

output_file = Path(txt_path).with_name('VA_EDITADO.txt')

with open(output_file, 'w', encoding='utf-8') as out:
    for hidx, hline in enumerate(header):
        hline_new = re.sub(r'\d{8}', hoje, hline)
        cnt_block = str(hidx + 1).zfill(counter_width)
        if len(hline_new) >= end_cnt:
            hline_new = hline_new[:start_cnt] + cnt_block + hline_new[end_cnt:]
        else:
            hline_new = hline_new.ljust(template_length - counter_width) + cnt_block
        out.write(hline_new + '\n')

    header_lines = len(header)
    for idx, row in df.iterrows():
        contrato_block = str(row['CONTRATO'])[:nome_contrato_len].ljust(nome_contrato_len)
        num_block = ('0' + row['CPF'] + row['DOB']).ljust(numeric_width)
        name_block = row['NAME'][:name_width].ljust(name_width)
        cnt_block = str(header_lines + idx + 1).zfill(counter_width)

        linha = list(template)
        linha[5:5 + nome_contrato_len] = list(contrato_block)
        linha[start_num:end_num] = list(num_block)
        linha[start_name:start_cnt] = list(name_block)
        linha[start_cnt:end_cnt] = list(cnt_block)

        final_line = ''.join(linha)
        assert len(final_line) == template_length, (
            f"Linha {header_lines + idx + 1} tem {len(final_line)} chars; deveria ter {template_length}"
        )
        out.write(final_line + '\n')

print(str(output_file.resolve()))