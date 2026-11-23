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
from common import DATA_COLETA as HOJE   # data da coleta da rede
import datetime
VERSAO = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

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
# Carimbo da versão publicada. O GitHub Pages serve a página com dez minutos de
# cache, e uma aba já aberta fica na versão antiga até recarregar - sem isto,
# nao da para saber se o que esta na tela e a ultima publicacao.
head = troca(head, '<span class="assina" id="assinaRodape"></span>',
             '<span class="assina" id="assinaRodape"></span>\n'
             '  <span class="versao" title="Se esta data estiver atrasada, '
             'recarregue a página segurando Shift">versão ' + VERSAO + '</span>')
# a contagem de medicos do corpo clinico abre a lista no title
head = troca(head, "</style>",
             ".equipe{cursor:help;border-bottom:1px dotted currentColor}\n"
             ".rodape .versao{display:block;margin-top:4px;font-size:10.5px;"
             "opacity:.55;font-variant-numeric:tabular-nums}\n</style>")
head = troca(head, "A comparação usa a praça filtrada na aba Rede completa.",
             "A comparação usa a cidade filtrada na aba Rede completa.")

# ================================================================ 2) o app
# ------------------------------------------- PDF: padrao Central de Rede
# O gerador que veio no app antigo da Amil (Relatorio + PDFWeb, com Segoe UI e
# Constantia embutidas) cortava nome, bairro e especialidades com "..." e saia
# em cinza claro. No lugar dele entra o pdf-rede.js (pdfmake + IBM Plex e
# Newsreader, fontes livres) - o mesmo dos sites da Amil, do Bradesco e da
# SulAmerica -, com o documento da Parana Clinicas descrito em pdf_parana.js.
# Os tres arquivos (pdf-rede.js, pdfmake.min.js, fontes-pdf.js) ficam na raiz,
# copiados sem alteracao do rede-amil; o pdf-rede.js carrega os outros dois
# so no primeiro PDF.
def recorta(txt, de, ate, novo=""):
    """Troca o trecho [de, ate) - os dois marcadores precisam existir uma vez."""
    global trocas
    if txt.count(de) != 1 or txt.count(ate) != 1 or txt.find(ate) < txt.find(de):
        raise SystemExit("RECORTE: marcadores nao encontrados uma vez:\n  %r\n  %r"
                         % (de[:80], ate[:80]))
    trocas += 1
    i, j = txt.find(de), txt.find(ate)
    return txt[:i] + novo + txt[j:]


app = recorta(app, "  function gerarPDF() {\n", "  function apelidoCidade() {\n")
app = recorta(app, "  function montarEEntregar(produtos) {\n", "  /* Zera todo filtro escolhido.")
app = recorta(app, "  function gerarPDFEntre() {\n", "  function montarSelects() {\n",
              L("pdf_parana.js"))
# Entre planos: cada linha e um endereco (mesma base das planilhas), entao a
# troca compara endereco a endereco - por CNPJ, as unidades de Sao Jose dos
# Pinhais da Oftalmo Curitiba sumiam da lista do que sai no 600.
app = troca(app,
            '    noB.forEach(function (p) { emB[p.c || p.n] = 1; });\n'
            '    var perde = noA.filter(function (p) { return !emB[p.c || p.n]; });\n'
            '    var emA = {};\n'
            '    noA.forEach(function (p) { emA[p.c || p.n] = 1; });\n'
            '    var ganha = noB.filter(function (p) { return !emA[p.c || p.n]; });\n',
            '    function chave(p) { return (p.c || p.n) + "|" + (p.e || []).join(" / "); }\n'
            '    noB.forEach(function (p) { emB[chave(p)] = 1; });\n'
            '    var perde = noA.filter(function (p) { return !emB[chave(p)]; });\n'
            '    var emA = {};\n'
            '    noA.forEach(function (p) { emA[chave(p)] = 1; });\n'
            '    var ganha = noB.filter(function (p) { return !emA[chave(p)]; });\n')

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
# Todas as paginas do GitHub Pages do Alan dividem a mesma origem
# (dallalbacorretor-a11y.github.io): uma chave generica no localStorage seria a
# mesma do site da Amil e dos outros estudos. Prefixo proprio deste estudo.
app = troca(app, 'var CHAVE_CORRETOR = "mazza.corretor.v1";',
            'var CHAVE_CORRETOR = "mzb_paranaclin_corretor";')
