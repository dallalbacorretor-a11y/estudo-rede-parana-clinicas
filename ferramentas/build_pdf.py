# -*- coding: utf-8 -*-
import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import PLANOS, ORDEM_CAT, norm
from build_comp import concilia
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Table, TableStyle, NextPageTemplate, PageBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

BASE = _local.RAIZ
D2 = os.path.join(BASE, "02 - COMPARATIVOS DE REDE")
PW, PH = landscape(A4)
NAVY = colors.HexColor("#10233f"); GOLD = colors.HexColor("#c9a227")
INK = colors.HexColor("#1c2230"); MUT = colors.HexColor("#6b7686")
LINE = colors.HexColor("#dfe4ec")
CURTOS = [p[2] for p in PLANOS]
CORES = {"400 QP": colors.HexColor("#a80a32"), "600 QC": colors.HexColor("#1f6b4e"),
         "CIM QC": colors.HexColor("#2a2abf")}
HEXS = {"400 QP": "#a80a32", "600 QC": "#1f6b4e", "CIM QC": "#2a2abf"}
TINT = {"400 QP": colors.HexColor("#fbeef1"), "600 QC": colors.HexColor("#edf5f1"),
        "CIM QC": colors.HexColor("#eeeefb")}
HOJE = datetime.date.today().strftime("%d/%m/%Y")

def S(name, **k):
    return ParagraphStyle(name, **k)

st_nome = S("nome", fontName="Helvetica-Bold", fontSize=7.6, leading=9.2, textColor=INK)
st_cel = S("cel", fontName="Helvetica", fontSize=7.0, leading=8.6, textColor=INK)
st_h = S("h", fontName="Helvetica-Bold", fontSize=7.2, leading=8.6,
         textColor=colors.white, alignment=TA_CENTER)
st_chk = S("chk", fontName="Helvetica-Bold", fontSize=9, leading=10, alignment=TA_CENTER)


def esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Doc(BaseDocTemplate):
    def __init__(self, fn, subtitulo):
        BaseDocTemplate.__init__(self, fn, pagesize=(PW, PH), leftMargin=12 * mm,
                                 rightMargin=12 * mm, topMargin=14 * mm, bottomMargin=13 * mm,
                                 title="Comparativo de Rede - Parana Clinicas", author="Mazza Broker")
        self.subtitulo = subtitulo
        f = Frame(12 * mm, 13 * mm, PW - 24 * mm, PH - 27 * mm, id="n")
        self.addPageTemplates([
            PageTemplate(id="capa", frames=[Frame(0, 0, PW, PH, id="c")], onPage=self.capa),
            PageTemplate(id="normal", frames=[f], onPage=self.rodape)])

    def capa(self, c, d):
        c.saveState()
        c.setFillColor(NAVY); c.rect(0, 0, PW, PH, fill=1, stroke=0)
        x = 30 * mm
        c.setFillColor(colors.white); c.setFont("Times-Bold", 32)
        c.drawString(x, PH - 88 * mm, "Comparativo de Rede Credenciada")
        c.setFillColor(GOLD); c.setFont("Times-Italic", 23)
        c.drawString(x, PH - 101 * mm, "Paran\u00e1 Cl\u00ednicas \u00b7 Curitiba e Regi\u00e3o Metropolitana")
        w = 46 * mm
        for i, k in enumerate(CURTOS):
            c.setFillColor(CORES[k])
            c.rect(x + i * (w + 4 * mm), PH - 112 * mm, w, 3.2 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#c3ccda")); c.setFont("Helvetica", 11)
        c.drawString(x, PH - 126 * mm, self.subtitulo)
        c.drawString(x, PH - 133 * mm,
                     "Planos Paran\u00e1 400 AHO QP \u00b7 Paran\u00e1 600 AHO QC \u00b7 Paran\u00e1 CIM AHO QC (COPART SR)")
        c.drawString(x, PH - 140 * mm, "Consulta realizada em %s na busca oficial da operadora." % HOJE)
        c.setFillColor(GOLD); c.setFont("Times-Bold", 17)
        c.drawString(x, 30 * mm, "Mazza Broker")
        c.setFillColor(colors.HexColor("#8d97a6")); c.setFont("Helvetica", 8.6)
        c.drawString(x, 24 * mm, "Alan Vinicius Dall Alba \u00b7 (41) 99547-6715 \u00b7 alan.vinicius@mazzabroker.com.br")
        c.restoreState()

    def rodape(self, c, d):
        c.saveState()
        c.setStrokeColor(LINE); c.setLineWidth(.5)
        c.line(12 * mm, 10.5 * mm, PW - 12 * mm, 10.5 * mm)
        c.setFillColor(MUT); c.setFont("Helvetica", 7)
        c.drawString(12 * mm, 6.8 * mm,
                     "Mazza Broker \u00b7 Rede credenciada Paran\u00e1 Cl\u00ednicas \u2014 Curitiba & Regi\u00e3o")
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
        c.drawRightString(PW - 12 * mm, 6.8 * mm, str(c.getPageNumber() - 1))
        c.restoreState()


def pagina_como_ler():
    tit = S("ct", fontName="Times-Bold", fontSize=17, leading=20, textColor=NAVY)
    ch = S("ch", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=NAVY)
    cb = S("cb", fontName="Helvetica", fontSize=7.8, leading=10, textColor=INK)
    cards = [[Paragraph("\u2714 Atende", ch),
              Paragraph("A cor identifica o plano", ch),
              Paragraph("\u00b7 N\u00e3o consta", ch)],
             [Paragraph("O prestador consta na rede daquele plano, na cidade e endere\u00e7o indicados.", cb),
              Paragraph("<font color='#a80a32'>400 QP</font> \u00b7 <font color='#1f6b4e'>600 QC</font> "
                        "\u00b7 <font color='#2a2abf'>CIM QC</font> \u2014 cada coluna tem sua faixa de cor.", cb),
              Paragraph("O prestador n\u00e3o apareceu na busca oficial daquele plano na data da consulta.", cb)]]
    t = Table(cards, colWidths=[(PW - 24 * mm) / 3.0] * 3, rowHeights=[14, 32])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f5f9")),
                           ("BOX", (0, 0), (0, -1), .9, CORES["400 QP"]),
                           ("BOX", (1, 0), (1, -1), .9, CORES["600 QC"]),
                           ("BOX", (2, 0), (2, -1), .9, CORES["CIM QC"]),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 7)]))
    aviso = Table([[Paragraph(
        "<b>A rede credenciada \u00e9 definida e alterada exclusivamente pela operadora.</b> Este material tem "
        "car\u00e1ter informativo e reflete a consulta feita em %s na busca oficial da Paran\u00e1 Cl\u00ednicas. "
        "Confirme sempre no portal da operadora antes de contratar. Os prestadores est\u00e3o agrupados por "
        "categoria e, dentro de cada uma, pela abrang\u00eancia nos planos e pela cidade." % HOJE,
        S("av", fontName="Helvetica", fontSize=8, leading=11, textColor=colors.white))]],
        colWidths=[PW - 24 * mm])
    aviso.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                               ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                               ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    return [Paragraph("Como ler este comparativo", tit), Spacer(1, 10), t, Spacer(1, 16), aviso]


