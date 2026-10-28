# -*- coding: utf-8 -*-
"""O que é dado pessoal e não entra em nada que é publicado (página, planilhas, PDFs, JSON).

A API da operadora devolve o CPF no lugar do CNPJ quando o prestador é médico
pessoa física, e às vezes o e-mail pessoal dele. O repositório é público: CPF
nunca entra, e e-mail só o institucional (de prestador com CNPJ e domínio próprio).

O CPF continua necessário para uma chamada da API (listaEspecialidadesPrestador,
em extras.py). Ele fica só no computador, em dados/_privado.json (no .gitignore).
"""
import json, os, re

PRIVADO = "dados/_privado.json"
WEBMAIL = re.compile(r"@(gmail|googlemail|hotmail|yahoo|ymail|rocketmail|outlook|live|msn|bol|uol|terra|icloud|"
                     r"me|ig|globo|r7|zipmail|oi|aol|protonmail|proton)\.", re.I)


def eh_cpf(doc):
    return len(re.sub(r"\D", "", doc or "")) == 11


def documento_publico(doc):
    """CNPJ fica; CPF vira vazio (a página mostra "sem CNPJ")."""
    return "" if eh_cpf(doc) else (doc or "").strip()


def email_publico(email, doc=""):
    email = (email or "").strip().lower()
    if not email or eh_cpf(doc) or WEBMAIL.search(email):
        return ""
    return email


def limpa_detalhe(d):
    """Detalhe da API sem CPF e sem e-mail pessoal (o que vai para dados/detalhes.json)."""
    if not isinstance(d, dict):
        return d
    d = dict(d)
    doc = d.get("cpf_cnpj") or ""
    d["email"] = email_publico(d.get("email"), doc) or None
    if eh_cpf(doc):
        d["cpf_cnpj"] = ""
    return d


def _le():
    return json.load(open(PRIVADO, encoding="utf-8")) if os.path.exists(PRIVADO) else {}


def guarda_cpfs(detalhes):
    """Guarda (só no computador) o CPF de cada id antes de ele sair do detalhe."""
    priv = _le()
    novos = {k: v["cpf_cnpj"] for k, v in detalhes.items()
             if isinstance(v, dict) and eh_cpf(v.get("cpf_cnpj")) and priv.get(k) != v["cpf_cnpj"]}
    if novos:
        priv.update(novos)
        json.dump(priv, open(PRIVADO, "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True)
    return priv


def cpf_de(pid):
    return _le().get(str(pid), "")
