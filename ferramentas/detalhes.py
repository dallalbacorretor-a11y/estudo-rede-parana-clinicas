# -*- coding: utf-8 -*-
"""Puxa o detalhe de cada prestador (CNPJ, razao social, lat/lon, especialidades completas)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from api import call

OUT = "dados/detalhes.json"
cache = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}

# O mesmo prestador/endereco tem um id por plano. Basta o detalhe de UM
# representante por (nome, endereco, numero, cep) - o resto e o mesmo cadastro.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import norm

rep = {}
for cod in ("236", "237", "234"):
    for r in json.load(open("dados/rede2_%s.json" % cod, encoding="utf-8")):
        k = (norm(r.get("nome")), norm(r.get("endereco")),
             (r.get("numero") or "").strip(), (r.get("cep") or "").strip())
        rep.setdefault(k, r["id"])
ids = set(rep.values())
falta = sorted(i for i in ids if str(i) not in cache)
print(len(ids), "prestadores,", len(falta), "faltando", flush=True)

CAMPOS = ("id_prestador", "nome_prestador", "razao_social", "cpf_cnpj", "endereco", "numero",
          "complemento", "bairro", "cep", "telefone_primario", "telefone_secundario",
          "latitude", "longitude", "nome_cidade", "ibge_cidade", "tipo_prestador",
          "id_tipo_prestador", "tipo_estabelecimento", "especialidade", "atend_24_horas",
          "acessibilidade", "email", "site_url")

for n, pid in enumerate(falta, 1):
    r = call("prestador/detalhePrestador", {"idOperadora": 33, "idPrestador": pid, "espagr": "S"})
    d = r.get("data") if isinstance(r, dict) else None
    cache[str(pid)] = {k: d.get(k) for k in CAMPOS} if isinstance(d, dict) else {}
    if n % 25 == 0:
        json.dump(cache, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print(" ", n, "/", len(falta), flush=True)
json.dump(cache, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
com_cnpj = len([v for v in cache.values() if v.get("cpf_cnpj")])
print("FIM", len(cache), "detalhes,", com_cnpj, "com CNPJ", flush=True)
