# -*- coding: utf-8 -*-
"""Os dois PDFs do comparativo.

Fala a mesma língua visual do PDF que a página gera: capa vermelha da Paraná
Clínicas, selo dourado da Mazza, faixas de categoria e a mesma cor por plano.
"""
import os, sys, re, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)
from common import PLANOS, ORDEM_CAT, CATS_EXAME, norm
from build_comp import concilia
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, NextPageTemplate, PageBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

BASE = _local.RAIZ
D2 = os.path.join(BASE, "02 - COMPARATIVOS DE REDE")
PW, PH = landscape(A4)

# ------------------------------------------------------------------- cores
MARCA = colors.HexColor("#8e0e28")      # vermelho Paraná Clínicas
MARCA2 = colors.HexColor("#a81b39")     # faixa de categoria
OURO = colors.HexColor("#9a7513")       # acento Mazza Broker
OURO_CLARO = colors.HexColor("#edc97e")
TINTA = colors.HexColor("#1b2331")
CINZA = colors.HexColor("#66707f")
CINZA_CLARO = colors.HexColor("#98a1b0")
RISCO = colors.HexColor("#eee2e5")
ZEBRA = colors.HexColor("#fdf7f8")
BRANCO = colors.white

CURTOS = [p[2] for p in PLANOS]
# as mesmas dos cartões da página — validadas para daltonismo e contraste
HEX = {"400 QP": "#a80a32", "600 QC": "#6b3f8f", "CIM QC": "#b5761b"}
CORES = {k: colors.HexColor(v) for k, v in HEX.items()}
TINT = {"400 QP": colors.HexColor("#fdf2f5"), "600 QC": colors.HexColor("#f5f1fa"),
        "CIM QC": colors.HexColor("#fdf6ec")}
# Na capa o fundo é o vermelho da marca: o #a80a32 do plano 400 sumiria dentro
# dele. Estes são os mesmos matizes, clareados até separarem sobre o vermelho
# (conferido no validador; o nome do plano vem escrito junto, então a cor não
# carrega sozinha a identidade).
CAPA = {"400 QP": colors.HexColor("#e06a80"), "600 QC": colors.HexColor("#a98ad6"),
        "CIM QC": colors.HexColor("#d9a84e")}
HOJE = datetime.date.today().strftime("%d/%m/%Y")

# ---------------------------------------------------------------- tipografia
def S(name, **k):
    return ParagraphStyle(name, **k)


st_nome = S("nome", fontName="Helvetica-Bold", fontSize=8, leading=9.6, textColor=TINTA)
st_cel = S("cel", fontName="Helvetica", fontSize=7.2, leading=9, textColor=TINTA)
st_h = S("h", fontName="Helvetica-Bold", fontSize=7.4, leading=9,
         textColor=BRANCO, alignment=TA_CENTER)
st_hL = S("hL", fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=BRANCO)
st_chk = S("chk", fontName="Helvetica-Bold", fontSize=10, leading=11, alignment=TA_CENTER)
st_hR = S("hR", fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=BRANCO,
          alignment=TA_RIGHT)

MIUDAS = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "as", "os", "no",
          "na", "para", "com", "por"}


SIGLAS = {"CIM", "IPO", "SUS", "UTI", "CL", "CDI", "CEDAV", "PR", "SC", "UPA",
          "HC", "AMB", "PS", "SA", "S/A", "LTDA", "ME", "TEA", "ONG"}


def bonito(t):
    """A operadora mistura CAIXA ALTA e Title Case no mesmo campo.

    Num nome todo em maiúscula, QUALQUER palavra curta parece sigla — era assim
    que saía "Hospital DO Centro" e "Hospital SAO Lucas". Então a regra de sigla
    só vale quando o nome original tem caixa mista; se veio todo em maiúscula,
    só a lista conhecida escapa.
    """
    t = (t or "").strip()
    if not t:
        return ""
    letras = [c for c in t if c.isalpha()]
    tudo_maiusculo = bool(letras) and all(c.isupper() for c in letras)
    saida = []
    for i, p in enumerate(re.split(r"(\s+|[-/])", t)):
        if not p.strip() or p in ("-", "/"):
            saida.append(p)
            continue
        b, alto = p.lower(), p.upper()
        if alto in SIGLAS:
            saida.append(alto)
        elif not tudo_maiusculo and len(p) <= 4 and p.isupper() and p.isalpha():
            saida.append(p)
        elif b in MIUDAS and i > 0:
            saida.append(b)
        else:
            saida.append(b[:1].upper() + b[1:])
    return "".join(saida)


def esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ páginas
class Doc(BaseDocTemplate):
    def __init__(self, fn, subtitulo, resumo):
        BaseDocTemplate.__init__(self, fn, pagesize=(PW, PH), leftMargin=12 * mm,
                                 rightMargin=12 * mm, topMargin=13 * mm,
                                 bottomMargin=13 * mm,
                                 title="Comparativo de Rede - Parana Clinicas",
                                 author="Mazza Broker")
        self.subtitulo, self.resumo = subtitulo, resumo
        f = Frame(12 * mm, 13 * mm, PW - 24 * mm, PH - 26 * mm, id="n")
        self.addPageTemplates([
            PageTemplate(id="capa", frames=[Frame(0, 0, PW, PH, id="c")], onPage=self.capa),
            PageTemplate(id="normal", frames=[f], onPage=self.rodape)])

    # -- capa: o vazio de antes virou o resumo da rede, que é o que interessa
    def capa(self, c, d):
        c.saveState()
        c.setFillColor(MARCA); c.rect(0, 0, PW, PH, fill=1, stroke=0)
        c.setFillColor(OURO); c.rect(0, PH - 2.2 * mm, PW, 2.2 * mm, fill=1, stroke=0)
        # título em cima, cartões embaixo: o branco fica ENTRE os dois blocos,
        # de propósito, em vez de sobrar no pé da página
        x, topo = 28 * mm, PH - 46 * mm

        c.setFillColor(OURO); c.rect(x, topo + 1.5, 2.6, 9, fill=1, stroke=0)
        c.setFillColor(OURO_CLARO); c.setFont("Helvetica-Bold", 8.5)
        c.drawString(x + 9, topo + 3, "CURITIBA E REGIÃO METROPOLITANA")

        c.setFillColor(BRANCO); c.setFont("Times-Bold", 40)
        c.drawString(x, topo - 22 * mm, "Rede Credenciada")
        c.setFillColor(OURO_CLARO); c.setFont("Times-Italic", 31)
        c.drawString(x, topo - 34 * mm, "Paraná Clínicas")
        c.setStrokeColor(OURO); c.setLineWidth(1.1)
        c.line(x, topo - 40 * mm, x + 62 * mm, topo - 40 * mm)

        c.setFillColor(colors.HexColor("#f0cdd5")); c.setFont("Helvetica", 10.5)
        c.drawString(x, topo - 48 * mm, self.subtitulo)

        # os três planos, com o tamanho da rede de cada um
        yc = 50 * mm
        larg, gap = 52 * mm, 6 * mm
        for i, k in enumerate(CURTOS):
            bx = x + i * (larg + gap)
            c.setFillColor(colors.HexColor("#ffffff")); c.setFillAlpha(0.08)
            c.rect(bx, yc, larg, 21 * mm, fill=1, stroke=0)
            c.setFillAlpha(1)
            c.setFillColor(CAPA[k]); c.rect(bx, yc + 19 * mm, larg, 2 * mm, fill=1, stroke=0)
            c.setFillColor(BRANCO); c.setFont("Helvetica-Bold", 10)
            c.drawString(bx + 7, yc + 12.5 * mm, "Paraná " + k.split()[0])
            c.setFillColor(colors.HexColor("#f0cdd5")); c.setFont("Helvetica", 7.6)
            c.drawString(bx + 7, yc + 8.5 * mm,
                         "QP · apartamento" if k.endswith("QP") else "QC · enfermaria")
            c.setFillColor(BRANCO); c.setFont("Times-Bold", 17)
            c.drawRightString(bx + larg - 7, yc + 8 * mm, str(self.resumo["planos"][k]))
            c.setFillColor(colors.HexColor("#e3adb9")); c.setFont("Helvetica", 6.2)
            c.drawRightString(bx + larg - 7, yc + 4.6 * mm, "PRESTADORES")

        c.setFillColor(colors.HexColor("#e3adb9")); c.setFont("Helvetica", 9)
        c.drawString(x, topo - 60 * mm,
                     "Levantado na busca oficial de rede credenciada da Paraná Clínicas "
                     "em " + HOJE + ".")

        # assinatura
        c.setFillColor(OURO); c.rect(x, 22 * mm, 34 * mm, 11 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#2b0710")); c.setFont("Times-Bold", 13)
        c.drawString(x + 5.5, 27.2 * mm, "Mazza")
        c.setFont("Helvetica-Bold", 5.6)
        c.drawString(x + 5.5, 24 * mm, "B R O K E R")
        c.setFillColor(colors.HexColor("#f0cdd5")); c.setFont("Helvetica", 9)
        c.drawString(x + 40 * mm, 28.5 * mm, "Alan Vinicius Dall Alba")
        c.setFillColor(colors.HexColor("#d4939f"))
        c.drawString(x + 40 * mm, 24.2 * mm,
                     "(41) 99547-6715   ·   alan.vinicius@mazzabroker.com.br")

        # rodapé da capa: as três cores, na largura da página
        for i, k in enumerate(CURTOS):
            c.setFillColor(CAPA[k])
            c.rect(i * PW / 3.0, 0, PW / 3.0 + 1, 4 * mm, fill=1, stroke=0)
        c.restoreState()

    def rodape(self, c, d):
        c.saveState()
        c.setFillColor(MARCA); c.rect(0, PH - 3 * mm, PW, 3 * mm, fill=1, stroke=0)
        c.setStrokeColor(RISCO); c.setLineWidth(.5)
        c.line(12 * mm, 10.5 * mm, PW - 12 * mm, 10.5 * mm)
        c.setFillColor(OURO); c.rect(12 * mm, 6.2 * mm, 2, 7, fill=1, stroke=0)
        c.setFillColor(CINZA); c.setFont("Helvetica", 7)
        c.drawString(12 * mm + 7, 6.9 * mm,
                     "Mazza Broker  ·  Rede credenciada Paraná Clínicas — Curitiba & Região"
                     "  ·  " + HOJE)
        c.setFillColor(MARCA); c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(PW - 12 * mm, 6.9 * mm, str(c.getPageNumber() - 1))
        c.restoreState()


# --------------------------------------------------- página 2: números + legenda
def numero(v, rot):
    return ('<font name="Times-Bold" size="22" color="#8e0e28">%s</font><br/>'
            '<font name="Helvetica" size="6.4" color="#66707f">%s</font>'
            % (v, esc(rot.upper())))


def bloco_cidades(resumo):
    """Onde a rede está, em barras. É o que preenche a metade de baixo da página
    — antes ficava em branco."""
    tit = S("t3", fontName="Times-Bold", fontSize=13, leading=16, textColor=MARCA)
    rot = S("r", fontName="Helvetica", fontSize=7.4, leading=9, textColor=TINTA)
    val = S("v", fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=CINZA)
    dados = resumo["cidades"][:12]
    maior = max([n for _, n in dados] or [1])
    larg_barra = 46 * mm
    linhas, estilo = [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                          ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                          ("LEFTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 8)]
    meio = (len(dados) + 1) // 2
    for i in range(meio):
        linha, r = [], i
        for col in (dados[i:i + 1], dados[meio + i:meio + i + 1]):
            if not col:
                linha += ["", "", ""]
                continue
            cid, n = col[0]
            barra = Table([[""]], colWidths=[max(2.2 * mm, larg_barra * n / maior)],
                          rowHeights=[5])
            barra.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MARCA2),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                       ("TOPPADDING", (0, 0), (-1, -1), 0),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            linha += [Paragraph(esc(bonito(cid)), rot), barra,
                      Paragraph(str(n), val)]
        linhas.append(linha)
    larg_rot = 46 * mm
    t = Table(linhas, colWidths=[larg_rot, larg_barra + 6 * mm, 12 * mm] * 2,
              hAlign="LEFT")
    t.setStyle(TableStyle(estilo))
    return [Paragraph("Onde a rede está", tit),
            Paragraph("Prestadores por cidade, somando os três planos.",
                      S("t4", fontName="Helvetica", fontSize=8, leading=11,
                        textColor=CINZA)),
            Spacer(1, 9), t]


def pagina_abertura(resumo):
    tit = S("t1", fontName="Times-Bold", fontSize=18, leading=21, textColor=MARCA)
    sub = S("t2", fontName="Helvetica", fontSize=8.6, leading=11.5, textColor=CINZA)
    cel = S("num", fontName="Helvetica", fontSize=8, leading=13, textColor=TINTA)

    # 2 linhas de 4: em uma linha só, os rótulos longos quebravam e a fila de
    # números saía desalinhada
    quadros = [q for q in resumo["quadros"] if q[0]]
    while len(quadros) % 4:
        quadros.append(("", ""))
    grade = [[Paragraph(numero(v, r) if r else "", cel) for v, r in quadros[i:i + 4]]
             for i in range(0, len(quadros), 4)]
    t = Table(grade, colWidths=[(PW - 24 * mm) / 4.0] * 4,
              rowHeights=[16 * mm] * len(grade))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBEFORE", (1, 0), (-1, -1), .6, RISCO),
        ("LINEBELOW", (0, 0), (-1, -2), .6, RISCO),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    ch = S("ch", fontName="Helvetica-Bold", fontSize=8.6, leading=11, textColor=MARCA)
    cb = S("cb", fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=TINTA)
    cards = [[Paragraph("✓  Atende", ch),
              Paragraph("Cada plano tem sua cor", ch),
              Paragraph("–  Não consta", ch)],
             [Paragraph("O prestador consta na rede daquele plano, no endereço indicado. "
                        "A coluna do plano fica marcada.", cb),
              Paragraph(" · ".join('<font color="%s"><b>%s</b></font>' % (HEX[k], k)
                                   for k in CURTOS) +
                        " — a mesma cor dos cartões na página de consulta.", cb),
              Paragraph("O prestador não apareceu na busca oficial daquele plano "
                        "na data desta consulta.<br/><b>D</b> no lugar do visto: "
                        "atende por <b>direcionamento interno</b> — o acesso "
                        "depende de encaminhamento da operadora.", cb)]]
    tc = Table(cards, colWidths=[(PW - 24 * mm - 2 * 6 * mm) / 3.0] * 3,
               rowHeights=[13, 30], colWidths2=None) if False else \
        Table(cards, colWidths=[(PW - 24 * mm - 12 * mm) / 3.0] * 3, rowHeights=[13, 42])
    tc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf7f8")),
        ("LINEABOVE", (0, 0), (0, 0), 2, CORES["400 QP"]),
        ("LINEABOVE", (1, 0), (1, 0), 2, CORES["600 QC"]),
        ("LINEABOVE", (2, 0), (2, 0), 2, CORES["CIM QC"]),
        ("BOX", (0, 0), (-1, -1), 0, BRANCO),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    aviso = Table([[Paragraph(
        '<b>A rede credenciada é definida e alterada exclusivamente pela operadora.</b>  '
        'Este material é informativo e retrata a consulta feita em %s. Confirme no portal '
        'da Paraná Clínicas antes de contratar. Os prestadores estão agrupados pela '
        'categoria que a operadora publica e, dentro de cada uma, pela abrangência nos '
        'planos e pela cidade.' % HOJE,
        S("av", fontName="Helvetica", fontSize=8, leading=11.5, textColor=BRANCO))]],
        colWidths=[PW - 24 * mm])
    aviso.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MARCA),
                               ("LEFTPADDING", (0, 0), (-1, -1), 12),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                               ("TOPPADDING", (0, 0), (-1, -1), 10),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))

    return [Paragraph("A rede em números", tit),
            Paragraph("Tudo que os três planos somados alcançam em Curitiba e Região. "
                      "Nas páginas seguintes, prestador por prestador.", sub),
            Spacer(1, 12), t, Spacer(1, 22),
            Paragraph("Como ler este comparativo", tit), Spacer(1, 10), tc,
            Spacer(1, 16), aviso, Spacer(1, 20)] + bloco_cidades(resumo)


