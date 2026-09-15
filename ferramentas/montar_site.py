# -*- coding: utf-8 -*-
"""Monta a pagina da rede Parana Clinicas reaproveitando o app do site da Amil.

Toda troca passa por troca(), que estoura se o texto original nao existir mais -
assim uma mudanca no arquivo de origem falha alto em vez de sair silenciosa.
"""
import json, io, os, sys
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local  # noqa: F401  (fixa o diretorio de trabalho)

SAI = os.path.join(_local.RAIZ, "index.html")
HOJE = "12/09/2026"

L = lambda f: io.open(f, encoding="utf-8").read()
head = L(os.path.join(_local.BASE, "amil_head.html"))     # CSS + markup (ate antes dos <script>)
lib = L(os.path.join(_local.BASE, "amil_lib.js"))         # fontes + gerador de PDF
app = L(os.path.join(_local.BASE, "amil_app.js"))         # aplicacao
dados = json.load(open("dados/dados_pc.json", encoding="utf-8"))

trocas = 0
def troca(txt, de, para, n=1):
    global trocas
    if txt.count(de) != n:
        raise SystemExit("ESPERAVA %d ocorrencia(s) de:\n  %r\nachei %d"
                         % (n, de[:120], txt.count(de)))
    trocas += n
    return txt.replace(de, para)


# ====================================================== 1) paleta e cabecalho
# Vermelho e branco da Parana Clinicas (SulAmerica) no lugar do navy.
# O ouro continua: e o acento da Mazza Broker, igual no material da Amil.
CORES_CLARO = {
    "--marca-fundo:#0d2a4f": "--marca-fundo:#8e0e28",
    "--banda:#25507f": "--banda:#b03050",
    "--marca-texto:#0d2a4f": "--marca-texto:#8e0e28",
    "--amil:#2733c4": "--plano-a:#a80a32",
    "--adesao:#7c2f6d": "--plano-b:#6b3f8f",
    "--amils:#0b6154": "--plano-c:#b5761b",
    "--papel:#f2f5f9": "--papel:#f7f4f4",
    "--risco:#dbe2ec": "--risco:#e9dfe1",
    "--realce:#f6f8fc": "--realce:#fbf6f7",
}
CORES_ESCURO = {
    "--marca-fundo:#0b1a2f": "--marca-fundo:#3b0a16",
    "--banda:#1c3a5e": "--banda:#6d1330",
    "--marca-texto:#9dbfec": "--marca-texto:#eaa8b6",
    "--sobre-marca:#dbe7f7": "--sobre-marca:#f7e6ea",
    "--amil:#8d99ff": "--plano-a:#d1445f",
    "--adesao:#e08fd0": "--plano-b:#9b6ec4",
    "--amils:#48c7b4": "--plano-c:#b08529",
    "--papel:#0a0f17": "--papel:#130d0f",
    "--carta:#131a25": "--carta:#1b1416",
    "--risco:#25303f": "--risco:#3a2a2e",
    "--realce:#19212e": "--realce:#241a1d",
    "--tinta:#e7ecf4": "--tinta:#f2e9eb",
    "--tinta-fraca:#94a0b4": "--tinta-fraca:#b7a3a8",
}
# o bloco escuro aparece duas vezes (media query + [data-theme=dark])
for de, para in CORES_CLARO.items():
    head = head.replace(de, para)
for de, para in CORES_ESCURO.items():
    head = head.replace(de, para)
# o que sobrou referenciando os nomes antigos
for a, b in (("var(--amil)", "var(--plano-a)"), ("var(--adesao)", "var(--plano-b)"),
             ("var(--amils)", "var(--plano-c)")):
    head = head.replace(a, b)
    app = app.replace(a, b)

# o navy do gradiente do topo e do botao de estado
head = head.replace("rgba(214,177,85,.16)", "rgba(233,197,106,.20)")
head = head.replace("#16233a", "#3b0a16")

head = troca(head, "<title>Rede Amil Paraná, Santa Catarina e São Paulo</title>",
             "<title>Rede credenciada Paraná Clínicas — Curitiba e Região</title>")