app = troca(app, '"Rede que a Amil devolve para "',
            '"Rede da Paraná Clínicas em "')
app = troca(app,
            '". Parte dos prestadores fica em municípios vizinhos — use a aba " +\n'
            '        "Rede completa para ver cidade por cidade."',
            '". Use a aba Rede completa para ver prestador por prestador."')

# ajustes de texto: aqui nao existe "praca" - a busca da operadora e por cidade
app = app.replace('". Escolha uma praça no filtro da aba Rede completa " +',
                  '". Use os filtros da aba Rede completa " +')
app = app.replace('" inteira. Escolha uma praça " +\n'
                  '            "no filtro da aba Rede completa para recortar este panorama."',
                  '". Filtre por cidade ou plano na aba " +\n'
                  '            "Rede completa para recortar este panorama."')
app = app.replace('"Rede de " + (D.estado || D.uf) + " inteira.',
                  '"Rede dos três planos em " + (D.estado || D.uf) + ".')

# ------------------------------------------------- categorias da operadora
# O app da Amil traz tres categorias no codigo ("Hospitais", "Laboratorios e
# imagem", "Clinicas e consultorios") e deduz a do prestador contando
# especialidades. Aqui quem classifica e o build_dados, a partir do campo
# tipo_estabelecimento da operadora - que separa hospital geral de
# especializado e tira os centros de imagem de dentro de "Clinica". Entao o
# app passa a confiar no `cat` que vem no dado, e as listas de categoria
# passam a sair de D.
app = troca(app, 'var CAT_EXAME = { "Laboratorios e imagem": 1 };',
            'var CAT_EXAME = {};   // preenchido por mapearEspecialidadesDeExame')
app = troca(app,
            '  function mapearEspecialidadesDeExame() {\n'
            '    ESP_EXAME = {};\n'
            '    D.prestadores.forEach(function (p) {\n'
            '      var lista = p.pc && p.pc["Laboratorios e imagem"];\n'
            '      (lista || []).forEach(function (e) { ESP_EXAME[e] = 1; });\n'
            '    });\n'
            '  }',
            '  function mapearEspecialidadesDeExame() {\n'
            '    ESP_EXAME = {};\n'
            '    CAT_EXAME = {};\n'
            '    (D.catsExame || []).forEach(function (c) { CAT_EXAME[c] = 1; });\n'
            '    TIPO_LUGAR = {};\n'
            '    (D.categorias || []).forEach(function (c) { TIPO_LUGAR[c] = 1; });\n'
            '    CAT_ELETIVA = {};\n'
            '    (D.categorias || []).forEach(function (c) {\n'
            '      if (!/^Hospitais/.test(c)) CAT_ELETIVA[c] = 1;\n'
            '    });\n'
            '    D.prestadores.forEach(function (p) {\n'
            '      Object.keys(CAT_EXAME).forEach(function (c) {\n'
            '        ((p.pc && p.pc[c]) || []).forEach(function (e) { ESP_EXAME[e] = 1; });\n'
            '      });\n'
            '    });\n'
            '  }')
app = troca(app,
            '  var TIPO_LUGAR = { "Hospitais": 1, "Laboratorios e imagem": 1,\n'
            '                     "Clinicas e consultorios": 1 };',
            '  var TIPO_LUGAR = {};   // idem')
app = troca(app,
            '  var CAT_ELETIVA = { "Laboratorios e imagem": 1,\n'
            '                      "Clinicas e consultorios": 1 };',
            '  var CAT_ELETIVA = {};  // idem')
app = troca(app,
            '  function tipoDe(p) {\n'
            '    var c = p.cats || [];\n'
            '    // pronto-socorro entra aqui junto com hospital: o Hospital de Caridade de\n'
            '    // Palmeira a Amil classifica so como PS, e ele nao e lugar de exame eletivo\n'
            '    if (c.indexOf("Hospitais") >= 0 || c.indexOf("Pronto-socorro 24h") >= 0) {\n'
            '      return "Hospitais";\n'
            '    }\n'
            '    var exames = quantos(p, "Laboratorios e imagem");\n'
            '    var consultas = quantos(p, "Clinicas e consultorios");\n'
            '    if (exames > consultas) return "Laboratorios e imagem";\n'
            '    if (consultas > 0) return "Clinicas e consultorios";\n'
            '    if (exames > 0) return "Laboratorios e imagem";\n'
            '    return null;\n'
            '  }',
            '  function tipoDe(p) {\n'
            '    return p.cat || null;   // quem classifica e o build_dados\n'
            '  }')
