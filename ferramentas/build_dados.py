# -*- coding: utf-8 -*-
"""Monta o DADOS_UF da Parana Clinicas no formato que a pagina consome."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import norm, CATEGORIAS, CATS_EXAME, PADRAO
from build_comp import concilia

from common import DATA_COLETA as HOJE   # data da coleta da rede

PRODUTOS = [
    {"codigo": "p400", "rotulo": "Paraná 400", "acomodacao": "QP · apartamento",
     "linha": "Paraná Clínicas", "cor": "#a80a32", "ans": "507887263",
     "nome": "Paraná 400 AHO QP COPART SR"},
    {"codigo": "p600", "rotulo": "Paraná 600", "acomodacao": "QC · enfermaria",
     "linha": "Paraná Clínicas", "cor": "#6b3f8f", "ans": "507885267",
     "nome": "Paraná 600 AHO QC COPART SR"},
    {"codigo": "cim", "rotulo": "Paraná CIM", "acomodacao": "QC · enfermaria",
     "linha": "Paraná Clínicas", "cor": "#b5761b", "ans": "507888261",
     "nome": "Paraná CIM AHO QC COPART SR"},
]
COD = {"236": "p400", "237": "p600", "234": "cim"}

# As categorias, a ordem e o mapa de tipo_estabelecimento vivem no common:
# a pagina e os arquivos de escritorio precisam classificar igual.

cc = json.load(open("dados/corpo_clinico.json", encoding="utf-8")) \
    if os.path.exists("dados/corpo_clinico.json") else {}


def num(v):
    """A API mistura '-25,4255148' e '-25.4255148'."""
    try:
        return round(float(str(v).replace(",", ".")), 5)
    except (TypeError, ValueError):
        return None


def fone(t):
    t = re.sub(r"\D", "", t or "")
    if len(t) == 11:
        return "%s-%s-%s" % (t[:2], t[2:7], t[7:])
    if len(t) == 10:
        return "%s-%s-%s" % (t[:2], t[2:6], t[6:])
    return ""


def cnpj_fmt(c):
    c = re.sub(r"\D", "", c or "")
    if len(c) == 14:
        return "%s.%s.%s/%s-%s" % (c[:2], c[2:5], c[5:8], c[8:12], c[12:])
    if len(c) == 11:
        return "%s.%s.%s-%s" % (c[:3], c[3:6], c[6:9], c[9:])
    return c


# ------------------------------------------------ 1) a base única do estudo
# A página sai da MESMA base das planilhas, do comparativo e dos PDFs
# (build_comp.concilia): um registro por prestador e endereço (CNPJ +
# logradouro + número), com a rede oficial e o direcionamento (D) separados.
# Antes a página agrupava por CNPJ e contava 373/456/208 "prestadores",
# enquanto os outros arquivos contavam endereços - dois números para a mesma
# rede. Agora uma linha da tabela é um endereço, como no comparativo.
ordem_prod = [p["codigo"] for p in PRODUTOS]
CURTO_COD = {"400 QP": "p400", "600 QC": "p600", "CIM QC": "cim"}
ordem_cat = {c: i for i, c in enumerate(CATEGORIAS)}


def ord_p(s):
    return sorted(s, key=lambda x: ordem_prod.index(x))


linhas = []
for x in concilia():
    cats = [x["categoria"]]
    if x.get("unidade"):
        cats.append(x["unidade"])
    esp = [e.upper() for e in (x.get("esp_lista") or [])]
    linhas.append({
        "nome": x["nome"].upper(),
        "cnpj": cnpj_fmt(x["cnpj"]),
        "cidade": x["cidade"].upper(),
        "bairro": (x["bairro"] or "").upper(),
        "end": (x["logradouro"] or "").upper(),
        "tels": [t for t in (fone(x["tel"]), fone(x["tel2"])) if t],
        "email": x["email"],
        "acess": x["acess"],
        "lugar": x["categoria"], "cats": cats,
        "esp": sorted(set(esp), key=esp.index),
        "xy": [num(x.get("lat")), num(x.get("lon"))],
        # o total do plano conta so a rede oficial; o D entra na lista, a parte
        "planos": ord_p({CURTO_COD[c] for c in x["planos"]}),
        "dirs": ord_p({CURTO_COD[c] for c in x["dir"]}),
    })

prestadores = []
for e in linhas:
    # o corpo clinico foi salvo com o CNPJ cru
    equipe = cc.get(re.sub(r"\D", "", e["cnpj"])) or []
    prestadores.append({
        "n": e["nome"], "c": e["cnpj"],
        "cid": [e["cidade"]],
        "pp": {e["cidade"]: e["planos"]},
        "cr": [e["cidade"]],
        "b": [e["bairro"]] if e["bairro"] else [],
        "e": [e["end"]] if e["end"] else [],
        "t": sorted(set(e["tels"])),
        "mail": [e["email"]] if e["email"] else [],
        "acess": e["acess"],
        "eq": [[m["n"], m["cr"], m["e"]] for m in equipe],
        "p": e["planos"],
        "dir": e["dirs"],
        "cat": e["lugar"] or PADRAO,
        "cats": sorted(e["cats"], key=lambda c: ordem_cat.get(c, 99)),
        "esp": sorted(set(e["esp"])),
        "pc": {c: sorted(set(e["esp"])) for c in sorted(e["cats"])},
        "s": [],
        "xy": e["xy"] if e["xy"][0] is not None else [None, None],
    })
prestadores.sort(key=lambda p: (ordem_cat.get(p["cat"], 99), norm(p["n"])))

# ----------------------------------------------- 3) centros (bairro|cidade)
centros = {}
for e in linhas:
    if e["xy"][0] is None or not e["bairro"]:
        continue
    k = "%s|%s" % (norm(e["bairro"]), norm(e["cidade"]))
    c = centros.setdefault(k, [0.0, 0.0, 0])
    c[0] += e["xy"][0]; c[1] += e["xy"][1]; c[2] += 1
centros = {k: [round(v[0] / v[2], 5), round(v[1] / v[2], 5), v[2]]
           for k, v in centros.items()}

dados = {"PR": {
    "gerado_em": HOJE,
    "centros": centros,
    "uf": "PR",
    "estado": "Curitiba e Região",
    "nota": "",
    "produtos": PRODUTOS,
    "categorias": CATEGORIAS,
    "catsExame": CATS_EXAME,
    "prestadores": prestadores,
}}
json.dump(dados, open("dados/dados_pc.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("prestadores (um por endereço):", len(prestadores),
      "| sem CNPJ:", len([p for p in prestadores if not p["c"]]),
      "| sem coordenada:", len([p for p in prestadores if p["xy"][0] is None]))
for p in PRODUTOS:
    rede = [x for x in prestadores if p["codigo"] in x["p"] and p["codigo"] not in x["dir"]]
    dirs = [x for x in prestadores if p["codigo"] in x["dir"]]
    print("  %-12s %d prestadores  +%d por direcionamento" % (p["rotulo"], len(rede), len(dirs)))
print("cidades:", len(set(c for p in prestadores for c in p["cid"])))
