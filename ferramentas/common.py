# -*- coding: utf-8 -*-
import json, re, unicodedata

PLANOS = [("236", "Paraná 400 AHO QP COPART SR", "400 QP", "507887263"),
          ("237", "Paraná 600 AHO QC COPART SR", "600 QC", "507885267"),
          ("234", "Paraná CIM AHO QC COPART SR", "CIM QC", "507888261")]

CAT = {"1": "Hospitais", "2": "Clínicas e Consultórios", "3": "Clínicas e Consultórios",
       "4": "Unidades próprias (CIM)", "5": "Unidades próprias (CIM)",
       "6": "Unidades próprias (CIM)", "7": "Unidades próprias (CIM)",
       "8": "Laboratórios e Imagem"}
ORDEM_CAT = ["Hospitais", "Unidades próprias (CIM)", "Clínicas e Consultórios", "Laboratórios e Imagem"]

def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s).upper()
    return re.sub(r"\s+", " ", s).strip()

def tel(t):
    t = re.sub(r"\D", "", t or "")
    if len(t) == 11: return "(%s) %s-%s" % (t[:2], t[2:7], t[7:])
    if len(t) == 10: return "(%s) %s-%s" % (t[:2], t[2:6], t[6:])
    return t or ""

def endereco(r):
    p = [r.get("endereco", "").strip()]
    n = (r.get("numero") or "").strip()
    if n: p.append(n)
    c = (r.get("complemento") or "").strip()
    if c: p.append(c)
    return ", ".join(x for x in p if x)

import os
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
_ESP = json.load(open("dados/esp_cache.json", encoding="utf-8")) if os.path.exists("dados/esp_cache.json") else {}

KW = ("HOSPITAL","CLINIC","CENTRO","LABORAT","INSTITUT","CIM ","SANTA CASA","MATERNIDADE","POLICLINIC",
      "IMAGEM","DIAGNOST","MEDICINA","ONCO","CARDIO","LTDA","ASSOCIA","FUNDAC","UNIDADE","PRONTO",
      "AMBULATOR","NUCLEO","MEDICAL","SAUDE","VITA","RADIOLOG","PATOLOG","CITOPATOL","ENDOSCOP",
      "OFTALMO","ORTOPED","NEURO","DERMA","UROLOG","GASTRO","REUMATO","PNEUMO","OTORRINO","FISIOTERAP",
      "CENTER","HEMATO","NEFRO","MASTOL","REPRODU","SONO","VACINA","CEDIL","GRUPO"," S A "," ME ")

def institucional(nome, classe):
    if classe in ("1", "8"):
        return True
    n = " " + norm(nome) + " "
    return any(k in n for k in KW)

def carrega(cod):
    rows = json.load(open("dados/rede2_%s.json" % cod, encoding="utf-8"))
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "nome": (r.get("nome") or "").strip(),
            "chave": (norm(r.get("nome")), norm(r.get("endereco")), (r.get("numero") or "").strip(), (r.get("cep") or "").strip()),
            "categoria": CAT.get(r.get("_classe"), "Outros"),
            "tipo": r.get("_tipo", ""),
            "cidade": r.get("_cidade", ""),
            "bairro": (r.get("bairro") or "").strip(),
            "endereco": endereco(r),
            "cep": (r.get("cep") or "").strip(),
            "tel": tel(r.get("tel")),
            "tel2": tel(r.get("tel_sec")),
            "esp": (_ESP.get(str(r["id"])) or r.get("esp") or "").strip(),
            "inst": institucional(r.get("nome"), r.get("_classe")),
        })
    return out
