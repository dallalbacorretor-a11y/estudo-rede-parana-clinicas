# -*- coding: utf-8 -*-
"""Monta o DADOS_UF da Parana Clinicas no formato que a pagina consome."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import (norm, cidade_bonita, LUGAR, CATEGORIAS, CATS_EXAME,
                    CIM_UNIDADE, PADRAO)

HOJE = "12/09/2026"

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

det = json.load(open("dados/detalhes.json", encoding="utf-8"))
espf = json.load(open("dados/esp_full.json", encoding="utf-8")) \
    if os.path.exists("dados/esp_full.json") else {}
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


def ender(r):
    p = (r.get("endereco") or "").strip()
    n = (r.get("numero") or "").strip()
    return (p + (", " + n if n else "")).upper()


def parte_esp(txt):
    """Separa 'A, B, C' sem quebrar dentro de parenteses."""
    return [s.strip().upper() for s in re.split(r",(?![^(]*\))", txt or "") if s.strip()]


# ------------------------------------------------------ 1) junta os 3 planos
# Uma linha por (prestador, endereco); cada uma sabe em que planos aparece e
# quais ids a representam (o id muda de plano para plano).
linhas = {}
for cod, prod in COD.items():
    for r in json.load(open("dados/rede2_%s.json" % cod, encoding="utf-8")):
        k = (norm(r.get("nome")), norm(r.get("endereco")),
             (r.get("numero") or "").strip(), (r.get("cep") or "").strip())
        e = linhas.get(k)
        if not e:
            e = linhas[k] = {"rows": [], "ids": [], "planos": set()}
        e["rows"].append(r)
        e["ids"].append(r["id"])
        e["planos"].add(prod)

for k, e in linhas.items():
    r = e["rows"][0]
    # o detalhe foi coletado para UM id por endereco; aceita qualquer um deles
    rid = next((str(i) for i in e["ids"] if str(i) in det), None)
    d = det.get(rid, {}) if rid else {}

    # especialidades: a lista completa vem de listaEspecialidadesPrestador,
    # que devolve por endereco; buscaRede e detalhePrestador cortam com [...]
    esp = []
    if rid and rid in espf:
        alvo = (norm(r.get("endereco")), (r.get("numero") or "").strip())
        esp = [x["e"].upper() for x in espf[rid]
               if (norm(x.get("end")), (x.get("num") or "").strip()) == alvo]
    if not esp and rid in espf:
        # alguns enderecos da busca nao constam na lista por endereco (a
        # operadora nao cadastrou); melhor a lista inteira do CNPJ do que o
        # texto cortado com [...]
        esp = [x["e"].upper() for x in espf[rid]]
    if not esp:
        txt = (d.get("especialidade") or "").strip()
        if "[...]" in txt or not txt:
            txt = (r.get("esp") or "").strip()
        esp = parte_esp(txt)

    tipo_est = (d.get("tipo_estabelecimento") or "").strip()
    lugar = LUGAR.get(tipo_est, PADRAO)
    cats = [lugar]
    unidade = CIM_UNIDADE.get(r.get("_classe"))
    if unidade:
        cats.append(unidade)

    e.update({
        "nome": (r.get("nome") or "").strip().upper(),
        "cnpj": cnpj_fmt(d.get("cpf_cnpj")),
        "cidade": cidade_bonita(r.get("_cidade") or d.get("nome_cidade")).upper(),
        "bairro": (r.get("bairro") or "").strip().upper(),
        "end": ender(r),
        "tels": [t for t in (fone(r.get("tel")), fone(r.get("tel_sec"))) if t],
        "email": (d.get("email") or "").strip().lower(),
        "acess": (d.get("acessibilidade") or "") == "S",
        "lugar": lugar, "cats": cats, "tipo_est": tipo_est,
        "esp": sorted(set(esp), key=esp.index),
        "xy": [num(r.get("lat")), num(r.get("lon"))],
    })

# ------------------------------------------------- 2) agrupa por prestador
# Chave: CNPJ quando existe (junta as varias unidades da mesma empresa);
# senao o nome normalizado - sem isso cada endereco viraria um "prestador".
grupos = {}
for e in linhas.values():
    k = e["cnpj"] or ("N:" + norm(e["nome"]))
    g = grupos.get(k)
    if not g:
        g = grupos[k] = {"n": e["nome"], "c": e["cnpj"], "cid": set(), "pp": {},
                         "b": set(), "e": set(), "t": set(), "p": set(),
                         "mail": set(), "acess": False,
                         "cats": set(), "pc": {}, "xy": None}
    g["cid"].add(e["cidade"])
    g["pp"].setdefault(e["cidade"], set()).update(e["planos"])
    if e["bairro"]:
        g["b"].add(e["bairro"])
    if e["end"]:
        g["e"].add(e["end"])
    g["t"].update(e["tels"])
    if e["email"]:
        g["mail"].add(e["email"])
    g["acess"] = g["acess"] or e["acess"]
    g["p"].update(e["planos"])
    for c in e["cats"]:
        g["cats"].add(c)
        g["pc"].setdefault(c, set()).update(e["esp"])
    if g["xy"] is None and e["xy"][0] is not None:
        g["xy"] = e["xy"]

ordem_prod = [p["codigo"] for p in PRODUTOS]
ordem_cat = {c: i for i, c in enumerate(CATEGORIAS)}


def ord_p(s):
    return sorted(s, key=lambda x: ordem_prod.index(x))


prestadores = []
for cnpj, g in grupos.items():
    lugares = [c for c in g["cats"] if c in ordem_cat] or [PADRAO]
    cat = sorted(lugares, key=lambda c: ordem_cat[c])[0]
    # o corpo clinico foi salvo com o CNPJ cru; a chave do grupo e formatada
    equipe = cc.get(re.sub(r"\D", "", cnpj)) or []
    prestadores.append({
        "n": g["n"], "c": g["c"],
        "cid": sorted(g["cid"]),
        "pp": {k: ord_p(v) for k, v in sorted(g["pp"].items())},
        "cr": sorted(g["cid"]),
        "b": sorted(g["b"]), "e": sorted(g["e"]), "t": sorted(g["t"]),
        "mail": sorted(g["mail"]),
        "acess": g["acess"],
        "eq": [[x["n"], x["cr"], x["e"]] for x in equipe],
        "p": ord_p(g["p"]),
        "cat": cat,
        "cats": sorted(g["cats"], key=lambda c: ordem_cat.get(c, 99)),
        "esp": sorted(set().union(*g["pc"].values())) if g["pc"] else [],
        "pc": {k: sorted(v) for k, v in sorted(g["pc"].items())},
        "s": [],
        "xy": g["xy"] or [None, None],
    })
# a tabela insere a faixa quando a categoria muda de uma linha para a outra -
# sem ordenar por categoria, a faixa se repete pagina afora
prestadores.sort(key=lambda p: (ordem_cat.get(p["cat"], 99), norm(p["n"])))

# ----------------------------------------------- 3) centros (bairro|cidade)
centros = {}
for e in linhas.values():
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

from collections import Counter
print("linhas (prestador+endereco):", len(linhas))
print("prestadores agrupados:", len(prestadores),
      "| sem CNPJ:", len([p for p in prestadores if not p["c"]]),
      "| sem coordenada:", len([p for p in prestadores if p["xy"][0] is None]))
print("sem tipo_estabelecimento:", len([e for e in linhas.values() if not e["tipo_est"]]))
print("com e-mail:", len([p for p in prestadores if p["mail"]]),
      "| com equipe medica:", len([p for p in prestadores if p["eq"]]),
      "| acessibilidade:", len([p for p in prestadores if p["acess"]]))
print("especialidades truncadas restantes:",
      len([p for p in prestadores for e in p["esp"] if "[...]" in e]))
for p in PRODUTOS:
    print("  %-12s %d prestadores" % (p["rotulo"],
          len([x for x in prestadores if p["codigo"] in x["p"]])))
for c in CATEGORIAS:
    n = len([p for p in prestadores if p["cat"] == c])
    if n:
        print("  %-34s %d" % (c, n))
print("cidades:", len(set(c for p in prestadores for c in p["cid"])))
