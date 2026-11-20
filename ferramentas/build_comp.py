# -*- coding: utf-8 -*-
"""A base única do estudo: concilia os 3 planos.

Página, planilhas por plano, comparativo (xlsx/HTML), PDFs e RESUMO saem
TODOS daqui - assim os totais por plano são os mesmos em qualquer arquivo.

Cada registro é um prestador num endereço (chave: CNPJ + logradouro + número,
ver common.chave_base). Três listas de plano por registro:
  oficial - planos em que ele aparece na busca oficial da operadora
  dir     - planos em que ele entra só por direcionamento interno (D)
  planos  - oficial + dir: o que a coluna do plano mostra (✔ ou D)
O total de um plano conta só `oficial`; o D é contado à parte.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import PLANOS, ORDEM_CAT, carrega, norm, planos_direcionados

ORDEM = [p[2] for p in PLANOS]


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
                if len(r["esp"]) > len(e["esp"]):
                    e["esp"] = r["esp"]; e["esp_lista"] = r["esp_lista"]
                e["inst"] = e.get("inst") or r.get("inst")
            e["planos"].add(curto)
    out = list(reg.values())
    for e in out:
        # o hospital de direcionamento não consta na busca daquele plano, mas é
        # acessível: entra na lista do plano, marcado com (D), e fica FORA do
        # total do plano (é informação do corretor, não da busca oficial)
        e["oficial"] = sorted(e["planos"], key=ORDEM.index)
        e["dir"] = [c for c in planos_direcionados(e.get("cnpj")) if c not in e["planos"]]
        e["planos"] = sorted(set(e["oficial"]) | set(e["dir"]), key=ORDEM.index)
    return out


def totais(d):
    """{curto: (rede oficial, só por direcionamento)} e a união da rede oficial."""
    por = {c: (sum(1 for x in d if c in x["oficial"]), sum(1 for x in d if c in x["dir"]))
           for c in ORDEM}
    return por, sum(1 for x in d if x["oficial"])


if __name__ == "__main__":
    d = concilia()
    json.dump([{k: v for k, v in x.items() if k != "chave"} for x in d],
              open("dados/comparativo.json", "w", encoding="utf-8"), ensure_ascii=False)
    from collections import Counter
    por, uniao = totais(d)
    print("prestadores (por endereço) na união da rede oficial:", uniao)
    for c, (n, nd) in por.items():
        print("  %-7s %d  +%d por direcionamento" % (c, n, nd))
    print(Counter(tuple(x["oficial"]) for x in d))
    print(Counter(x["categoria"] for x in d))
