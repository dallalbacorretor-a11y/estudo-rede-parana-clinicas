# -*- coding: utf-8 -*-
import os, sys, json, html, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import PLANOS, ORDEM_CAT, norm
from build_comp import concilia

BASE = _local.RAIZ
D2 = os.path.join(BASE, "02 - COMPARATIVOS DE REDE")
CURTOS = [p[2] for p in PLANOS]
CORES = {"400 QP": "#a80a32", "600 QC": "#1f6b4e", "CIM QC": "#2a2abf"}

def build():
    dados = concilia()
    dados.sort(key=lambda r: (ORDEM_CAT.index(r["categoria"]) if r["categoria"] in ORDEM_CAT else 99,
                              -len(r["planos"]), r["cidade"] != "Curitiba", r["cidade"], norm(r["nome"])))
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    linhas = []
    for r in dados:
        dirs = r.get("dir") or []
        tds = "".join(
            '<td class="chk" style="color:%s" %s>%s</td>'
            % (CORES[c],
               'title="Direcionamento interno: atende por encaminhamento da operadora"'
               if c in dirs else "",
               "D" if c in dirs else ("✔" if c in r["planos"] else "·"))
            for c in CURTOS)
        linhas.append(
            '<tr data-cat="%s" data-cid="%s" data-txt="%s">'
            '<td class="nm"><b>%s</b><span class="esp">%s</span></td>'
            '<td class="cid">%s<span class="esp">%s</span></td>'
            '<td class="end">%s<span class="esp">%s</span></td>'
            '<td class="tel">%s</td>%s</tr>' % (
                html.escape(r["categoria"]), html.escape(r["cidade"]),
                html.escape((r["nome"] + " " + r["esp"] + " " + r["bairro"] + " " + r["cidade"]).lower()),
                html.escape(r["nome"]), html.escape(r["esp"]),
                html.escape(r["cidade"]), html.escape(r["bairro"]),
                html.escape(r["endereco"]), html.escape(r["cep"]),
                html.escape(r["tel"] or ""), tds))
    ths = "".join('<th class="pl" style="background:%s">%s</th>' % (CORES[c], c) for c in CURTOS)
    cats = "".join('<option value="%s">%s</option>' % (c, c) for c in ORDEM_CAT)
    cids = "".join('<option value="%s">%s</option>' % (c, c) for c in sorted(set(r["cidade"] for r in dados)))
    tpl = open("template.html", encoding="utf-8").read()
    doc = (tpl.replace("{{LINHAS}}", "\n".join(linhas)).replace("{{THS}}", ths)
              .replace("{{CATS}}", cats).replace("{{CIDS}}", cids)
              .replace("{{DATA}}", hoje).replace("{{TOTAL}}", str(len(dados))))
    fn = os.path.join(D2, "COMPARATIVO REDE PARANA CLINICAS.html")
    open(fn, "w", encoding="utf-8").write(doc)
    print("ok", fn, len(dados))

if __name__ == "__main__":
    build()
