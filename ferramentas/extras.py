# -*- coding: utf-8 -*-
"""Especialidades completas (por endereco) e corpo clinico.

listaEspecialidadesPrestador exige cpfCnpj e devolve a lista inteira, sem o
"[...]" que buscaRede e detalhePrestador cortam. O corpo clinico so faz sentido
para estabelecimento - para os 201 medicos do CIM o "corpo clinico" e ele mesmo.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from api import call

det = json.load(open("dados/detalhes.json", encoding="utf-8"))
ESP, CC = "dados/esp_full.json", "dados/corpo_clinico.json"
esp = json.load(open(ESP, encoding="utf-8")) if os.path.exists(ESP) else {}
cc = json.load(open(CC, encoding="utf-8")) if os.path.exists(CC) else {}

INSTITUCIONAL = {"Hospital Geral", "Hospital Especializado", "Policlínica",
                 "Clínica | Centro de Especialidade", "SADT - Imagem",
                 "SADT - Análises Clínicas, Anatomia Patológica e Citopatologia",
                 "SADT - Terapias", "SADT - Terapias Especiais", "SADT - Oncologia",
                 "SADT - Outros", "Unidade Própria", "Próprio São José  Pinhais"}

falta_esp = [k for k, v in det.items() if v.get("cpf_cnpj") and k not in esp]
# corpo clinico e por CNPJ, nao por endereco
por_cnpj = {}
for k, v in det.items():
    if v.get("tipo_estabelecimento") in INSTITUCIONAL and v.get("cpf_cnpj"):
        por_cnpj.setdefault(v["cpf_cnpj"], k)
falta_cc = [(c, k) for c, k in por_cnpj.items() if c not in cc]
print(len(falta_esp), "especialidades +", len(falta_cc), "corpo clinico", flush=True)

for n, k in enumerate(falta_esp, 1):
    r = call("prestador/listaEspecialidadesPrestador",
             {"idOperadora": 33, "idPrestador": int(k), "cpfCnpj": det[k]["cpf_cnpj"]})
    lista = r.get("data") if isinstance(r, dict) else None
    esp[k] = [{"e": (x.get("descricao") or "").strip(),
               "end": (x.get("endereco") or "").strip(),
               "num": (x.get("numero") or "").strip(),
               "bai": (x.get("bairro") or "").strip(),
               "cid": (x.get("cidade") or "").strip()}
              for x in lista if (x.get("descricao") or "").strip()] if isinstance(lista, list) else []
    if n % 25 == 0:
        json.dump(esp, open(ESP, "w", encoding="utf-8"), ensure_ascii=False)
        print("  esp", n, "/", len(falta_esp), flush=True)
json.dump(esp, open(ESP, "w", encoding="utf-8"), ensure_ascii=False)
print("ESP OK", len(esp), flush=True)

for n, (cnpj, k) in enumerate(falta_cc, 1):
    r = call("prestador/corpoClinicoPrestador",
             {"idOperadora": 33, "idPrestador": int(k), "cpfCnpj": cnpj})
    lista = r.get("data") if isinstance(r, dict) else None
    cc[cnpj] = [{"n": (x.get("nome_corpo_clinico") or "").strip(),
                 "cr": " ".join(filter(None, [(x.get("sigla_conselho_regional") or "").strip(),
                                              (x.get("numero_conselho_regional") or "").strip(),
                                              (x.get("uf_conselho_regional") or "").strip()])),
                 "e": (x.get("descricao") or "").strip()}
                for x in lista if (x.get("nome_corpo_clinico") or "").strip()] if isinstance(lista, list) else []
    if n % 25 == 0:
        json.dump(cc, open(CC, "w", encoding="utf-8"), ensure_ascii=False)
        print("  cc", n, "/", len(falta_cc), flush=True)
json.dump(cc, open(CC, "w", encoding="utf-8"), ensure_ascii=False)
print("FIM esp=%d cc=%d (com equipe: %d)"
      % (len(esp), len(cc), len([v for v in cc.values() if v])), flush=True)
