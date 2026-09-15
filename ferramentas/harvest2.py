# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from api import call

PLANOS = {"236": "Parana 400 AHO QP COPART SR",
          "237": "Parana 600 AHO QC COPART SR",
          "234": "Parana CIM AHO QC COPART SR"}
OP = 33
log = open("harvest2.log", "w", encoding="utf-8")
def L(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); log.write(s+"\n"); log.flush()

def busca(plano, cidade="", tip=None, bairro=""):
    pl = {"idOperadora": OP, "idPlano": plano, "idEstado": "PR", "idCidade": cidade,
          "bairro": bairro, "espagr": "S", "secoes": "N", "orderAlfa": True, "orderDist": False}
    if tip: pl["tip"] = tip
    r = call("prestador/buscaRede", pl)
    if isinstance(r, dict) and r.get("status") and isinstance(r.get("data"), dict):
        return r["data"].get("rede", [])
    return []

for plano, nome in PLANOS.items():
    out = "dados/rede2_%s.json" % plano
    if os.path.exists(out):
        L("skip", plano); continue
    cid = call("regiao/listaCidades", {"idOperadora": OP, "idPlano": plano, "idEstado": "PR"})["data"]
    tip = call("prestador/tipoPrestador", {"idOperadora": OP, "idPlano": plano, "idEstado": "PR", "idCidade": "", "bairro": ""})["data"]
    L("===", plano, nome, len(cid), "cidades x", len(tip), "tipos")
    linhas = {}
    for c in cid:
        tot = 0
        for t in tip:
            rows = busca(plano, c["codigo_IBGE"], t["classe"])
            if len(rows) >= 200:
                brs = call("regiao/listaBairros", {"idOperadora": OP, "idPlano": plano,
                           "idEstado": "PR", "idCidade": c["codigo_IBGE"]})
                brs = brs.get("data", []) if isinstance(brs, dict) else []
                sub = []
                for b in brs:
                    bn = b.get("nome") or b.get("bairro")
                    rr = busca(plano, c["codigo_IBGE"], t["classe"], bn)
                    if len(rr) >= 200: L("   !! CAP", c["nome"], t["descricao"], bn)
                    sub.extend(rr)
                L("   drill", c["nome"], t["descricao"], "->", len(sub), "via", len(brs), "bairros")
                rows = sub
            for r in rows:
                r["_cidade"] = c["nome"]; r["_tipo"] = t["descricao"]; r["_classe"] = t["classe"]
                linhas.setdefault(r["id"], r)
            tot += len(rows)
        L("  %-24s %d" % (c["nome"], tot))
    json.dump(list(linhas.values()), open(out, "w", encoding="utf-8"), ensure_ascii=False)
    L("==>", plano, len(linhas), "prestadores/enderecos unicos")
L("FIM")