head = troca(head,
             '<h1>Rede credenciada <em>Amil</em> — <span id="tituloEstado">Paraná, '
             'Santa Catarina e São Paulo</span></h1>',
             '<h1>Rede credenciada <em>Paraná Clínicas</em> — '
             '<span id="tituloEstado">Curitiba e Região</span></h1>')

# "Rede de (praça)" nao existe aqui: a busca da Parana Clinicas e por cidade.
head = troca(head, '<span class="rotulo">Rede de (praça)</span>',
             '<span class="rotulo">Cidade</span>')
# some com o filtro duplicado de cidade (o elemento fica no DOM: o app o le)
head = troca(head, '<div class="campo"><span class="rotulo">Cidade do prestador</span>',
             '<div class="campo" style="display:none"><span class="rotulo">Cidade do prestador</span>')

head = troca(head,
             '<span class="miudo" style="margin-left:auto">A busca por cidade traz a rede\n'
             '      da região — parte dos prestadores fica em municípios vizinhos.</span>',
             '<span class="miudo" style="margin-left:auto">Rede levantada cidade a cidade '
             'na busca oficial da operadora.</span>')

head = troca(head,
             '<p class="nota-familia">Cada cartão é uma <b>rede</b>, não um contrato:\n'
             '     enfermaria e apartamento (QC e QP) compartilham a mesma rede, e a linha\n'
             '     de <b>Adesão</b> usa a rede do PME/PJ correspondente — Adesão Prata está\n'
             '     dentro de Prata, Adesão Ouro dentro de Ouro, e assim por diante.</p>',
             '<p class="nota-familia">Cada cartão é uma <b>rede</b>, não um contrato: '
             'enfermaria e apartamento (<b>QC</b> e <b>QP</b>) compartilham a mesma rede — '
             'por isso Paraná 400 AHO QC e Paraná 600 AHO QP não aparecem à parte, '
             'estão dentro do 400 e do 600.</p>')

head = head.replace("portal da Amil", "portal da Paraná Clínicas")
head = troca(head, "A comparação usa a praça filtrada na aba Rede completa.",
             "A comparação usa a cidade filtrada na aba Rede completa.")

# ================================================================ 2) o app
app = troca(app,
            'var COR = { "PME/PJ": "var(--plano-a)", "Adesao": "var(--plano-b)", '
            '"Amil S": "var(--plano-c)" };',
            'var COR = { "Paraná Clínicas": "var(--marca-texto)" };')
app = troca(app,
            'var COR_GRAFICO = { "PME/PJ": "#4457e0", "Adesao": "#b03a97",\n'
            '                      "Amil S": "#0f9a80", "Black": "#5b6472" };',
            'var COR_GRAFICO = { "Paraná Clínicas": "#a80a32" };')

# mapa: a rede e so a regiao de Curitiba - o retangulo do Parana inteiro
# jogaria tudo num canto da tela.
lats = [p["xy"][0] for p in dados["PR"]["prestadores"] if p["xy"][0] is not None]
lngs = [p["xy"][1] for p in dados["PR"]["prestadores"] if p["xy"][1] is not None]
m = 0.06
app = troca(app, "PR: { lat: [-26.72, -22.51], lng: [-54.62, -48.02] },",
            "PR: { lat: [%.3f, %.3f], lng: [%.3f, %.3f] }," %
            (min(lats) - m, max(lats) + m, min(lngs) - m, max(lngs) + m))

app = troca(app, '"rede-amil-pr-"', '"rede-parana-clinicas-"')
app = troca(app, '"Rede que a Amil devolve para "',
            '"Rede da Paraná Clínicas em "')
app = troca(app,
            '". Parte dos prestadores fica em municípios vizinhos — use a aba " +\n'
            '        "Rede completa para ver cidade por cidade."',
            '". Use a aba Rede completa para ver prestador por prestador."')
app = app.replace("Levantado na busca avançada oficial da Amil.",
                  "Levantado na busca oficial de rede credenciada da Paraná Clínicas.")
app = troca(app,
            '"Amil devolveu na data da capa, para os planos "',
            '"a Paraná Clínicas devolveu na data da capa, para os planos "')
