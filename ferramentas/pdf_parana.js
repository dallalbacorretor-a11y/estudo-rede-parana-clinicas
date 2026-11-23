  /* ============== PDF no padrao Central de Rede (pdf-rede.js) ==============
     O mesmo gerador dos sites da Amil, do Bradesco e da SulAmerica: a pagina
     DESCREVE o documento (capa, leitura, blocos, tabela) e o pdf-rede.js o
     monta com o pdfmake e as fontes livres do site (IBM Plex e Newsreader).
     O pdfmake quebra a linha: nome, bairro e especialidades saem inteiros.
     Totais com a regra da pagina: o numero principal e o da busca oficial e
     o direcionamento interno (D) vem a parte.
     (Trecho inserido no app por montar_site.py, no lugar do gerador antigo.) */

  /* "400 QP" - o nome curto cabe no cabecalho da coluna do plano. */
  function curtoProduto(p) {
    return ((p.rotulo || "").replace(/^Paraná\s+/, "") + " " +
            String(p.acomodacao || "").split(" ")[0]).trim();
  }

  function corDoProduto(p) {
    return p.cor || "#8e0e28";
  }

  function tituloCidade(t) {
    return String(t || "").replace(/(^|\s)(\S)(\S*)/g, function (m, a, b, c) {
      return a + b.toUpperCase() + c.toLowerCase();
    }).replace(/\bE\b/g, "e");
  }

  function telefonePdf(t) {
    return String(t || "").replace(/^(\d\d)-/, "($1) ");
  }

  function assinaturaDoc() {
    var c = corretor || {};
    var p = [c.corretora || "Mazza Broker"];
    ["nome", "fone", "email"].forEach(function (k) { if (c[k]) p.push(c[k]); });
    return "Documento gerado em " + new Date().toLocaleDateString("pt-BR") + "  ·  " +
           p.join("  ·  ");
  }

  function nomeArquivo(partes) {
    return partes.filter(Boolean).join(" - ").replace(/\s*\/\s*/g, "-")
                 .replace(/[\/\\:*?"<>|]+/g, "-").replace(/\s+/g, " ").trim() + ".pdf";
  }

  function juntar(nomes) {
    return nomes.length <= 1 ? (nomes[0] || "")
         : nomes.slice(0, -1).join(", ") + " e " + nomes[nomes.length - 1];
  }

  function cidadesDoPrestador(p) {
    return (p.cr && p.cr.length) ? p.cr : (p.cid || []);
  }

  /* A cidade com mais prestadores primeiro, depois as da regiao. */
  function porCidadeENome(lista) {
    var conta = {};
    lista.forEach(function (p) {
      var c = cidadesDoPrestador(p)[0] || "";
      conta[c] = (conta[c] || 0) + 1;
    });
    return lista.slice().sort(function (a, b) {
      var ca = cidadesDoPrestador(a)[0] || "", cb = cidadesDoPrestador(b)[0] || "";
      if (ca !== cb) return (conta[cb] - conta[ca]) || (ca < cb ? -1 : 1);
      return ordenarPorNome(a, b);
    });
  }

  /* Consultorio e medico do CIM: o cliente procura pela especialidade. */
  function porEspecialidadeENome(lista) {
    function chave(p) { return semAcento(especialidades(p.esp)[0] || "~"); }
    return lista.slice().sort(function (a, b) {
      var ea = chave(a), eb = chave(b);
      return ea !== eb ? (ea < eb ? -1 : 1) : ordenarPorNome(a, b);
    });
  }

  /* Marca do plano na linha: visto (busca oficial), visto com a palavra
     "direcionamento" (D da pagina) ou nada. */
  function marcaPdf(p, cod) {
    if (produtosDe(p).indexOf(cod) < 0) return false;
    return (p.dir || []).indexOf(cod) >= 0 ? "direcionamento" : true;
  }

  function linhaPdf(p, produtos) {
    var unidade = (p.cats || []).filter(function (c) { return /^CIM /.test(c); });
    return {
      nome: bonito(p.n),
      tag: unidade.join(" · "),
      esp: especialidades(p.esp).join(" · "),
      end: (p.e || []).map(bonito).join(" | "),
      tel: (p.t || []).map(telefonePdf).join("\n"),
      bairro: (p.b || []).map(bonito).join(" · "),
      cidade: bonito(cidadesDoPrestador(p).join(" / ")),
      marcas: produtos.map(function (pr) { return marcaPdf(p, pr.codigo); })
    };
  }

  function contaTexto(n, nDir) {
    return n.toLocaleString("pt-BR") + (n === 1 ? " prestador" : " prestadores") +
           (nDir ? "  ·  +" + nDir + " por direcionamento" : "");
  }

  /* `soDir(p)`: a linha so entra por direcionamento - conta a parte. */
  function blocoPdf(titulo, itens, produtos, soDir) {
    var nDir = itens.filter(soDir).length;
    return { tipo: "bloco", titulo: titulo, conta: contaTexto(itens.length - nDir, nDir),
             endereco: true, telefone: true,
             produtos: produtos.map(function (pr) {
               return { nome: curtoProduto(pr), cor: corDoProduto(pr) };
             }),
             linhas: itens.map(function (p) { return linhaPdf(p, produtos); }) };
  }

  var TITULO_PDF = { "Médicos dos CIM": "Médicos que atendem nos CIM" };

  function ordemDoBloco(cat, itens) {
    return (cat === "Consultórios" || cat === "Médicos dos CIM")
      ? porEspecialidadeENome(itens) : porCidadeENome(itens);
  }

  function leituraPdf(produtos) {
    var nomes = produtos.map(rotuloProduto);
    return { tipo: "leitura",
      cartoes: [
        { titulo: produtos.length > 1 ? "Os " + produtos.length + " planos" : "O plano",
          etiquetas: produtos.map(function (p) { return [rotuloProduto(p), corDoProduto(p)]; }),
          texto: [["O ", false], ["visto", true],
                  [" na coluna do plano quer dizer que o prestador atende quem tem esse " +
                   "plano. Visto com a palavra ", false], ["direcionamento", true],
                  [" quer dizer direcionamento interno: o hospital atende por " +
                   "encaminhamento da operadora, não por acesso livre, e fica fora do " +
                   "total do plano, contado à parte. Enfermaria e apartamento (QC e QP) " +
                   "usam a mesma rede.", false]] },
        { titulo: "Como a rede está organizada",
          texto: [["Cada bloco é uma categoria da operadora: ", false],
                  ["hospitais gerais e especializados", true], [", ", false],
                  ["unidades próprias CIM", true], [", exames, terapias, ", false],
                  ["clínicas e consultórios", true], [" e ", false],
                  ["médicos dos CIM", true],
                  [". A contagem é por endereço de atendimento: cada prestador conta uma " +
                   "vez em cada endereço. Sob o nome vêm as especialidades completas.", false]] },
        { titulo: "De onde vêm os dados",
          texto: [["Busca oficial de rede credenciada da Paraná Clínicas", true],
                  [", plano por plano e cidade por cidade, coleta de " + D.gerado_em +
                   ". O direcionamento interno é informação do corretor, não vem da " +
                   "busca oficial.", false]] }
      ],
      aviso: [["Antes de contratar. ", true],
              ["A rede credenciada é definida e alterada exclusivamente pela Paraná Clínicas, " +
               "a qualquer tempo. Este documento reproduz a busca oficial na data indicada " +
               "e serve para orientar a escolha — ", false],
              ["confirme no portal da Paraná Clínicas antes de contratar.", true]] };
  }

  /* Botao em "Montando..." enquanto o PDF sai; volta sozinho no fim. */
  function entregarPdf(botao, doc) {
    if (!window.PDFRede) {
      avisar("<b>O gerador de PDF não carregou nesta página.</b> Recarregue e tente de novo.", true);
      return;
    }
    var rotulo = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Montando…";
    function fim() { botao.disabled = false; botao.textContent = rotulo; }
    setTimeout(function () {
      var r;
      try { r = window.PDFRede.baixar(doc()); }
      catch (e) { fim(); avisar("<b>Não consegui montar o PDF:</b> " + esc(e.message || e), true); return; }
      Promise.resolve(r).then(fim, function (e) {
        fim();
        avisar("<b>Não consegui montar o PDF:</b> " + esc(e && e.message ? e.message : e), true);
      });
    }, 30);
  }

  function documentoRede(produtos) {
    var comparativo = produtos.length > 1;
    var lista = filtrar();
    var oficiais = lista.filter(function (p) { return !soPorDirecionamento(p); });
    var nDir = lista.length - oficiais.length;
    var onde = tituloCidade(apelidoCidade()) + " / " + (D.uf || "PR");
    var nomes = produtos.map(rotuloProduto);

    function daCat() {
      var quais = Array.prototype.slice.call(arguments);
      return oficiais.filter(function (p) { return quais.indexOf(tipoDe(p)) >= 0; }).length;
    }
    var cidades = {};
    oficiais.forEach(function (p) {
      cidadesDoPrestador(p).forEach(function (c) { cidades[c] = 1; });
    });
    // os mesmos quadros da Visao geral da pagina
    var placar = [[oficiais.length, "prestadores"]];
    if (nDir) placar.push(["+" + nDir, "por direcionamento"]);
    placar = placar.concat([
      [Object.keys(cidades).length, "cidades"],
      [daCat("Hospitais gerais"), "hospitais gerais"],
      [daCat("Hospitais especializados"), "hospitais especializados"],
      [daCat("Diagnóstico por imagem"), "centros de imagem"],
      [daCat("Laboratórios e análises clínicas", "Exames e procedimentos", "Oncologia"),
       "laboratórios e exames"],
      [daCat("Unidades próprias CIM", "Médicos dos CIM"), "atendimento nos CIM"],
      [daCat("Clínicas e policlínicas", "Consultórios", "Terapias"), "clínicas e consultórios"]
    ].filter(function (c) { return c[0]; }));
    if (comparativo) {
      produtos.forEach(function (pr, i) {
        var no = lista.filter(function (p) { return produtosDe(p).indexOf(pr.codigo) >= 0; });
        var d = no.filter(function (p) { return (p.dir || []).indexOf(pr.codigo) >= 0; }).length;
        placar.push([no.length - d, nomes[i] + (d ? " (+" + d + " D)" : "")]);
      });
    }

    var recorte = [(comparativo ? "planos " : "plano ") +
                   nomes.join(estado.modo === "e" ? " e " : " ou ")];
    if (temEscolha("cat")) recorte.push("categoria " + escolhidos("cat").join(", "));
    if (temEscolha("esp")) recorte.push("especialidade " +
      escolhidos("esp").map(especialidade).join(", "));
    if (temEscolha("bairro")) recorte.push("bairro " + escolhidos("bairro").map(bonito).join(", "));
    if ($("q").value.trim()) recorte.push("busca “" + $("q").value.trim() + "”");
    recorte.push("busca oficial da Paraná Clínicas de " + D.gerado_em);

    var secoes = [leituraPdf(produtos)];
    D.categorias.forEach(function (cat) {
      var itens = lista.filter(function (p) { return tipoDe(p) === cat; });
      if (!itens.length) return;
      secoes.push(blocoPdf(TITULO_PDF[cat] || cat, ordemDoBloco(cat, itens), produtos,
                           soPorDirecionamento));
    });

    return {
      arquivo: nomeArquivo(["Rede Parana Clinicas", juntar(nomes), onde]),
      rodape: "Rede credenciada Paraná Clínicas   ·   " +
              juntar(produtos.map(curtoProduto)) + "   ·   " + onde + "   ·   coleta " + D.gerado_em,
      corretora: (corretor || {}).corretora || "Mazza Broker",
      corretorNome: (corretor || {}).nome || "",
      capa: { titulo: "Rede credenciada", destaque: "Paraná Clínicas", onde: onde,
              recorte: recorte.join("  ·  "), placar: placar,
              cores: produtos.map(corDoProduto), assinatura: assinaturaDoc() },
      secoes: secoes
    };
  }

  function gerarPDF() {
    var produtos = produtosEscolhidos();
    if (!produtos.length) {
      avisar("<b>Marque pelo menos um produto.</b> O PDF sai com uma coluna " +
             "para cada plano marcado.");
      return;
    }
    if (produtos.length > MAX_COLUNAS_PDF) {
      avisar("<b>Escolha até " + MAX_COLUNAS_PDF + " planos para o PDF.</b> " +
             "Desmarque alguns e gere de novo.", true);
      return;
    }
    entregarPdf($("pdf"), function () { return documentoRede(produtos); });
  }

  /* ---------------- PDF da troca de plano (aba Entre planos) ---------------- */
  function documentoEntre(codA, codB) {
    var r = compararPlanos(codA, codB);
    var prodA = D.produtos.filter(function (p) { return p.codigo === codA; })[0];
    var prodB = D.produtos.filter(function (p) { return p.codigo === codB; })[0];
    var nA = nomeProduto(codA), nB = nomeProduto(codB);
    var praças = escolhidos("cid");
    var onde = (praças.length ? praças.map(bonito).join(", ") : (D.estado || D.uf)) +
               " / " + (D.uf || "PR");
    function oficial(p, cod) {
      return produtosDe(p).indexOf(cod) >= 0 && (p.dir || []).indexOf(cod) < 0;
    }
    function soDirEm(cod) {
      return function (p) { return (p.dir || []).indexOf(cod) >= 0; };
    }
    var base = baseEntre();
    var A = base.filter(function (p) { return oficial(p, codA); });
    var B = base.filter(function (p) { return oficial(p, codB); });
    var dA = r.noA.length - A.length, dB = r.noB.length - B.length;
    // deixam de ser rede direta: no plano novo, so por direcionamento
    var viramD = A.filter(function (p) { return (p.dir || []).indexOf(codB) >= 0; });
    var saemOf = r.perde.filter(function (p) { return oficial(p, codA); }).length;
    var pct = A.length ? Math.round(100 * (A.length - saemOf) / A.length) : 100;
    function contaCidades(lst) {
      var c = {};
      lst.forEach(function (p) { cidadesDoPrestador(p).forEach(function (x) { c[x] = 1; }); });
      return Object.keys(c).length;
    }
    function naCat(lst, cat) { return lst.filter(function (p) { return tipoDe(p) === cat; }); }
    var hospSaem = r.perde.filter(function (p) { return /^Hospitais/.test(tipoDe(p) || ""); });

    var linhas = [];
    D.categorias.forEach(function (cat) {
      var v = [naCat(A, cat).length, naCat(B, cat).length,
               naCat(r.perde, cat).length, naCat(r.ganha, cat).length];
      if (v.some(function (x) { return x; })) linhas.push({ celulas: [cat].concat(v) });
    });
    linhas.push({ total: true, celulas: ["Total (busca oficial)", A.length, B.length,
                                         r.perde.length, r.ganha.length] });
    linhas.push({ celulas: ["Por direcionamento (D), à parte", dA ? "+" + dA : "—",
                            dB ? "+" + dB : "—", "", ""] });
    linhas.push({ celulas: ["Cidades com rede", contaCidades(A), contaCidades(B), "", ""] });

    var secoes = [
      { tipo: "texto", titulo: "O que a troca significa", conta: onde, texto: [
        ["O ", false], [nA, true], [" atende " + A.length.toLocaleString("pt-BR") +
        " prestadores na busca oficial" + (dA ? " (+" + dA + " por direcionamento)" : "") +
        ". O ", false], [nB, true], [" atende " + B.length.toLocaleString("pt-BR") +
        (dB ? " (+" + dB + " por direcionamento)" : "") + ". Na troca, ", false],
        [r.perde.length.toLocaleString("pt-BR"), true], [" saem da rede do cliente e ", false],
        [r.ganha.length.toLocaleString("pt-BR"), true], [" entram.", false]]
          .concat(viramD.length ? [[" Outros ", false], [String(viramD.length), true],
            [" continuam acessíveis, mas só por direcionamento interno.", false]] : []) },
      { tipo: "tabela", titulo: "Resumo por categoria", conta: nA + " para " + nB,
        colunas: [{ nome: "Categoria" },
                  { nome: curtoProduto(prodA), cor: corDoProduto(prodA), largura: 74 },
                  { nome: curtoProduto(prodB), cor: corDoProduto(prodB), largura: 74 },
                  { nome: "Saem", largura: 74 }, { nome: "Entram", largura: 74 }],
        linhas: linhas,
        nota: [["Saem", true], [": estão no " + nA + " e não aparecem no " + nB +
                ", nem por direcionamento. ", false], ["Entram", true],
               [": o contrário. O direcionamento interno (D) fica fora dos totais.", false]] },
      leituraPdf([prodA, prodB])
    ];
    if (r.cidadesSomem.length) {
      secoes.push({ tipo: "texto", titulo: "Cidades que ficam sem rede",
                    conta: r.cidadesSomem.length,
                    texto: [[r.cidadesSomem.map(bonito).join("  ·  "), false]] });
    }
    D.categorias.forEach(function (cat) {
      var itens = naCat(r.perde, cat);
      if (itens.length) secoes.push(blocoPdf("Saem no " + nB + ": " + (TITULO_PDF[cat] || cat),
        ordemDoBloco(cat, itens), [prodA, prodB], soDirEm(codA)));
    });
    if (viramD.length) {
      secoes.push(blocoPdf("Passam a ser só por direcionamento no " + nB,
        porCidadeENome(viramD), [prodA, prodB], function () { return false; }));
    }
    D.categorias.forEach(function (cat) {
      var itens = naCat(r.ganha, cat);
      if (itens.length) secoes.push(blocoPdf("Entram no " + nB + ": " + (TITULO_PDF[cat] || cat),
        ordemDoBloco(cat, itens), [prodA, prodB], soDirEm(codB)));
    });

    return {
      arquivo: nomeArquivo(["Rede Parana Clinicas", "troca de " + nA + " para " + nB, onde]),
      rodape: "Paraná Clínicas   ·   " + curtoProduto(prodA) + " para " + curtoProduto(prodB) +
              "   ·   " + onde + "   ·   coleta " + D.gerado_em,
      corretora: (corretor || {}).corretora || "Mazza Broker",
      corretorNome: (corretor || {}).nome || "",
      capa: { titulo: "O que muda", destaque: prodA.rotulo + " para " + prodB.rotulo, onde: onde,
              recorte: "de " + nA + " para " + nB + "  ·  busca oficial da Paraná Clínicas de " +
                       D.gerado_em,
              placar: [[pct + "%", "da rede mantida"],
                       [r.perde.length, "prestadores saem"],
                       [hospSaem.length, "hospitais saem"],
                       [r.ganha.length, "prestadores entram"],
                       [r.cidadesSomem.length, "cidades sem rede"]]
                .concat(viramD.length ? [[viramD.length, "passam a direcionamento"]] : []),
              cores: [corDoProduto(prodA), corDoProduto(prodB)], assinatura: assinaturaDoc() },
      secoes: secoes
    };
  }

  function gerarPDFEntre() {
    var codA = $("planoA").value, codB = $("planoB").value;
    if (!codA || !codB || codA === codB) return;
    entregarPdf($("pdfEntre"), function () { return documentoEntre(codA, codB); });
  }

