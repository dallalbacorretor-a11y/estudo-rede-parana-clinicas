# -*- coding: utf-8 -*-
"""Concilia os 3 planos e gera o comparativo (xlsx)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import PLANOS, ORDEM_CAT, carrega, norm, planos_direcionados

def concilia():
    reg = {}
    for cod, nome, curto, ans in PLANOS:
        for r in carrega(cod):
            k = r["chave"]
            e = reg.get(k)
            if not e:
                e = dict(r); e["planos"] = set(); reg[k] = e
            else:
                # mantém a descrição de especialidades mais completa
                if len(r["esp"]) > len(e["esp"]): e["esp"] = r["esp"]
                e["inst"] = e.get("inst") or r.get("inst")
            e["planos"].add(curto)
    out = list(reg.values())
    ordem = [p[2] for p in PLANOS]
    for e in out:
        # o hospital de direcionamento não consta na busca daquele plano, mas é
        # acessível: entra na lista do plano e fica marcado com (D)
        e["dir"] = planos_direcionados(e.get("cnpj"))
        e["planos"] = sorted(set(e["planos"]) | set(e["dir"]), key=ordem.index)
    return out

if __name__ == "__main__":
    d = concilia()
    json.dump([{k: v for k, v in x.items() if k != "chave"} for x in d],
              open("dados/comparativo.json", "w", encoding="utf-8"), ensure_ascii=False)
    from collections import Counter
    print("prestadores/endereços únicos:", len(d))
    print(Counter(len(x["planos"]) for x in d))
    print(Counter(tuple(x["planos"]) for x in d))
    print(Counter(x["categoria"] for x in d))