# hospital geral e especializado: os dois valem a ressalva de "so internado"
app = app.replace(
    '    var c = p.cats || [];\n'
    '    return c.indexOf("Hospitais") >= 0 || c.indexOf("Pronto-socorro 24h") >= 0;',
    '    return /^Hospitais/.test(tipoDe(p) || "");')

# Quadros do panorama: passam a contar pelas categorias novas. "Onde se
# interna" e a pergunta que o cliente faz, entao hospital geral ganha quadro
# proprio; os CIM tambem, porque sao o diferencial da operadora.
app = troca(app,
            '    var hospitais = lista.filter(function (p) {\n'
            '      return tipoDe(p) === "Hospitais";\n'
            '    }).length;\n'
            '    var exames = lista.filter(function (p) {\n'
            '      return tipoDe(p) === "Laboratorios e imagem";\n'
            '    }).length;\n'
            '    var consultorios = lista.filter(function (p) {\n'
            '      return tipoDe(p) === "Clinicas e consultorios";\n'
            '    }).length;',
            '    function daCat() {\n'
            '      var quais = Array.prototype.slice.call(arguments);\n'
            '      return lista.filter(function (p) {\n'
            '        return quais.indexOf(tipoDe(p)) >= 0;\n'
            '      }).length;\n'
            '    }\n'
            '    var hospitais = daCat("Hospitais gerais");\n'
            '    var hospEsp = daCat("Hospitais especializados");\n'
            '    var imagem = daCat("Diagnóstico por imagem");\n'
            '    var exames = daCat("Laboratórios e análises clínicas",\n'
            '                       "Exames e procedimentos", "Oncologia");\n'
            '    var cim = daCat("Unidades próprias CIM", "Médicos dos CIM");\n'
            '    var consultorios = daCat("Clínicas e policlínicas", "Consultórios",\n'
            '                             "Terapias");')
app = troca(app,
            '    $("panNumeros").innerHTML = [\n'
            '      [lista.length, "prestadores"],\n'
            '      [cidades.length, cidades.length === 1 ? "cidade" : "cidades"],\n'
            '      [hospitais, "hospitais"],\n'
            '      [exames, "exames e laboratórios"],\n'
            '      [consultorios, "clínicas e consultórios"]\n'
            '    ].map(function (n) {',
            '    $("panNumeros").innerHTML = [\n'
            '      [lista.length, "prestadores"],\n'
            '      [cidades.length, cidades.length === 1 ? "cidade" : "cidades"],\n'
            '      [hospitais, "hospitais gerais"],\n'
            '      [hospEsp, "hospitais especializados"],\n'
            '      [imagem, "centros de imagem"],\n'
            '      [exames, "laboratórios e exames"],\n'
            '      [cim, "atendimento nos CIM"],\n'
            '      [consultorios, "clínicas e consultórios"]\n'
            '    ].filter(function (n) { return n[0]; }).map(function (n) {')

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
# ------------------------------------- dados que a operadora publica e o app
# da Amil nao tinha onde mostrar: e-mail, acessibilidade e corpo clinico.
# Buscar pelo nome do medico e o caso real do corretor - "meu cliente quer o
# Dr. Fulano, onde ele atende?".
app = troca(app,
            '      if (q && semAcento(p.n).indexOf(q) < 0 && (p.c || "").indexOf(q) < 0) {\n'
            '        return false;\n'
            '      }',
            '      if (q && semAcento(p.n).indexOf(q) < 0 && (p.c || "").indexOf(q) < 0 &&\n'
            '          !(p.eq || []).some(function (m) {\n'
            '            return semAcento(m[0]).indexOf(q) >= 0;\n'
            '          })) {\n'
            '        return false;\n'
            '      }', 2)   # a aba Rede completa e a aba Entre planos
app = troca(app,
            '           \'<div class="miudo">\' + esc(p.t.join(" · ")) + "</div></td>";',
            '           \'<div class="miudo">\' + esc(p.t.join(" · ")) +\n'
            '           (p.mail && p.mail.length\n'
            '             ? " · " + esc(p.mail[0]) : "") +\n'
            '           (p.acess ? \' · <span title="Prestador com acessibilidade \'\n'
            '                      + \'declarada à operadora">acessível</span>\' : "") +\n'
            '           (p.eq && p.eq.length\n'
            '             ? \'<span class="equipe" title="\' +\n'
            '               esc(p.eq.slice(0, 14).map(function (m) {\n'
            '                 return m[0] + (m[2] ? " — " + m[2] : "");\n'
            '               }).join("\\n")) + (p.eq.length > 14 ? "\\n…" : "") +\n'
            '               \'"> · equipe de \' + p.eq.length + \' médicos</span>\'\n'
            '             : "") + "</div></td>";')

