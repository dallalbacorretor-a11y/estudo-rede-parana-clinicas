# -*- coding: utf-8 -*-
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import PLANOS, ORDEM_CAT, norm, NOTA_CONTAGEM, DATA_COLETA
from build_comp import concilia
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE = _local.RAIZ
D1 = os.path.join(BASE, "01 - REDE CREDENCIADA", "Paraná Clínicas")
D2 = os.path.join(BASE, "02 - COMPARATIVOS DE REDE")
# vermelho da operadora, igual a pagina e aos PDFs
MARCA = "8E0E28"; CINZA = "F2F2F2"
thin = Side(style="thin", color="D9D9D9")
BORD = Border(left=thin, right=thin, top=thin, bottom=thin)

def estiliza(ws, ncols, larguras):
    for c in range(1, ncols+1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor=MARCA)
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = larguras[c-1]
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.font = Font(size=9)
            cell.border = BORD

COLS = ["Categoria", "Tipo (operadora)", "Prestador", "CNPJ", "Especialidades",
        "Cidade", "Bairro", "Endereço", "CEP", "Telefone", "Telefone 2", "E-mail",
        "No plano"]
LARG = [26, 30, 42, 20, 46, 20, 22, 44, 12, 16, 16, 32, 10]

def sheet_rede(ws, dados, curto):
    ws.append(COLS)
    dados = sorted(dados, key=lambda r: (ORDEM_CAT.index(r["categoria"]) if r["categoria"] in ORDEM_CAT else 99,
                                         r["cidade"], norm(r["nome"]), r["bairro"]))
    for r in dados:
        # D = direcionamento interno (igual à página): consta na lista, fora do total
        ws.append([r["categoria"], r["tipo"], r["nome"], r["cnpj"], r["esp"],
                   r["cidade"], r["bairro"], r["endereco"], r["cep"],
                   r["tel"], r["tel2"], r["email"],
                   "D" if curto in r["dir"] else "✔"])
    estiliza(ws, len(COLS), LARG)

# ---- 1) um xlsx por plano, da mesma base do comparativo, da página e dos PDFs
from collections import Counter
base = concilia()
todos = {}
for cod, nome, curto, ans in PLANOS:
    dados = [x for x in base if curto in x["planos"]]
    rede = [x for x in dados if curto in x["oficial"]]
    dirs = [x for x in dados if curto in x["dir"]]
    todos[cod] = [{k: v for k, v in x.items() if k != "chave"} for x in dados]
    wb = Workbook(); ws = wb.active; ws.title = "Rede"
    sheet_rede(ws, dados, curto)
    ws2 = wb.create_sheet("Resumo")
    ws2.append(["Plano", nome]); ws2.append(["Registro ANS", ans])
    ws2.append(["Código do plano (busca)", cod])
    ws2.append(["Data da coleta", DATA_COLETA]); ws2.append([])
    ws2.append(["Categoria", "Prestadores"])
    cc = Counter(r["categoria"] for r in rede)
    for c in ORDEM_CAT:
        if cc.get(c): ws2.append([c, cc[c]])
    ws2.append(["TOTAL (rede da busca oficial)", len(rede)])
    ws2.append(["Por direcionamento interno (D), à parte", len(dirs)])
    for x in dirs:
        ws2.append(["   D · " + x["nome"], x["cidade"]])
    ws2.append([])
    ws2.append(["Cidade", "Prestadores"])
    cd = Counter(r["cidade"] for r in rede)
    for c, n in sorted(cd.items(), key=lambda x: -x[1]): ws2.append([c, n])
    ws2.append([])
    ws2.append([NOTA_CONTAGEM])
    for col, w in (("A", 40), ("B", 24)): ws2.column_dimensions[col].width = w
    for cel in ("A1", "A2", "A3", "A5", "B5"): ws2[cel].font = Font(bold=True)
    fn = os.path.join(D1, "REDE %s.xlsx" % nome.upper().replace("PARANÁ ", "PARANA "))
    wb.save(fn); print("ok", fn, len(rede), "+%d D" % len(dirs))

json.dump({k: v for k, v in todos.items()}, open("dados/todos.json", "w", encoding="utf-8"), ensure_ascii=False)
