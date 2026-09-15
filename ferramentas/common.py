# -*- coding: utf-8 -*-
"""Base compartilhada: classificação, normalização e leitura da coleta.

Os arquivos de escritório (xlsx, PDF, comparativo) e a página usam a MESMA
classificação, que sai daqui — se divergirem, o cliente recebe dois materiais
que se contradizem.
"""
import json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)

PLANOS = [("236", "Paraná 400 AHO QP COPART SR", "400 QP", "507887263"),
          ("237", "Paraná 600 AHO QC COPART SR", "600 QC", "507885267"),
          ("234", "Paraná CIM AHO QC COPART SR", "CIM QC", "507888261")]

# ---------------------------------------------------------------- categorias
# A operadora classifica em dois campos. `tipo_prestador` (8 classes) é grosso
# demais: joga os centros de imagem dentro de "Clínica", e quem procura
# ressonância não acha. `tipo_estabelecimento` separa de verdade — inclusive
# hospital geral de especializado, que é a pergunta de quem quer saber onde
# interna. É este que manda.
LUGAR = {
    "Hospital Geral": "Hospitais gerais",
    "Hospital Especializado": "Hospitais especializados",
    "Unidade Própria": "Unidades próprias CIM",
    "Próprio São José  Pinhais": "Unidades próprias CIM",
    "Corpo Clínico": "Médicos dos CIM",
    "Policlínica": "Clínicas e policlínicas",
    "Clínica | Centro de Especialidade": "Clínicas e policlínicas",
    "Consultório": "Consultórios",
    "SADT - Imagem": "Diagnóstico por imagem",
    "SADT - Análises Clínicas, Anatomia Patológica e Citopatologia":
        "Laboratórios e análises clínicas",
    "SADT - Terapias": "Terapias",
    "SADT - Terapias Especiais": "Terapias",
    "SADT - Oncologia": "Oncologia",
    "SADT - Outros": "Exames e procedimentos",
}
# Ordem de exibição e de precedência: quando um CNPJ tem endereços de tipos
# diferentes, a categoria principal é a primeira desta lista que ele tiver.
CATEGORIAS = ["Hospitais gerais", "Hospitais especializados",
              "Unidades próprias CIM", "Diagnóstico por imagem",
              "Laboratórios e análises clínicas", "Oncologia",
              "Exames e procedimentos", "Terapias",
              "Clínicas e policlínicas", "Consultórios", "Médicos dos CIM"]
ORDEM_CAT = CATEGORIAS
# Onde se faz exame ou procedimento marcado.
CATS_EXAME = ["Diagnóstico por imagem", "Laboratórios e análises clínicas",
              "Exames e procedimentos", "Oncologia"]
PADRAO = "Consultórios"
# Estabelecimento, por oposição a profissional — é o corte do PDF "Principais".
PESSOAIS = {"Consultórios", "Médicos dos CIM"}
# A unidade CIM de cada médico vem do outro campo.
CIM_UNIDADE = {"4": "CIM Água Verde", "5": "CIM CIC",
               "6": "CIM São José dos Pinhais", "7": "CIM Araucária"}


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s).upper()
    return re.sub(r"\s+", " ", s).strip()


# A operadora publica parte das cidades sem acento ("Sao Jose dos Pinhais").
# Corrigir aqui vale para a página, as planilhas e os PDFs de uma vez.
CIDADES = {"ARAUCARIA": "Araucária", "BOCAIUVA DO SUL": "Bocaiúva do Sul",
           "ITAPERUCU": "Itaperuçu", "SAO JOSE DOS PINHAIS": "São José dos Pinhais",
           "ALMIRANTE TAMANDARE": "Almirante Tamandaré"}


def cidade_bonita(c):
    return CIDADES.get(norm(c), (c or "").strip())


def tel(t):
    t = re.sub(r"\D", "", t or "")
    if len(t) == 11:
        return "(%s) %s-%s" % (t[:2], t[2:7], t[7:])
    if len(t) == 10:
        return "(%s) %s-%s" % (t[:2], t[2:6], t[6:])
    return t or ""


def endereco(r):
    p = [r.get("endereco", "").strip()]
    n = (r.get("numero") or "").strip()
    if n:
        p.append(n)
    c = (r.get("complemento") or "").strip()
    if c:
        p.append(c)
    return ", ".join(x for x in p if x)


def chave(r):
    return (norm(r.get("nome")), norm(r.get("endereco")),
            (r.get("numero") or "").strip(), (r.get("cep") or "").strip())


def _ler(nome):
    p = "dados/" + nome
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


_DET = _ler("detalhes.json")
_ESPF = _ler("esp_full.json")
_ESPC = _ler("esp_cache.json")

# O id do prestador muda de plano para plano; o detalhe foi coletado para um id
# por endereço. Este índice diz, para cada endereço, qual id tem detalhe.
_RID = {}
for _cod, _n, _c, _a in PLANOS:
    for _r in json.load(open("dados/rede2_%s.json" % _cod, encoding="utf-8")):
        _k = chave(_r)
        if _k not in _RID and str(_r["id"]) in _DET:
            _RID[_k] = str(_r["id"])


def _parte(txt):
    return [s.strip() for s in re.split(r",(?![^(]*\))", txt or "") if s.strip()]


def especialidades(r):
    """Lista completa. buscaRede e detalhePrestador cortam com [...]; quem tem
    a lista inteira é listaEspecialidadesPrestador, por endereço."""
    rid = _RID.get(chave(r))
    if rid and rid in _ESPF:
        alvo = (norm(r.get("endereco")), (r.get("numero") or "").strip())
        esp = [x["e"] for x in _ESPF[rid]
               if (norm(x.get("end")), (x.get("num") or "").strip()) == alvo]
        # alguns endereços da busca não constam na lista por endereço
        if not esp:
            esp = [x["e"] for x in _ESPF[rid]]
        if esp:
            return sorted(set(esp), key=esp.index)
    txt = (_ESPC.get(str(r["id"])) or "").strip()
    if not txt or "[...]" in txt:
        d = _DET.get(rid or "", {})
        txt = (d.get("especialidade") or "").strip()
    if not txt or "[...]" in txt:
        txt = (r.get("esp") or "").strip()
    return _parte(txt)


def carrega(cod):
    rows = json.load(open("dados/rede2_%s.json" % cod, encoding="utf-8"))
    out = []
    for r in rows:
        k = chave(r)
        d = _DET.get(_RID.get(k) or "", {})
        cat = LUGAR.get((d.get("tipo_estabelecimento") or "").strip(), PADRAO)
        esp = especialidades(r)
        out.append({
            "id": r["id"],
            "nome": (r.get("nome") or "").strip(),
            "chave": k,
            "cnpj": (d.get("cpf_cnpj") or "").strip(),
            "categoria": cat,
            "tipo": (d.get("tipo_estabelecimento") or r.get("_tipo") or "").strip(),
            "unidade": CIM_UNIDADE.get(r.get("_classe"), ""),
            "cidade": cidade_bonita(r.get("_cidade")),
            "bairro": (r.get("bairro") or "").strip(),
            "endereco": endereco(r),
            "cep": (r.get("cep") or "").strip(),
            "tel": tel(r.get("tel")),
            "tel2": tel(r.get("tel_sec")),
            "email": (d.get("email") or "").strip().lower(),
            "acess": (d.get("acessibilidade") or "") == "S",
            "esp": ", ".join(esp),
            # antes isto era um chute por palavra-chave no nome; agora a
            # própria operadora diz o que é estabelecimento e o que é pessoa
            "inst": cat not in PESSOAIS,
        })
    return out