app = app.replace("Confirme no portal da Amil", "Confirme no portal da Paraná Clínicas")
app = troca(app, '("Amil " + nA + " x " + nB + " - " + onde + ".pdf")',
            '("Parana Clinicas " + nA + " x " + nB + " - " + onde + ".pdf")')
app = troca(app, 'var nome = "Rede Amil " +', 'var nome = "Rede Parana Clinicas " +')
app = troca(app,
            'var aviso = "Cada plano deste material representa uma rede: enfermaria e " +\n'
            '      "apartamento compartilham a mesma rede credenciada, e a linha de Adesão " +\n'
            '      "usa a rede do PME/PJ correspondente. " +',
            'var aviso = "Cada plano deste material representa uma rede: enfermaria (QC) " +\n'
            '      "e apartamento (QP) compartilham a mesma rede credenciada. " +')
app = troca(app, '"da Amil apresentava na data da capa e não substitui a consulta ao "',
            '"da Paraná Clínicas apresentava na data da capa e não substitui a consulta ao "')
app = troca(app, '"operadora. Este documento é o retrato do que a busca avançada oficial "',
            '"operadora. Este documento é o retrato do que a busca oficial de rede "')

# ajustes de texto: aqui nao existe "praca" - a busca da operadora e por cidade
app = app.replace('". Escolha uma praça no filtro da aba Rede completa " +',
                  '". Use os filtros da aba Rede completa " +')
app = app.replace('" inteira. Escolha uma praça " +\n'
                  '            "no filtro da aba Rede completa para recortar este panorama."',
                  '". Filtre por cidade ou plano na aba " +\n'
                  '            "Rede completa para recortar este panorama."')
app = app.replace('"Rede de " + (D.estado || D.uf) + " inteira.',
                  '"Rede dos três planos em " + (D.estado || D.uf) + ".')

# Os quadros do PDF eram os da Amil: "Pronto-socorro 24h" e "Centros de
# diagnostico por imagem" nao existem na classificacao da Parana Clinicas e
# saiam zerados. Entram os numeros que a operadora publica de fato - com as
# unidades proprias CIM - e quadro zerado nao aparece.
app = troca(app,
            '    var hosp = daCategoria("Hospitais");\n'
            '    var ps = daCategoria("Pronto-socorro 24h");',
            '    var hosp = daCategoria("Hospitais");\n'
            '    var cim = daCategoria("Unidades próprias (CIM)");\n'
            '    var ps = daCategoria("Pronto-socorro 24h");')
app = troca(app,
            '    rel.numeros([\n'
            '      [hosp.length, "Hospitais para internação"],\n'
            '      [ps.length, "Pronto-socorro 24 horas"],\n'
            '      [nAnalises, "Laboratórios de análises clínicas"],\n'
            '      [nImagem, "Centros de diagnóstico por imagem"],\n'
            '      [cons.length, "Clínicas e consultórios"],\n'
            '      [lista.length, "Prestadores no total"]\n'
            '    ]);',
            '    rel.numeros([\n'
            '      [hosp.length, "Hospitais"],\n'
            '      [cim.length, "Unidades próprias CIM"],\n'
            '      [lab.length, "Laboratórios e imagem"],\n'
            '      [cons.length, "Clínicas e consultórios"],\n'
            '      [lista.length, "Prestadores no total"]\n'
            '    ].filter(function (n) { return n[0]; }));')

# Aqui os tres planos sao de uma linha so, entao colorir pela linha pintaria
# tudo de vermelho. Cada plano ganha sua cor - a mesma no cartao, na coluna da
# tabela e na barra do grafico. Como token CSS, e nao hex, para o modo escuro
# usar a versao clara validada; o hex fica so para o PDF.
app = troca(app, 'var COR = { "Paraná Clínicas": "var(--marca-texto)" };',
            'var COR = { "Paraná Clínicas": "var(--marca-texto)" };\n'
            '  var VAR_PLANO = { p400: "var(--plano-a)", p600: "var(--plano-b)",\n'
            '                    cim: "var(--plano-c)" };')
app = troca(app, 'b.style.setProperty("--cor", p.cor || COR[p.linha] || "var(--plano-a)");',
            'b.style.setProperty("--cor", VAR_PLANO[p.codigo] || p.cor ||\n'
            '                                COR[p.linha] || "var(--plano-a)");')