COLW = [74 * mm, 33 * mm, 73 * mm, 24 * mm] + [21 * mm] * 3


def tabela(linhas):
    head = [Paragraph("Prestador / especialidades", st_h), Paragraph("Cidade / bairro", st_h),
            Paragraph("Endere\u00e7o", st_h), Paragraph("Telefone", st_h)] + \
           [Paragraph(c, st_h) for c in CURTOS]
    data = [head]
    style = [("BACKGROUND", (0, 0), (3, 0), NAVY),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("LINEBELOW", (0, 1), (-1, -1), .4, LINE)]
    for i, k in enumerate(CURTOS):
        style.append(("BACKGROUND", (4 + i, 0), (4 + i, 0), CORES[k]))
        style.append(("BACKGROUND", (4 + i, 1), (4 + i, -1), TINT[k]))
    r = 1
    for kind, item in linhas:
        if kind == "cat":
            data.append([Paragraph(item.upper(), S("c%d" % r, fontName="Helvetica-Bold",
                                                   fontSize=7.6, leading=9.5, textColor=NAVY))] + [""] * 6)
            style += [("SPAN", (0, r), (-1, r)),
                      ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#e9edf4")),
                      ("TOPPADDING", (0, r), (-1, r), 6), ("BOTTOMPADDING", (0, r), (-1, r), 5)]
        else:
            d = item
            nome = Paragraph("%s<br/><font size=6.3 color='#6b7686'>%s</font>"
                             % (esc(d["nome"]), esc(d["esp"])), st_nome)
            cid = Paragraph("%s<br/><font size=6.3 color='#6b7686'>%s</font>"
                            % (esc(d["cidade"]), esc(d["bairro"])), st_cel)
            end = Paragraph("%s<br/><font size=6.3 color='#6b7686'>%s</font>"
                            % (esc(d["endereco"]), esc(d["cep"])), st_cel)
            row = [nome, cid, end, Paragraph(esc(d["tel"]), st_cel)]
            for k in CURTOS:
                if k in d["planos"]:
                    row.append(Paragraph("<font color='%s'>\u2714</font>" % HEXS[k], st_chk))
                else:
                    row.append(Paragraph("<font color='#aab3c0'>\u00b7</font>", st_chk))
            data.append(row)
        r += 1
    t = Table(data, colWidths=COLW, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


def gera(fn, dados, subtitulo):
    linhas = []
    for cat in ORDEM_CAT:
        sub = [d for d in dados if d["categoria"] == cat]
        if not sub:
            continue
        sub.sort(key=lambda r: (-len(r["planos"]), r["cidade"] != "Curitiba", r["cidade"], norm(r["nome"])))
        linhas.append(("cat", cat))
        linhas += [("row", d) for d in sub]
    doc = Doc(fn, subtitulo)
    story = [NextPageTemplate("normal"), PageBreak()] + pagina_como_ler() + [PageBreak(), tabela(linhas)]
    doc.build(story)
    print("ok", fn, len(dados))


if __name__ == "__main__":
    d = concilia()
    princ = [x for x in d if x.get("inst")]
    gera(os.path.join(D2, "COMPARATIVO REDE PARANA CLINICAS - CLIENTES (Principais).pdf"),
         princ, "Hospitais, unidades pr\u00f3prias CIM, cl\u00ednicas e laborat\u00f3rios")
    gera(os.path.join(D2, "COMPARATIVO REDE PARANA CLINICAS - Apresentacao.pdf"),
         d, "Rede completa \u2014 hospitais, CIM, cl\u00ednicas, consult\u00f3rios e laborat\u00f3rios")