# ---------------------------------------------------- direcionamento interno
# Alguns hospitais nao constam na busca daquele plano mas sao liberados por
# encaminhamento. Marcar com D, e nao com o visto, e o que evita prometer
# acesso direto (ver dados/direcionamento.json).
app = troca(app, '             (tem ? "&#10003;" : "") + "</td>";',
            '             (tem\n'
            '               ? ((p.dir || []).indexOf(c.codigo) >= 0\n'
            '                   ? \'<abbr class="dir" title="Atende por direcionamento \'\n'
            '                     + \'interno da operadora: o acesso depende de \'\n'
            '                     + \'encaminhamento, não é livre.">D</abbr>\'\n'
            '                   : "&#10003;")\n'
            '               : "") + "</td>";')
head = troca(head, ".equipe{cursor:help;border-bottom:1px dotted currentColor}",
             ".equipe{cursor:help;border-bottom:1px dotted currentColor}\n"
             ".prod .dir{font:700 11px/1 inherit;text-decoration:none;cursor:help;"
             "border:1px solid currentColor;border-radius:3px;padding:0 3px}")
head = troca(head,
             'por isso Paraná 400 AHO QC e Paraná 600 AHO QP não aparecem à parte, '
             'estão dentro do 400 e do 600.</p>',
             'por isso Paraná 400 AHO QC e Paraná 600 AHO QP não aparecem à parte, '
             'estão dentro do 400 e do 600. <b>D</b> na coluna do plano significa '
             '<b>direcionamento interno</b>: o hospital atende, mas por '
             'encaminhamento da operadora, não por acesso livre. Contagem por '
             'endereço de atendimento: cada prestador conta uma vez em cada '
             'endereço; os <b>D</b> aparecem na lista, mas ficam fora do total '
             'do plano e são contados à parte.</p>')

# ------------------------------------- total do plano = busca oficial; D a parte
# O numero principal (cartao, grafico, tabela, PDF) e o da busca oficial - o
# mesmo das planilhas, do comparativo e dos PDFs. O D e informacao do corretor
# (dados/direcionamento.json): continua na lista, contado a parte.
app = troca(app,
            '  function selecionados() {\n'
            '    return D.produtos\n'
            '      .filter(function (p) { return estado.produtos[p.codigo]; })\n'
            '      .map(function (p) { return p.codigo; });\n'
            '  }\n',
            '  function selecionados() {\n'
            '    return D.produtos\n'
            '      .filter(function (p) { return estado.produtos[p.codigo]; })\n'
            '      .map(function (p) { return p.codigo; });\n'
            '  }\n'
            '\n'
            '  /* Linha que so entra no filtro de plano por direcionamento interno\n'
            '     (D): aparece na tabela, mas fica fora do total do plano. */\n'
            '  function soPorDirecionamento(p) {\n'
            '    var sel = selecionados();\n'
            '    if (!sel.length || !(p.dir || []).length) return false;\n'
            '    var oficial = produtosDe(p).filter(function (c) {\n'
            '      return p.dir.indexOf(c) < 0;\n'
            '    });\n'
            '    var tem = sel.filter(function (c) { return oficial.indexOf(c) >= 0; });\n'
            '    return estado.modo === "e" ? tem.length !== sel.length : !tem.length;\n'
            '  }\n')
app = troca(app,
            '      var quem = base.filter(function (p) {\n'
            '        return produtosDe(p).indexOf(pr.codigo) >= 0;\n'
            '      });\n'
            '      var cid = {}, hosp = 0;\n',
            '      var quem = base.filter(function (p) {\n'
            '        return produtosDe(p).indexOf(pr.codigo) >= 0;\n'
            '      });\n'
            '      var nDir = quem.filter(function (p) {\n'
            '        return (p.dir || []).indexOf(pr.codigo) >= 0;\n'
            '      }).length;\n'
            '      quem = quem.filter(function (p) {\n'
            '        return (p.dir || []).indexOf(pr.codigo) < 0;\n'
            '      });\n'
            '      var cid = {}, hosp = 0;\n')
