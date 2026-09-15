# -*- coding: utf-8 -*-
"""Monta o DADOS_UF da Parana Clinicas no mesmo formato do site da Amil."""
import sys, os, json, re, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import norm

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

# O app classifica prestador por estes nomes exatos (sem acento, como a Amil
# publica) - mudar a grafia quebra o panorama e as secoes do PDF. O CIM entra
# como categoria extra E como clinica, para ser filtravel sem perder a logica.
CLINICA = "Clinicas e consultorios"
CIM = "Unidades próprias (CIM)"
CAT = {"1": ["Hospitais"], "2": [CLINICA], "3": [CLINICA],
       "4": [CIM, CLINICA], "5": [CIM, CLINICA], "6": [CIM, CLINICA],
       "7": [CIM, CLINICA], "8": ["Laboratorios e imagem"]}
CATEGORIAS = ["Hospitais", CIM, CLINICA, "Laboratorios e imagem"]

det = json.load(open("dados/detalhes.json", encoding="utf-8"))


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


# ---------------------------------------------------------------- 1) linhas
# Uma linha por (prestador, endereco). Cada uma sabe em que planos aparece.
linhas = {}
for cod, prod in COD.items():
    for r in json.load(open("dados/rede2_%s.json" % cod, encoding="utf-8")):
        k = (norm(r.get("nome")), norm(r.get("endereco")),
             (r.get("numero") or "").strip(), (r.get("cep") or "").strip())
        d = det.get(str(r["id"]), {})
        e = linhas.get(k)
        if not e:
            esp = (d.get("especialidade") or r.get("esp") or "").strip()
            if "[...]" in esp:
                esp = (r.get("esp") or "").strip()
            e = linhas[k] = {
                "nome": (r.get("nome") or "").strip().upper(),
                "cnpj": cnpj_fmt(d.get("cpf_cnpj")),
                "cidade": (r.get("_cidade") or d.get("nome_cidade") or "").upper(),
                "bairro": (r.get("bairro") or "").strip().upper(),
                "end": ender(r),
                "tels": [t for t in (fone(r.get("tel")), fone(r.get("tel_sec"))) if t],
                "cats": CAT.get(r.get("_classe"), [CLINICA]),
                "tipo": r.get("_tipo", ""),
                "esp": [s.strip().upper() for s in re.split(r",(?![^(]*\))", esp) if s.strip()],
                "xy": [num(r.get("lat")), num(r.get("lon"))],
                "planos": set(),
            }
        e["planos"].add(prod)

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
                         "cats": set(), "pc": {}, "xy": None, "_cat": {}}
    g["cid"].add(e["cidade"])
    g["pp"].setdefault(e["cidade"], set()).update(e["planos"])
    if e["bairro"]:
        g["b"].add(e["bairro"])
    if e["end"]:
        g["e"].add(e["end"])
    g["t"].update(e["tels"])
    g["p"].update(e["planos"])
    for c in e["cats"]:
        g["cats"].add(c)
        g["pc"].setdefault(c, set()).update(e["esp"])
        g["_cat"][c] = g["_cat"].get(c, 0) + 1
    if g["xy"] is None and e["xy"][0] is not None:
        g["xy"] = e["xy"]

ordem_prod = [p["codigo"] for p in PRODUTOS]
ordem_cat = {c: i for i, c in enumerate(CATEGORIAS)}


def ord_p(s):
    return sorted(s, key=lambda x: ordem_prod.index(x))


def tipo_de(cats, pc):
    """Mesma regra do app: hospital manda; fora isso vale o que ele mais oferece.
    Precisa bater com a do JS, senao a tabela repete a faixa de categoria."""
    if "Hospitais" in cats:
        return "Hospitais"
    exames = len(pc.get("Laboratorios e imagem", ()))
    consultas = len(pc.get(CLINICA, ()))
    if exames > consultas:
        return "Laboratorios e imagem"
    if consultas > 0:
        return CLINICA
    if exames > 0:
        return "Laboratorios e imagem"
    return CLINICA


prestadores = []
for g in grupos.values():
    # Categoria principal: a mais "forte" (hospital ganha de clinica) e, em
    # empate, a que aparece em mais enderecos.
    cat = tipo_de(g["cats"], g["pc"])
    esp = sorted(set().union(*g["pc"].values())) if g["pc"] else []
    # o CIM nao pode ser a categoria principal: o app so entende as tres da Amil
    prestadores.append({
        "n": g["n"], "c": g["c"],
        "cid": sorted(g["cid"]),
        "pp": {k: ord_p(v) for k, v in sorted(g["pp"].items())},
        "cr": sorted(g["cid"]),
        "b": sorted(g["b"]), "e": sorted(g["e"]), "t": sorted(g["t"]),
        "p": ord_p(g["p"]),
        "cat": cat,
        "cats": sorted(g["cats"], key=lambda c: ordem_cat.get(c, 99)),
        "esp": esp,
        "pc": {k: sorted(v) for k, v in sorted(g["pc"].items())},
        "s": [],
        "xy": g["xy"] or [None, None],
    })
# a tabela insere a faixa quando a categoria muda de uma linha para a
# outra - sem ordenar por categoria, a faixa se repete pagina afora
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
    "prestadores": prestadores,
}}
json.dump(dados, open("dados/dados_pc.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

sem_cnpj = len([p for p in prestadores if not p["c"]])
sem_xy = len([p for p in prestadores if p["xy"][0] is None])
print("linhas (prestador+endereco):", len(linhas))
print("prestadores agrupados:", len(prestadores), "| sem CNPJ:", sem_cnpj, "| sem coordenada:", sem_xy)
print("centros (bairros):", len(centros))
for p in PRODUTOS:
    print("  %-12s %d prestadores" % (p["rotulo"], len([x for x in prestadores if p["codigo"] in x["p"]])))
from collections import Counter
print(Counter(p["cat"] for p in prestadores))
print("cidades:", len(set(c for p in prestadores for c in p["cid"])))