# ------------------------------------------------------------------- tabela
COLW = [82 * mm, 29 * mm, 58 * mm, 36 * mm] + [21 * mm] * 3
MAX_ESP = 8          # sem teto, um hospital estica a linha para 4x a altura


def celula_nome(d):
    esp = [e.strip() for e in (d["esp"] or "").split(",") if e.strip()]
    extra = len(esp) - MAX_ESP
    txt = ", ".join(bonito(e) for e in esp[:MAX_ESP])
    if extra > 0:
        txt += " <font color='#98a1b0'>+%d</font>" % extra
    marca = (' <font size="5.4" color="#98a1b0">· acessível</font>'
             if d.get("acess") else "")
    return Paragraph("%s%s<br/><font size=6.3 color='#66707f'>%s</font>"
                     % (esc(bonito(d["nome"])), marca, esc(txt) if not extra else txt),
                     st_nome)


def celula_contato(d):
    linhas = [esc(d["tel"] or "")]
    if d.get("tel2") and d["tel2"] != d["tel"]:
        linhas.append("<font size=6.3 color='#66707f'>%s</font>" % esc(d["tel2"]))
    if d.get("email"):
        linhas.append("<font size=5.8 color='#98a1b0'>%s</font>" % esc(d["email"]))
    return Paragraph("<br/>".join(linhas), st_cel)