app = troca(app,
            '      dados[pr.codigo] = { n: quem.length, hosp: hosp,\n',
            '      dados[pr.codigo] = { n: quem.length, hosp: hosp, dir: nDir,\n')
app = troca(app,
            '                      " · " + d.cid + (d.cid === 1 ? " cidade" : " cidades");\n',
            '                      " · " + d.cid + (d.cid === 1 ? " cidade" : " cidades") +\n'
            '                      (d.dir ? " · +" + d.dir + " por direcionamento" : "");\n')
app = troca(app,
            '    var cidades = {}, porCat = {};\n'
            '    r.forEach(function (p) {\n'
            '      (p.cr && p.cr.length ? p.cr : p.cid).forEach(function (c) {\n'
            '        cidades[c] = 1;\n'
            '      });\n'
            '      porCat[tipoDe(p) || p.cat] = (porCat[tipoDe(p) || p.cat] || 0) + 1;\n'
            '    });\n',
            '    var cidades = {}, porCat = {}, nDir = 0;\n'
            '    r.forEach(function (p) {\n'
            '      if (soPorDirecionamento(p)) { nDir++; return; }\n'
            '      (p.cr && p.cr.length ? p.cr : p.cid).forEach(function (c) {\n'
            '        cidades[c] = 1;\n'
            '      });\n'
            '      porCat[tipoDe(p) || p.cat] = (porCat[tipoDe(p) || p.cat] || 0) + 1;\n'
            '    });\n')
app = troca(app,
            '''    var m = '<div class="metrica"><b>' + r.length + "</b><span>prestadores</span></div>" +\n''',
            '''    var m = '<div class="metrica"><b>' + (r.length - nDir) + "</b><span>prestadores</span></div>" +\n'''
            '''            (nDir ? '<div class="metrica"><b>+' + nDir +\n'''
            '''                    "</b><span>por direcionamento</span></div>" : "") +\n''')

# Por ultimo, o que sobrou de "=== Hospitais" espalhado pelas contagens
# (cartao do plano, bolha do mapa, "hospitais que saem" da aba Entre planos).
# Depois dos blocos acima, senao esta troca os desfiguraria antes da hora.
for _de, _para in (('tipoDe(p) === "Hospitais"', '/^Hospitais/.test(tipoDe(p) || "")'),
                   ('tipoDe(p) !== "Hospitais"', '!/^Hospitais/.test(tipoDe(p) || "")')):
    if _de not in app:
        raise SystemExit("nao achei mais: " + _de)
    trocas += app.count(_de)
    app = app.replace(_de, _para)

# =================================== 3) do amil_lib.js, so o cabecalho
# O amil_lib.js traz, alem de tres linhas de configuracao, as fontes Microsoft
# embutidas (Constantia e Segoe UI) e o motor de PDF antigo (PDFWeb +
# Relatorio). O PDF agora e o pdf-rede.js: da lib so ficam as linhas de
# configuracao (ORDEM_UF, DADOS e CORRETOR) - a pagina fica mais leve e sem
# fonte de licenca restrita.
cab = [l for l in lib.split("\n")
       if l.startswith(("window.ORDEM_UF=", "window.DADOS=", "window.CORRETOR="))]
if len(cab) != 3:
    raise SystemExit("amil_lib.js: esperava ORDEM_UF, DADOS e CORRETOR; achei %d" % len(cab))
lib = "\n".join(cab) + "\n"
lib = troca(lib, 'window.ORDEM_UF=["PR", "SC", "SP"];', 'window.ORDEM_UF=["PR"];')

if "Amil" in app or "Amil" in lib:
    import re
    sobrou = set(re.findall(r".{40}Amil.{40}", app))
    print("AVISO: ainda ha mencoes a Amil no app (provavelmente comentarios):", len(sobrou))

# ============================================================== 4) monta
blob = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
# pdf-rede.js antes dos dados: ele acha pdfmake.min.js e fontes-pdf.js pelo
# proprio endereco (document.currentScript), entao precisa ser <script src>.
pagina = (head + '\n<script src="pdf-rede.js"></script>'
          + "\n<script>window.DADOS_UF=" + blob + ";\n"
          + lib + "</script>\n<script>" + app + "</script>\n")
io.open(SAI, "w", encoding="utf-8").write(pagina)
print("trocas conferidas:", trocas)
print("gravado:", SAI, round(len(pagina.encode("utf-8")) / 1024 / 1024, 2), "MB")