app = troca(app, '\'" style="--cor:\' + (COR[c.linha] || "var(--plano-a)") + \'">\' +',
            '\'" style="--cor:\' + (VAR_PLANO[c.codigo] || COR[c.linha] ||\n'
            '                                        "var(--plano-a)") + \'">\' +')
app = troca(app, 'var cor = COR_GRAFICO[d.linha] || "var(--marca-texto)";',
            'var cor = VAR_PLANO[d.cod] || COR_GRAFICO[d.linha] || "var(--marca-texto)";')
app = troca(app, "return { rot: rotuloProduto(pr), linha: pr.linha,",
            "return { rot: rotuloProduto(pr), linha: pr.linha, cod: pr.codigo,")
app = troca(app, "return { rot: d.rot, linha: d.linha, v: d.n };",
            "return { rot: d.rot, linha: d.linha, cod: d.cod, v: d.n };")
app = troca(app, "return { rot: d.rot, linha: d.linha, v: d.cid };",
            "return { rot: d.rot, linha: d.linha, cod: d.cod, v: d.cid };")
# capa do PDF na cor do plano (o PDF nao tem modo escuro: hex mesmo)
app = troca(app, 'cor: aux.COR_LINHA[produto.linha] || "#20456f",',
            'cor: produto.cor || aux.COR_LINHA[produto.linha] || "#8e0e28",')
app = troca(app, 'cor: aux.COR_LINHA[prodA ? prodA.linha : "PME/PJ"] || "#20456f",',
            'cor: (prodA && prodA.cor) || "#8e0e28",')

# =============================================================== 3) o PDF
lib = troca(lib, 'window.ORDEM_UF=["PR", "SC", "SP"];', 'window.ORDEM_UF=["PR"];')
lib = troca(lib, 'var NAVY = "#0d2a4f", NAVY_MEIO = "#20456f", OURO = "#9a7513",',
            'var NAVY = "#8e0e28", NAVY_MEIO = "#a81b39", OURO = "#9a7513",')
lib = troca(lib, 'var COR_LINHA = { "PME/PJ": "#2733c4", "Adesao": "#7c2f6d",\n'
                 '                    "Amil S": "#0b6154", "Black": "#3a3a3a" };',
            'var COR_LINHA = { "Paraná Clínicas": "#8e0e28" };')
lib = troca(lib, '"Rede Credenciada Amil"', '"Rede Credenciada Paraná Clínicas"')
lib = troca(lib, '"Levantado na busca avançada oficial da Amil em "',
            '"Levantado na busca oficial de rede credenciada da Paraná Clínicas em "')
lib = troca(lib, '"Rede credenciada Amil " +', '"Rede credenciada Paraná Clínicas " +')
lib = troca(lib, 'var RISCO = "#e4e9f0", ZEBRA = "#f7f9fc",',
            'var RISCO = "#eee2e5", ZEBRA = "#fdf8f9",', 0) if False else lib
lib = lib.replace('RISCO = "#e4e9f0", ZEBRA = "#f7f9fc"',
                  'RISCO = "#eee2e5", ZEBRA = "#fdf9fa"')
lib = lib.replace('"#cfe0f5"', '"#f2d6dd"').replace('"#9fb8d8"', '"#e0a9b6"')
lib = lib.replace('"#c7d8ee"', '"#f4dde3"')
lib = lib.replace('OURO_CLARO = "#e3c46a"', 'OURO_CLARO = "#edc97e"')

if "Amil" in app or "Amil" in lib.split("window.FONTES")[0]:
    import re
    sobrou = set(re.findall(r".{40}Amil.{40}", app))
    print("AVISO: ainda ha mencoes a Amil no app (provavelmente comentarios):", len(sobrou))

# ============================================================== 4) monta
blob = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
pagina = (head + "\n<script>window.DADOS_UF=" + blob + ";\n"
          + lib.split(";\n", 1)[1] + "</script>\n<script>" + app + "</script>\n")
io.open(SAI, "w", encoding="utf-8").write(pagina)
print("trocas conferidas:", trocas)
print("gravado:", SAI, round(len(pagina.encode("utf-8")) / 1024 / 1024, 2), "MB")