def tabela(linhas):
    head = [Paragraph("Prestador / especialidades", st_hL),
            Paragraph("Cidade / bairro", st_hL),
            Paragraph("Endereço", st_hL),
            Paragraph("Contato", st_hL)] + [Paragraph(c, st_h) for c in CURTOS]
    data = [head]
    style = [("BACKGROUND", (0, 0), (3, 0), MARCA),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("LINEBELOW", (0, 1), (-1, -1), .4, RISCO)]
    for i, k in enumerate(CURTOS):
        style.append(("BACKGROUND", (4 + i, 0), (4 + i, 0), CORES[k]))
        style.append(("BACKGROUND", (4 + i, 1), (4 + i, -1), TINT[k]))
    r = 1
    zebra = 0
    for kind, item in linhas:
        if kind == "cat":
            cat, n = item
            data.append([Paragraph(esc(cat.upper()), st_hL), "", "", "",
                         Paragraph("%d" % n, st_hR), "", ""])
            style += [("SPAN", (0, r), (3, r)), ("SPAN", (4, r), (-1, r)),
                      ("BACKGROUND", (0, r), (-1, r), MARCA2),
                      ("TOPPADDING", (0, r), (-1, r), 5),
                      ("BOTTOMPADDING", (0, r), (-1, r), 5)]
            zebra = 0
        else:
            d = item
            cid = Paragraph("%s<br/><font size=6.3 color='#66707f'>%s</font>"
                            % (esc(bonito(d["cidade"])), esc(bonito(d["bairro"]))), st_cel)
            end = Paragraph("%s<br/><font size=6.3 color='#66707f'>%s</font>"
                            % (esc(bonito(d["endereco"])), esc(d["cep"])), st_cel)
            row = [celula_nome(d), cid, end, celula_contato(d)]
            dirs = d.get("dir") or []
            for k in CURTOS:
                if k in dirs:
                    # direcionamento interno: D no lugar do visto
                    marca = "<font size=8 color='%s'><b>D</b></font>" % HEX[k]
                elif k in d["planos"]:
                    marca = "<font color='%s'>✓</font>" % HEX[k]
                else:
                    marca = "<font color='#c9ccd2'>–</font>"
                row.append(Paragraph(marca, st_chk))
            data.append(row)
            if zebra % 2:
                style.append(("BACKGROUND", (0, r), (3, r), ZEBRA))
            zebra += 1
        r += 1
    t = Table(data, colWidths=COLW, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


# -------------------------------------------------------------------- monta
def monta_resumo(dados):
    def n(*cats):
        return len([d for d in dados if d["categoria"] in cats])
    quadros = [
        (len(dados), "prestadores"),
        (len(set(d["cidade"] for d in dados)), "cidades"),
        (n("Hospitais gerais"), "hospitais gerais"),
        (n("Hospitais especializados"), "especializados"),
        (n("Diagnóstico por imagem"), "centros de imagem"),
        (n(*CATS_EXAME) - n("Diagnóstico por imagem"), "laboratórios"),
        (n("Unidades próprias CIM", "Médicos dos CIM"), "nos CIM"),
        (n("Clínicas e policlínicas", "Consultórios", "Terapias"),
         "clínicas e consultórios"),
    ]
    from collections import Counter
    cid = Counter(d["cidade"] for d in dados)
    return {"quadros": quadros,
            "cidades": cid.most_common(),
            "planos": {k: len([d for d in dados if k in d["planos"]]) for k in CURTOS}}


def gera(fn, dados, subtitulo):
    linhas = []
    for cat in ORDEM_CAT:
        sub = [d for d in dados if d["categoria"] == cat]
        if not sub:
            continue
        sub.sort(key=lambda r: (-len(r["planos"]), r["cidade"] != "Curitiba",
                                r["cidade"], norm(r["nome"])))
        linhas.append(("cat", (cat, len(sub))))
        linhas += [("row", d) for d in sub]
    doc = Doc(fn, subtitulo, monta_resumo(dados))
    doc.build([NextPageTemplate("normal"), PageBreak()]
              + pagina_abertura(monta_resumo(dados))
              + [PageBreak(), tabela(linhas)])
    print("ok", fn, len(dados), "prestadores")


if __name__ == "__main__":
    d = concilia()
    princ = [x for x in d if x.get("inst")]
    gera(os.path.join(D2, "COMPARATIVO REDE PARANA CLINICAS - CLIENTES (Principais).pdf"),
         princ, "Hospitais, centros de diagnóstico, laboratórios, clínicas e "
                "unidades próprias CIM")
    gera(os.path.join(D2, "COMPARATIVO REDE PARANA CLINICAS - Apresentacao.pdf"),
         d, "Rede completa — inclui os consultórios e os médicos que atendem nos CIM")
