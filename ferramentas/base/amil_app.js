
(function () {
  "use strict";
  var D = window.DADOS;
  var $ = function (id) { return document.getElementById(id); };
  var semAcento = function (s) {
    return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
  };
  var COR = { "PME/PJ": "var(--amil)", "Adesao": "var(--adesao)", "Amil S": "var(--amils)" };
  /* Cada campo guarda um CONJUNTO de escolhas. Dentro do campo vale "ou"
     (cardiologia OU dermatologia); entre campos vale "e" (cardiologia E no
     Batel). Vazio quer dizer "tudo". */
  /* Quantas linhas a tabela desenha de uma vez. Sem esse teto, um filtro
     amplo monta 27 mil células e a página congela por segundos - o CSV e o
     PDF continuam usando a lista COMPLETA, o teto é só do que aparece. */
  var POR_VEZ = 200;
  var estado = { produtos: {}, modo: "ou", perto: null, teto: POR_VEZ,
                 f: { cid: {}, cidr: {}, cat: {}, esp: {}, bairro: {} },
                 aberto: null };

  /* Duas perguntas diferentes sobre cidade:
       cid  = "Rede de"            -> praça cuja rede a Amil devolveu
       cidr = "Cidade do prestador" -> onde o prestador fica de fato
     A busca da Amil por São José dos Pinhais traz 234 prestadores, dos quais
     só 77 ficam lá; os outros 157 são de Curitiba. */
  var CAMPOS = ["cid", "cidr", "cat", "esp", "bairro"];
  var ROTULO = { cid: "Rede de", cidr: "Cidade do prestador",
                 cat: "Categoria", esp: "Especialidade", bairro: "Bairro" };
  var TUDO = { cid: "Todas", cidr: "Todas", cat: "Todas", esp: "Todas",
               bairro: "Todos" };

  function escolhidos(campo) { return Object.keys(estado.f[campo]); }
  function temEscolha(campo) { return escolhidos(campo).length > 0; }

  /* Onde o prestador fica de verdade. A busca da Amil por uma cidade traz a
     rede da região inteira: em São José dos Pinhais, 157 dos 234 prestadores
     ficam em Curitiba. Mostrar a cidade pesquisada aqui seria mentir. */
  function localDe(p) {
    var cidades = p.cr && p.cr.length ? p.cr : p.cid;
    var bairro = (p.b && p.b.length) ? p.b[0] : "";
    return (bairro ? bairro + ", " : "") + cidades.join(" / ");
  }

  /* Distância em linha reta entre dois pontos (Haversine). Não é distância
     de carro — serve para ordenar "o que está mais perto", não para navegar. */
  function km(a, b) {
    var R = 6371, r = Math.PI / 180;
    var dLat = (b[0] - a[0]) * r, dLon = (b[1] - a[1]) * r;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(a[0] * r) * Math.cos(b[0] * r) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
  }

  function distanciaDe(p) {
    if (!estado.perto || !p.xy) return null;
    return km(estado.perto.xy, p.xy);
  }

  /* A Amil devolve tudo em CAIXA ALTA ("CADMO CLINICA MEDICA", "RUA SAO PIO
     X"). Ler uma tabela inteira gritada cansa e parece rascunho; o PDF ja
     capitalizava, a tela nao. Preserva siglas de 2-4 letras (UTI, CDI, SUS). */
  var MINUSCULAS = { da:1, das:1, de:1, di:1, do:1, dos:1, e:1, em:1, na:1,
                     nas:1, no:1, nos:1, ou:1, para:1, por:1 };
  var SIGLAS = { BR: 1, PR: 1, SC: 1, RS: 1, TEA:1, ATM:1, UTI:1, CDI:1, SUS:1, CNPJ:1, RX:1, TC:1, RM:1,
                 SPA:1, PS:1, UPA:1, AME:1, LTDA:1, ME:1, EPP:1, SA:1, S:1 };
  function bonito(t) {
    if (!t) return "";
    if (!/[A-ZÀ-Ú]{3}/.test(t)) return t;         // ja veio em caixa mista
    return String(t).replace(/[A-Za-zÀ-ú][A-Za-zÀ-ú'-]*/g, function (pal, i) {
      // o token leva o hifen junto ("Br-116" casa como "Br-"), entao a
      // consulta da sigla ignora pontuacao no fim
      var alto = pal.toUpperCase(), nu = alto.replace(/[-']+$/, "");
      if (SIGLAS[nu]) return nu + alto.slice(nu.length);
      var baixo = pal.toLowerCase();
      if (i > 0 && MINUSCULAS[baixo]) return baixo;
      return baixo.charAt(0).toUpperCase() + baixo.slice(1);
    });
  }

  /* Mesma limpeza que o PDF faz: fora o codigo TUSS do fim e o prefixo do
     tipo, que ja e o nome da faixa logo acima ("Hospitais - Cardiologia"
     dentro da secao Hospitais nao informa nada). */
  function especialidade(e) {
    return bonito(String(e || "")
      .replace(/\s*-\s*\d{6,}\s*$/, "")
      .replace(/^(HOSPITAIS|PRONTO SOCORRO|PRONTO ATENDIMENTO|LABORATORIOS E EXAMES|CONSULTORIOS)\s*-\s*/i, "")
      .replace(/\s*\|\s*/g, ", ")
      .trim());
  }

  /* Tirar o prefixo faz "HOSPITAIS - PSIQUIATRIA" e "PSIQUIATRIA" virarem a
     mesma coisa; sem juntar, a lista repete o termo. */
  function especialidades(lista) {
    var vistos = {}, saida = [];
    (lista || []).forEach(function (e) {
      var t = especialidade(e);
      if (t && !vistos[t]) { vistos[t] = 1; saida.push(t); }
    });
    return saida;
  }

  /* Categorias em que o hospital NAO e opcao de atendimento eletivo: ele
     realiza o exame, porem para internado e urgencia. */
  var CAT_EXAME = { "Laboratorios e imagem": 1 };

  /* Hospital e pronto-socorro sao o mesmo caso: fazem o exame, mas no
     contexto de urgencia e internacao. "Hospital Dia" e clinica de
     procedimento eletivo e NAO entra aqui - por isso a regra olha a
     categoria da Amil, nao o nome do prestador. */
  /* Categorias do prestador para efeito de FILTRO e de CONTAGEM.
     Em "Laboratorios e imagem" so entra quem atende exame eletivo; o
     hospital continua listado em Hospitais e Pronto-socorro 24h. */
  /* Especialidades que sao exame (montadas uma vez, a partir do proprio
     dado: tudo que algum prestador oferece dentro de "Laboratorios e
     imagem"). Serve para reconhecer a busca por exame feita sem escolher
     categoria - "Ressonancia Magnetica", por exemplo. */
  var ESP_EXAME = {};

  function mapearEspecialidadesDeExame() {
    ESP_EXAME = {};
    D.prestadores.forEach(function (p) {
      var lista = p.pc && p.pc["Laboratorios e imagem"];
      (lista || []).forEach(function (e) { ESP_EXAME[e] = 1; });
    });
  }

  var TIPO_LUGAR = { "Hospitais": 1, "Laboratorios e imagem": 1,
                     "Clinicas e consultorios": 1 };

  function quantos(p, cat) {
    return ((p.pc && p.pc[cat]) || []).length;
  }

  /* O que este prestador E (um so). Hospital manda; fora isso vale o que
     ele mais oferece - exames ou consultas. */
  function tipoDe(p) {
    var c = p.cats || [];
    // pronto-socorro entra aqui junto com hospital: o Hospital de Caridade de
    // Palmeira a Amil classifica so como PS, e ele nao e lugar de exame eletivo
    if (c.indexOf("Hospitais") >= 0 || c.indexOf("Pronto-socorro 24h") >= 0) {
      return "Hospitais";
    }
    var exames = quantos(p, "Laboratorios e imagem");
    var consultas = quantos(p, "Clinicas e consultorios");
    if (exames > consultas) return "Laboratorios e imagem";
    if (consultas > 0) return "Clinicas e consultorios";
    if (exames > 0) return "Laboratorios e imagem";
    return null;
  }

  /* Categorias validas do prestador: o tipo dele + os servicos que presta. */
  function catsDe(p) {
    var tipo = tipoDe(p), saida = tipo ? [tipo] : [];
    (p.cats || []).forEach(function (c) {
      if (!TIPO_LUGAR[c]) saida.push(c);          // servico: sempre soma
    });
    return saida;
  }

  function ehHospitalWeb(p) {
    var c = p.cats || [];
    return c.indexOf("Hospitais") >= 0 || c.indexOf("Pronto-socorro 24h") >= 0;
  }

  /* Atendimento ELETIVO - exame marcado e consulta marcada. No hospital o que
     acontece e internacao e urgencia; eletivo e em laboratorio, centro de
     imagem ou clinica. (Nao confundir com CAT_EXAME la acima, que serve para
     reconhecer quando o FILTRO em curso e de exame.) */
  var CAT_ELETIVA = { "Laboratorios e imagem": 1,
                      "Clinicas e consultorios": 1 };

  /* Especialidades que a ficha de um prestador pode anunciar.

     A ficha do hospital NAO lista o que ele so faz internado: quem lia
     "Ressonancia Magnetica" embaixo do nome do hospital ligava para marcar e
     levava um nao - e o nao sobrava para o corretor. O dado continua inteiro
     em `p.pc`, que e de onde o PDF monta as secoes; aqui ele so deixa de ser
     anunciado como porta aberta. */
  function espDe(p) {
    if (!ehHospitalWeb(p)) return p.esp || [];
    var eletiva = {}, pc = p.pc || {};
    Object.keys(CAT_ELETIVA).forEach(function (c) {
      (pc[c] || []).forEach(function (e) { eletiva[e] = 1; });
    });
    return (p.esp || []).filter(function (e) { return !eletiva[e]; });
  }

  /* A ressalva vale onde a ficha de fato encurtou - `visiveis` e a lista que
     o cliente vai ler.

     Nao basta ter eletivo guardado. Quando a Amil publica a MESMA
     especialidade nas duas pontas ("OFTALMOLOGIA" e "HOSPITAIS -
     OFTALMOLOGIA"), as duas aparecem como "Oftalmologia" e nada sai da vista;
     sao os casos de "Medicos de Olhos" e "Hospital de Olhos Cascavel" -
     clinica de procedimento que a Amil classifica em Hospitais, onde a
     consulta eletiva provavelmente acontece. Avisar "so internacao e
     urgencia" ali seria mentir contra o credenciado. */
  function temEletivoOculto(p, visiveis) {
    if (!ehHospitalWeb(p)) return false;
    var pc = p.pc || {};
    var temGuardado = Object.keys(CAT_ELETIVA).some(function (c) {
      return (pc[c] || []).length > 0;
    });
    if (!temGuardado) return false;
    return especialidades(p.esp).length > visiveis.length;
  }

  /* O filtro em curso e de exame? Ai a ordem e o aviso mudam. */
  function filtrandoExame() {
    var cats = escolhidos("cat");
    if (cats.length && cats.every(function (c) { return CAT_EXAME[c]; })) {
      return true;
    }
    var esps = escolhidos("esp");
    return esps.length > 0 && esps.every(function (e) { return ESP_EXAME[e]; });
  }

  /* Familias de rede nao tem acomodacao (QC e QP viraram um cartao so),
     entao o rotulo nao pode carregar um espaco solto no fim. */
  function rotuloProduto(p) {
    return (p.rotulo + " " + (p.acomodacao || "")).trim();
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // valores possiveis de cada campo, recalculados conforme o que ja foi filtrado
  var opcoes = { cid: [], cidr: [], cat: [], esp: [], bairro: [] };

  function botaoDe(campo) {
    return document.querySelector('.seletor[data-campo="' + campo + '"]');
  }

  function pintarSeletor(campo) {
    var b = botaoDe(campo), lista = escolhidos(campo);
    if (!b) return;
    b.classList.toggle("tem", lista.length > 0);
    b.querySelector(".resumo").textContent =
      lista.length === 0 ? TUDO[campo]
      : lista.length === 1 ? lista[0]
      : lista.length + " selecionados";
  }

  function marcasEscolhidas() {
    var alvo = $("escolhidos"), html = "";
    CAMPOS.forEach(function (campo) {
      escolhidos(campo).forEach(function (v) {
        html += '<span class="marca-filtro"><b>' + esc(ROTULO[campo]) +
                "</b>" + esc(v) + '<button type="button" data-campo="' +
                campo + '" data-valor="' + esc(v) +
                '" aria-label="remover">&times;</button></span>';
      });
    });
    alvo.innerHTML = html;
  }

  function alternar(campo, valor) {
    if (estado.f[campo][valor]) delete estado.f[campo][valor];
    else estado.f[campo][valor] = 1;
    if (campo === "cid" || campo === "cidr") dependentes();
    pintarSeletor(campo);
    marcasEscolhidas();
    desenhar();
  }

  /* Abre a lista ancorada no botão. Mostra quantos prestadores cada opção
     traria com os outros filtros já aplicados - evita escolher e dar zero. */
  function abrirLista(campo) {
    var painel = $("listaFlutuante"), botao = botaoDe(campo);
    estado.aberto = campo;
    painel.hidden = false;
    $("tituloLista").textContent = ROTULO[campo];
    $("buscaLista").value = "";
    desenharLista();          // desenha antes de medir: a altura tem que ser a real
    posicionar();
    $("buscaLista").focus();
  }

  /* Encosta o painel no botão sem deixar nenhuma borda sair da janela. No
     celular o CSS já o prende embaixo, então aqui não mexemos. */
  function posicionar() {
    var painel = $("listaFlutuante");
    if (painel.hidden || !estado.aberto) return;
    if (window.innerWidth <= 640) {
      painel.style.left = "";
      painel.style.top = "";
      return;
    }
    var r = botaoDe(estado.aberto).getBoundingClientRect();
    var alt = painel.offsetHeight, larg = painel.offsetWidth;
    painel.style.left = Math.max(8,
      Math.min(r.left, window.innerWidth - larg - 8)) + "px";
    var topo = r.bottom + 5;
    if (topo + alt > window.innerHeight - 8) {
      topo = r.top - alt - 5;                       // tenta abrir para cima
      if (topo < 8) topo = Math.max(8, window.innerHeight - alt - 8);
    }
    painel.style.top = topo + "px";
  }

  function fecharLista() {
    $("listaFlutuante").hidden = true;
    estado.aberto = null;
  }

  /* Os bairros que servem de referência: precisam de pelo menos dois
     prestadores para o centro fazer sentido. */
  function opcoesPerto() {
    var lista = Object.keys(D.centros || {}).map(function (k) {
      var partes = k.split("|");
      return { chave: k, bairro: partes[0], cidade: partes[1],
               xy: [D.centros[k][0], D.centros[k][1]], n: D.centros[k][2] };
    });
    lista.sort(function (a, b) {
      if (a.cidade !== b.cidade) return semAcento(a.cidade) < semAcento(b.cidade) ? -1 : 1;
      return semAcento(a.bairro) < semAcento(b.bairro) ? -1 : 1;
    });
    return lista;
  }

  function abrirPerto() {
    var painel = $("listaFlutuante");
    estado.aberto = "perto";
    painel.hidden = false;
    $("tituloLista").textContent = "Perto de";
    $("buscaLista").value = "";
    desenharLista();
    posicionar();
    $("buscaLista").focus();
  }

  function desenharLista() {
    var campo = estado.aberto;
    if (!campo) return;
    var busca = semAcento($("buscaLista").value.trim());
    if (campo === "perto") {
      var html2 = '<label class="opcao"><input type="radio" name="perto" value=""' +
                  (estado.perto ? "" : " checked") +
                  '><span>Não ordenar por distância</span></label>';
      opcoesPerto().forEach(function (o) {
        if (busca && semAcento(o.bairro + " " + o.cidade).indexOf(busca) < 0) return;
        html2 += '<label class="opcao"><input type="radio" name="perto" value="' +
                 esc(o.chave) + '"' +
                 (estado.perto && estado.perto.chave === o.chave ? " checked" : "") +
                 "><span>" + esc(o.bairro) +
                 ' <font color="#98a1b0">· ' + esc(o.cidade) + "</font></span>" +
                 '<span class="qtd">' + o.n + "</span></label>";
      });
      $("opcoesLista").innerHTML = html2;
      $("contaLista").textContent = estado.perto
        ? "ordenado a partir de " + estado.perto.bairro : "sem ordenação";
      return;
    }
    var contagem = contarPor(campo);
    var html = "";
    // o que dá resultado vem primeiro; o que daria zero desce e fica apagado
    var visiveis = opcoes[campo].filter(function (v) {
      return !busca || semAcento(v).indexOf(busca) >= 0;
    }).sort(function (a, b) {
      var na = (contagem[a] || 0) > 0 ? 0 : 1, nb = (contagem[b] || 0) > 0 ? 0 : 1;
      if (na !== nb) return na - nb;
      return semAcento(a) < semAcento(b) ? -1 : 1;
    });
    visiveis.forEach(function (v) {
      var n = contagem[v] || 0;
      html += '<label class="opcao' + (n ? "" : " vazia") +
              '"><input type="checkbox" value="' + esc(v) + '"' +
              (estado.f[campo][v] ? " checked" : "") + "><span>" +
              esc(v) + '</span><span class="qtd">' + n + "</span></label>";
    });
    $("opcoesLista").innerHTML = html ||
      '<div class="opcao" style="color:var(--tinta-fraca)">nada encontrado</div>';
    var n = escolhidos(campo).length;
    $("contaLista").textContent = n ? n + " selecionado" + (n > 1 ? "s" : "")
                                    : "nenhum selecionado";
  }

  /* Quantos prestadores cada opção deste campo traria, com os DEMAIS filtros
     valendo. */
  function contarPor(campo) {
    var base = filtrar(campo), conta = {};
    base.forEach(function (p) {
      var valores = campo === "cid" ? p.cid
                  : campo === "cidr" ? (p.cr && p.cr.length ? p.cr : [p.cid])
                  : campo === "cat" ? catsDe(p)
                  : campo === "esp" ? p.esp : p.b;
      (valores || []).forEach(function (v) {
        conta[v] = (conta[v] || 0) + 1;
      });
    });
    return conta;
  }

  /* Tamanho da rede de cada plano, respeitando os filtros de lugar mas
     ignorando quais produtos estao marcados - senao o cartao mostraria
     zero para todo plano nao selecionado. */
  function atualizarCartoes() {
    var base = baseEntre();
    var maior = 0, dados = {};
    D.produtos.forEach(function (pr) {
      var quem = base.filter(function (p) {
        return produtosDe(p).indexOf(pr.codigo) >= 0;
      });
      var cid = {}, hosp = 0;
      quem.forEach(function (p) {
        ((p.cr && p.cr.length) ? p.cr : p.cid).forEach(function (c) {
          cid[c] = 1;
        });
        if (tipoDe(p) === "Hospitais") hosp++;
      });
      dados[pr.codigo] = { n: quem.length, hosp: hosp,
                           cid: Object.keys(cid).length };
      if (quem.length > maior) maior = quem.length;
    });
    D.produtos.forEach(function (pr) {
      var d = dados[pr.codigo];
      var q = document.querySelector('[data-q="' + pr.codigo + '"]');
      var t = document.querySelector('[data-d="' + pr.codigo + '"]');
      var m = document.querySelector('[data-m="' + pr.codigo + '"]');
      if (!q) return;
      q.innerHTML = d.n + "<small>prestadores</small>";
      t.textContent = d.hosp + (d.hosp === 1 ? " hospital" : " hospitais") +
                      " · " + d.cid + (d.cid === 1 ? " cidade" : " cidades");
      m.style.width = (maior ? Math.max(2, 100 * d.n / maior) : 0) + "%";
    });
  }

  function montarProdutos() {
    var porLinha = {};
    D.produtos.forEach(function (p) {
      (porLinha[p.linha] = porLinha[p.linha] || []).push(p);
    });
    var alvo = $("grupos");
    alvo.innerHTML = "";
    Object.keys(porLinha).forEach(function (linha) {
      var g = document.createElement("div");
      g.className = "grupo";
      g.style.setProperty("--cor", COR[linha] || "var(--amil)");
      var r = document.createElement("span");
      r.className = "rotulo";
      r.textContent = linha;
      var fichas = document.createElement("div");
      fichas.className = "fichas";
      porLinha[linha].forEach(function (p) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "ficha";
        b.setAttribute("aria-pressed", "false");
        // cor propria do plano; sem ela, a cor da linha
        b.style.setProperty("--cor", p.cor || COR[p.linha] || "var(--amil)");
        b.innerHTML =
          '<span class="nome-plano"><span class="marca">✓</span>' +
          esc(rotuloProduto(p)) + "</span>" +
          '<span class="qtd" data-q="' + esc(p.codigo) + '">—</span>' +
          '<span class="detalhe" data-d="' + esc(p.codigo) + '"></span>' +
          '<span class="medida"><i data-m="' + esc(p.codigo) + '"></i></span>';
        b.onclick = function () {
          estado.produtos[p.codigo] = !estado.produtos[p.codigo];
          b.classList.toggle("ativa", !!estado.produtos[p.codigo]);
          b.setAttribute("aria-pressed", String(!!estado.produtos[p.codigo]));
          desenhar();
        };
        fichas.appendChild(b);
      });
      g.appendChild(r);
      g.appendChild(fichas);
      alvo.appendChild(g);
    });
  }

  /* Em quais produtos este prestador está, considerando as praças que você
     escolheu. A cobertura é por praça: o Santa Brígida está em 11 produtos
     quando a busca parte de Curitiba e em 2 quando parte de Pinhais. */
  function produtosDe(p) {
    var pracas = escolhidos("cid");
    if (!pracas.length || !p.pp) return p.p;
    var uniao = {};
    pracas.forEach(function (pr) {
      (p.pp[pr] || []).forEach(function (c) { uniao[c] = 1; });
    });
    return Object.keys(uniao);
  }

  function selecionados() {
    return D.produtos
      .filter(function (p) { return estado.produtos[p.codigo]; })
      .map(function (p) { return p.codigo; });
  }

  function colunas() {
    var s = selecionados();
    return s.length
      ? D.produtos.filter(function (p) { return s.indexOf(p.codigo) >= 0; })
      : D.produtos;
  }

  function algum(lista, conjunto) {
    for (var i = 0; i < lista.length; i++) if (conjunto[lista[i]]) return true;
    return false;
  }

  /* `ignorar` deixa de fora um campo - usado para contar as opções daquele
     campo sem que ele filtre a si mesmo. */
  function filtrar(ignorar) {
    var q = semAcento($("q").value.trim()), sel = selecionados();
    var usa = function (campo) {
      return campo !== ignorar && temEscolha(campo);
    };
    return D.prestadores.filter(function (p) {
      if (usa("cid") && !algum(p.cid, estado.f.cid)) return false;
      if (usa("cidr") && !algum(p.cr && p.cr.length ? p.cr : p.cid,
                                estado.f.cidr)) return false;
      if (usa("cat") && !algum(catsDe(p), estado.f.cat)) return false;
      if (usa("esp") && !algum(p.esp, estado.f.esp)) return false;
      if (usa("bairro") && !algum(p.b, estado.f.bairro)) return false;
      if (q && semAcento(p.n).indexOf(q) < 0 && (p.c || "").indexOf(q) < 0) {
        return false;
      }
      if (sel.length) {
        var meus = produtosDe(p);
        var tem = sel.filter(function (c) { return meus.indexOf(c) >= 0; });
        if (estado.modo === "e" ? tem.length !== sel.length : !tem.length) {
          return false;
        }
      }
      return true;
    });
  }

  function dependentes() {
    var bairros = {}, esps = {}, cats = {}, reais = {};
    D.prestadores.forEach(function (p) {
      if (temEscolha("cid") && !algum(p.cid, estado.f.cid)) return;
      (p.cr && p.cr.length ? p.cr : p.cid).forEach(function (x) {
        reais[x] = 1;
      });
      if (temEscolha("cidr") && !algum(p.cr && p.cr.length ? p.cr : p.cid,
                                       estado.f.cidr)) return;
      p.b.forEach(function (x) { bairros[x] = 1; });
      p.esp.forEach(function (x) { esps[x] = 1; });
      catsDe(p).forEach(function (x) { cats[x] = 1; });
    });
    var porOrdem = function (a, b) {
      return semAcento(a) < semAcento(b) ? -1 : 1;
    };
    opcoes.cidr = Object.keys(reais).sort(porOrdem);
    opcoes.bairro = Object.keys(bairros).sort(porOrdem);
    opcoes.esp = Object.keys(esps).sort(porOrdem);
    opcoes.cat = D.categorias.filter(function (c) { return cats[c]; });
    // uma escolha que deixou de existir sai sozinha
    ["cidr", "bairro", "esp", "cat"].forEach(function (campo) {
      escolhidos(campo).forEach(function (v) {
        if (opcoes[campo].indexOf(v) < 0) delete estado.f[campo][v];
      });
      pintarSeletor(campo);
    });
    marcasEscolhidas();
  }

  function desenhar(manterTeto) {
    if (!manterTeto) estado.teto = POR_VEZ;
    var r = filtrar(), cols = colunas();
    /* A etiqueta segue existindo para quando o hospital aparece por outro
       caminho (busca por nome, por especialidade), fora do filtro de
       categoria - ali ele nao foi excluido e o aviso continua valendo. */
    var soExame = filtrandoExame();
    if (soExame) {
      // quem atende eletivo primeiro; hospital e PS vao para o fim
      r = r.slice().sort(function (a, b) {
        var ha = ehHospitalWeb(a) ? 1 : 0, hb = ehHospitalWeb(b) ? 1 : 0;
        if (ha !== hb) return ha - hb;
        return D.categorias.indexOf(tipoDe(a) || a.cat) -
               D.categorias.indexOf(tipoDe(b) || b.cat);
      });
    }
    if (estado.perto) {
      // com referência, a ordem passa a ser a distância - dentro da categoria
      r = r.slice().sort(function (a, b) {
        if (a.cat !== b.cat) {
          return D.categorias.indexOf(a.cat) - D.categorias.indexOf(b.cat);
        }
        var da = distanciaDe(a), db = distanciaDe(b);
        if (da === null) return 1;
        if (db === null) return -1;
        return da - db;
      });
    }
    var cidades = {}, porCat = {};
    r.forEach(function (p) {
      (p.cr && p.cr.length ? p.cr : p.cid).forEach(function (c) {
        cidades[c] = 1;
      });
      porCat[tipoDe(p) || p.cat] = (porCat[tipoDe(p) || p.cat] || 0) + 1;
    });

    var m = '<div class="metrica"><b>' + r.length + "</b><span>prestadores</span></div>" +
            '<div class="metrica"><b>' + Object.keys(cidades).length + "</b><span>cidades</span></div>";
    D.categorias.forEach(function (c) {
      if (porCat[c]) {
        m += '<div class="metrica"><b>' + porCat[c] + "</b><span>" + esc(c) + "</span></div>";
      }
    });
    $("resumo").innerHTML = m;
    atualizarCartoes();
    var temProduto = selecionados().length;
    $("instrucao").innerHTML = temProduto
      ? "<b>" + temProduto + (temProduto === 1 ? " plano marcado"
                                              : " planos marcados") + "</b>"
      : "Clique nos planos — pode marcar mais de um";
    $("limparSel").hidden = !temProduto;
    $("dicaModo").textContent = temProduto
      ? "Mostrando só as colunas dos produtos marcados."
      : "Sem seleção, a tabela mostra todos os produtos.";
    // o PDF depende de um produto marcado: o botao diz isso sozinho
    $("pdf").classList.toggle("esperando", !temProduto);
    $("pdf").textContent = temProduto ? "Gerar PDF" : "Gerar PDF — escolha um produto";

    if (!$("panorama").hidden) montarPanorama();
    $("nada").hidden = r.length > 0;
    var t = $("tabela");
    if (!r.length) { t.innerHTML = ""; return; }

    var h = '<thead><tr><th class="fixa">Prestador</th><th>Endereço e contato</th>';
    cols.forEach(function (c) {
      h += '<th class="prod">' + esc(c.rotulo) + "<i>" + esc(c.acomodacao) + "</i></th>";
    });
    h += "</tr></thead><tbody>";

    var catAtual = null;
    var mostrados = r.slice(0, estado.teto);
    mostrados.forEach(function (p) {
      var chaveFaixa = (soExame && ehHospitalWeb(p)) ? "\u0000hosp"
                     : (tipoDe(p) || p.cat);
      if (chaveFaixa !== catAtual) {
        catAtual = chaveFaixa;
        var rotuloFaixa = esc(catAtual === "\u0000hosp" ? "Hospitais"
                                                       : catAtual);
        if (soExame && ehHospitalWeb(p)) {
          rotuloFaixa = "Hospitais — exames apenas em pronto-socorro e " +
                        "internação, não para exame eletivo";
        }
        h += '<tr class="faixa' + (soExame && ehHospitalWeb(p) ? " alerta" : "") +
             '"><td colspan="' + (2 + cols.length) + '">' +
             rotuloFaixa + "</td></tr>";
      }
      var selo = p.s && p.s.length
        ? '<span class="marca-selo" title="' + esc(p.s.join(", ")) + '">' +
          esc(p.s[0]) + "</span>"
        : "";
      var dist = distanciaDe(p);
      var etiquetaKm = dist === null ? "" :
        '<span class="km">' + (dist < 10 ? dist.toFixed(1) : Math.round(dist)) +
        ' km</span>';
      var esps = especialidades(espDe(p));
      var soInternado = temEletivoOculto(p, esps)
        ? '<span class="interna">só internação e urgência</span>'
        : "";
      var aviso = (soExame && ehHospitalWeb(p))
        ? '<span class="so-ps" title="Hospital realiza o exame, mas em regra ' +
          'para paciente internado e em urgência">PS / INTERNAÇÃO</span>' : "";
      h += '<tr><td class="fixa"><div class="nome">' + esc(bonito(p.n)) + selo + aviso +
           etiquetaKm + "</div>" +
           '<div class="miudo"><span class="cnpj">' + esc(p.c || "sem CNPJ") +
           "</span> · " + esc(bonito(localDe(p))) + "</div>" +
           '<div class="especs">' + esc(esps.slice(0, 5).join(" · ")) +
           (esps.length > 5 ? " · +" + (esps.length - 5) : "") +
           soInternado + "</div></td>" +
           "<td>" + esc(bonito(p.e.slice(0, 2).join(" | "))) +
           (p.e.length > 2 ? '<div class="miudo">+' + (p.e.length - 2) + " endereços</div>" : "") +
           '<div class="miudo">' + esc(p.t.join(" · ")) + "</div></td>";
      var meus = produtosDe(p);
      cols.forEach(function (c) {
        var tem = meus.indexOf(c.codigo) >= 0;
        h += '<td class="prod' + (tem ? " tem" : "") +
             '" style="--cor:' + (COR[c.linha] || "var(--amil)") + '">' +
             (tem ? "&#10003;" : "") + "</td>";
      });
      h += "</tr>";
    });
    if (r.length > mostrados.length) {
      h += '<tr class="mais"><td colspan="' + (2 + cols.length) + '">' +
           "<span>mostrando " + mostrados.length + " de " + r.length +
           " prestadores</span>" +
           '<button type="button" id="verMais">Mostrar mais ' +
           Math.min(POR_VEZ, r.length - mostrados.length) + "</button></td></tr>";
    }
    t.innerHTML = h + "</tbody>";
    var botao = $("verMais");
    if (botao) {
      botao.onclick = function () {
        estado.teto += POR_VEZ;
        desenhar(true);
      };
    }
  }

  // O visualizador do link entrega arquivos pela capability "downloads";
  // aberto como arquivo local, cai no download comum do navegador.
  /* O visualizador do link entrega arquivos pela capability "downloads".
     Sem ela, o <a download> abaixo é bloqueado SEM AVISO - por isso aqui o
     estado é explícito e aparece na tela em vez de falhar em silêncio. */
  var salvador = null;
  var entregaPronta = "aguardando";

  function avisar(texto, permanente) {
    var el = $("avisoDownload");
    if (!texto) { el.hidden = true; return; }
    el.innerHTML = texto;
    el.hidden = false;
    if (!permanente) {
      clearTimeout(avisar._t);
      avisar._t = setTimeout(function () { el.hidden = true; }, 6000);
    }
  }

  if (window.claude && typeof window.claude.use === "function") {
    window.claude.use("downloads").then(function (d) {
      salvador = d;
      entregaPronta = d ? "ok" : "indisponivel";
      if (!d) {
        avisar("<b>Este visualizador não permite baixar arquivos.</b> " +
               "O PDF e o CSV são montados, mas não conseguem ser salvos aqui. " +
               "Abra o link em uma aba do navegador ou peça o arquivo por outro " +
               "caminho.", true);
      }
    }).catch(function () {
      entregaPronta = "indisponivel";
      avisar("<b>Não consegui preparar o download nesta página.</b>", true);
    });
  } else {
    // página aberta como arquivo local: o download comum do navegador funciona
    entregaPronta = "navegador";
  }

  function entregar(nome, texto) {
    salvar(nome, texto, "text/csv;charset=utf-8");
  }

  /* Um caminho só para CSV e PDF, com o resultado sempre visível. */
  function salvar(nome, dado, mime) {
    if (entregaPronta === "aguardando") {
      avisar("Preparando o download… tente de novo em um instante.");
      return;
    }
    if (salvador) {
      avisar("Salvando <b>" + esc(nome) + "</b>… confirme na janela que aparecer.");
      salvador.save({ filename: nome, data: dado })
        .then(function () { avisar("<b>" + esc(nome) + "</b> salvo."); })
        .catch(function (e) {
          var c = e && e.code;
          avisar(c === "declined"
            ? "Download cancelado."
            : "<b>Não consegui salvar</b> (" + esc(c || "erro") + "). " +
              "Tente abrir o link em uma aba do navegador.", c !== "declined");
        });
      return;
    }
    if (entregaPronta === "indisponivel") {
      avisar("<b>Este visualizador não permite baixar arquivos.</b> " +
             "Abra o link em uma aba do navegador para salvar.", true);
      return;
    }
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([dado], { type: mime }));
    a.download = nome;
    document.body.appendChild(a);
    a.click();
    a.remove();
    avisar("<b>" + esc(nome) + "</b> baixado.");
  }

  function baixarCsv() {
    var r = filtrar(), cols = colunas();
    var cab = ["Categoria", "Prestador", "CNPJ", "Rede de", "Cidade do prestador",
               "Bairros", "Enderecos", "Telefones", "Especialidades"]
      .concat(estado.perto ? ["Km de " + estado.perto.bairro] : [])
      .concat(cols.map(function (c) { return c.rotulo + " " + c.acomodacao; }));
    var asp = function (v) {
      return '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"';
    };
    var linhas = r.map(function (p) {
      var meus = produtosDe(p);
      return [p.cat, p.n, p.c, (p.cid || []).join(" | "),
              (p.cr || []).join(" | "), p.b.join(" | "), p.e.join(" | "),
              p.t.join(" | "), espDe(p).join(", ")]
        .concat(estado.perto
          ? [(distanciaDe(p) === null ? "" : distanciaDe(p).toFixed(1))] : [])
        .concat(cols.map(function (c) { return meus.indexOf(c.codigo) >= 0 ? "X" : ""; }))
        .map(asp).join(";");
    });
    var csv = "﻿" + [cab.map(asp).join(";")].concat(linhas).join("\r\n");
    entregar("rede-amil-pr-" + apelidoCidade().toLowerCase()
      .replace(/\s+/g, "-") + ".csv", csv);
  }


  // --------------------------------------------------- PDF de apresentação
  var GRUPOS_EXAME = [
    ["Análises clínicas e patologia",
     /ANALISES CLINICAS|ANATOMIA PATOLOGICA|HEMOTERAPIA/],
    ["Diagnóstico por imagem",
     /RESSONANCIA|TOMOGRAFIA|ANGIO|ULTRASSON|ULTRASON|ULTRASOM|DOPPLER|DOOPLER|DUPLEX|MAMOGRAFIA|MAMOTOMIA|DENSITOMETRIA|RADIOLOGIA|CINTILOGRAFIA|MEDICINA NUCLEAR|PET CT|PUNCAO OU BIOPSIA/],
    ["Exames funcionais",
     /AUDIOMETRIA|IMPEDANCIOMETRIA|ELETROENCEFALOGRAMA|ELETRONEUROMIOGRAFIA|HOLTER|M\.?A\.?P\.?A|TESTE ERGOMETRICO|ECODOPPLERCARDIOGRAMA|POLISSONOGRAFIA|PROVA DE FUNCAO PULMONAR|CARDIOTOCOGRAFIA|URODINAMICA|PH-METRIA/],
    ["Endoscopia e procedimentos",
     /COLONOSCOPIA|ENDOSCOPIA|BRONCOSCOPIA|HISTEROSCOPIA|COLPOSCOPIA|FIBROSCOPIA|VIDEOLAPAROSCOPIA|CATETERISMO|LITOTRIPSIA/],
    ["Oncologia", /QUIMIOTERAPIA|RADIOTERAPIA/]
  ];

  function grupoExame(esp) {
    var e = semAcento(esp);
    for (var i = 0; i < GRUPOS_EXAME.length; i++) {
      if (GRUPOS_EXAME[i][1].test(e)) return GRUPOS_EXAME[i][0];
    }
    return "Outros exames";
  }

  /* Com UM produto marcado o PDF sai detalhado (com especialidades). Com
     VARIOS ele vira comparativo: uma coluna de visto por produto, no lugar
     das especialidades - nao ha largura para os dois. */
  var MAX_COLUNAS_PDF = 8;

  function produtosEscolhidos() {
    var sel = selecionados();
    return D.produtos.filter(function (p) { return sel.indexOf(p.codigo) >= 0; });
  }

  /* Hospital que tambem aparece nos exames. A Amil lista o hospital como
     lugar de fazer ressonancia porque ele de fato faz - mas em regra para
     internado e urgencia, nao para exame eletivo. */
  function ehHospital(p) {
    var c = p.cats || [];
    return c.indexOf("Hospitais") >= 0 || c.indexOf("Pronto-socorro 24h") >= 0;
  }

  function ordenarPorNome(a, b) {
    return semAcento(a.n) < semAcento(b.n) ? -1 :
           (semAcento(a.n) > semAcento(b.n) ? 1 : 0);
  }

  /* ===================================================== VISAO GERAL ===== */

  /* Cores dos graficos. As da marca (#2733c4 / #7c2f6d / #0b6154) servem para
     o visto da tabela, onde o texto ao lado carrega a identidade, mas
     reprovam como preenchimento de barra: um leitor deuteranope nao separa
     o roxo da Adesao do verde do Amil S (ΔE 4,0). Estes tres passam nos dois
     modos, claro e escuro. */
  var COR_GRAFICO = { "PME/PJ": "#4457e0", "Adesao": "#b03a97",
                      "Amil S": "#0f9a80", "Black": "#5b6472" };

  /* Limites reais de cada estado. Alguns enderecos da Amil sao
     administrativos e caem em outra UF (achei um na Paraiba); sem recorte,
     um ponto perdido esmaga a escala do mapa inteiro. */
  var LIMITES = {
    PR: { lat: [-26.72, -22.51], lng: [-54.62, -48.02] },
    SC: { lat: [-29.36, -25.95], lng: [-53.84, -48.35] },
    RS: { lat: [-33.75, -27.08], lng: [-57.65, -49.69] }
  };

  function dentroDoEstado(xy) {
    var lim = LIMITES[D.uf];
    if (!lim || !xy) return !!xy;
    return xy[0] >= lim.lat[0] && xy[0] <= lim.lat[1] &&
           xy[1] >= lim.lng[0] && xy[1] <= lim.lng[1];
  }

  /* Uma linha por cidade: quantos prestadores, quantos hospitais e o ponto
     medio de quem esta la. */
  function cidadesComRede(lista) {
    var mapa = {};
    lista.forEach(function (p) {
      if (!dentroDoEstado(p.xy)) return;
      var onde = (p.cr && p.cr.length) ? p.cr : p.cid;
      onde.forEach(function (c) {
        var r = mapa[c] || (mapa[c] = { nome: c, n: 0, hosp: 0, lat: 0, lng: 0 });
        r.n++;
        if (tipoDe(p) === "Hospitais") r.hosp++;
        r.lat += p.xy[0];
        r.lng += p.xy[1];
      });
    });
    return Object.keys(mapa).map(function (k) {
      var r = mapa[k];
      r.lat /= r.n; r.lng /= r.n;
      return r;
    }).sort(function (a, b) { return b.n - a.n; });
  }

  function desenharMapa(cidades) {
    var svg = $("mapa");
    svg.innerHTML = "";
    if (!cidades.length) return;

    var L = 1000, A = 460, PAD = 34;
    svg.setAttribute("viewBox", "0 0 " + L + " " + A);

    var lats = cidades.map(function (c) { return c.lat; });
    var lngs = cidades.map(function (c) { return c.lng; });
    var la0 = Math.min.apply(null, lats), la1 = Math.max.apply(null, lats);
    var lo0 = Math.min.apply(null, lngs), lo1 = Math.max.apply(null, lngs);
    // longitude encurta conforme a latitude: sem isso o estado sai esticado
    var k = Math.cos((la0 + la1) / 2 * Math.PI / 180);
    var larg = Math.max((lo1 - lo0) * k, 1e-6), alt = Math.max(la1 - la0, 1e-6);
    var escala = Math.min((L - 2 * PAD) / larg, (A - 2 * PAD) / alt);
    var cx = (L - larg * escala) / 2, cy = (A - alt * escala) / 2;

    function px(c) {
      return [cx + (c.lng - lo0) * k * escala,
              cy + (la1 - c.lat) * escala];
    }

    var maior = cidades[0].n;
    function raio(n) { return 5 + 30 * Math.sqrt(n / maior); }

    var ns = "http://www.w3.org/2000/svg";
    var dica = $("mapaDica");
    var ocupado = [];               // caixas de texto ja colocadas

    // maiores primeiro no DOM para os menores ficarem por cima e clicaveis
    cidades.forEach(function (c) {
      var pt = px(c), r = raio(c.n);
      var g = document.createElementNS(ns, "g");
      g.setAttribute("class", "cidade");

      var circ = document.createElementNS(ns, "circle");
      circ.setAttribute("cx", pt[0].toFixed(1));
      circ.setAttribute("cy", pt[1].toFixed(1));
      circ.setAttribute("r", r.toFixed(1));
      circ.setAttribute("fill", "var(--marca-texto)");
      circ.setAttribute("fill-opacity", "0.16");
      circ.setAttribute("stroke", "var(--marca-texto)");
      circ.setAttribute("stroke-opacity", "0.55");
      circ.setAttribute("stroke-width", "1.4");
      g.appendChild(circ);

      if (c.hosp) {                      // hospital: ponto cheio no centro
        var nucleo = document.createElementNS(ns, "circle");
        nucleo.setAttribute("cx", pt[0].toFixed(1));
        nucleo.setAttribute("cy", pt[1].toFixed(1));
        nucleo.setAttribute("r", Math.min(r - 1.5, 3 + c.hosp * 0.5).toFixed(1));
        nucleo.setAttribute("fill", "var(--ouro)");
        g.appendChild(nucleo);
      }

      if (r > 13) {
        var nome = bonito(c.nome);
        // largura estimada do texto: 5,6 px por caractere a 11 px, seriveis
        // para reservar espaco sem medir no DOM a cada circulo
        var meiaLarg = nome.length * 2.8 + 4;
        var caixa = { x0: pt[0] - meiaLarg, x1: pt[0] + meiaLarg,
                      y0: pt[1] + r + 3, y1: pt[1] + r + 17 };
        var livre = ocupado.every(function (o) {
          return caixa.x1 < o.x0 || caixa.x0 > o.x1 ||
                 caixa.y1 < o.y0 || caixa.y0 > o.y1;
        });
        if (livre) {
          ocupado.push(caixa);
          var t = document.createElementNS(ns, "text");
          t.setAttribute("x", pt[0].toFixed(1));
          t.setAttribute("y", (pt[1] + r + 13).toFixed(1));
          t.setAttribute("text-anchor", "middle");
          t.setAttribute("font-size", "11");
          t.setAttribute("font-weight", "600");
          t.setAttribute("fill", "var(--tinta)");
          t.setAttribute("paint-order", "stroke");
          t.setAttribute("stroke", "var(--papel)");
          t.setAttribute("stroke-width", "3.5");
          t.setAttribute("stroke-linejoin", "round");
          t.textContent = nome;
          g.appendChild(t);
        }
      }

      g.addEventListener("mousemove", function (ev) {
        var caixa = svg.parentNode.getBoundingClientRect();
        dica.innerHTML = "<b>" + esc(bonito(c.nome)) + "</b><br>" +
          c.n + (c.n === 1 ? " prestador" : " prestadores") +
          (c.hosp ? " · <i>" + c.hosp +
                    (c.hosp === 1 ? " hospital" : " hospitais") + "</i>" : "");
        dica.hidden = false;
        var x = ev.clientX - caixa.left + 14, y = ev.clientY - caixa.top + 14;
        dica.style.left = Math.min(x, caixa.width - dica.offsetWidth - 8) + "px";
        dica.style.top = y + "px";
      });
      g.addEventListener("mouseleave", function () { dica.hidden = true; });
      svg.appendChild(g);
    });

    // legenda de tamanho, com valores reais desta seleção
    var meio = Math.max(1, Math.round(maior / 6));
    $("mapaLegenda").innerHTML =
      '<span class="amostra">' + bolinha(raio(meio)) + meio + " prestadores</span>" +
      '<span class="amostra">' + bolinha(raio(maior)) + maior + " prestadores</span>" +
      '<span class="amostra"><span style="width:9px;height:9px;border-radius:50%;' +
      'background:var(--ouro);display:inline-block"></span>' +
      "o miolo dourado marca cidade com hospital</span>";
  }

  function bolinha(r) {
    var d = Math.min(26, Math.max(9, r));
    return '<span style="width:' + d + "px;height:" + d + "px;border-radius:50%;" +
           "border:1.4px solid var(--marca-texto);background:var(--marca-texto);" +
           'opacity:.55;display:inline-block"></span>';
  }

  /* Barras horizontais: a pergunta e de grandeza, entao barra. Cor pela
     linha do produto, com legenda - identidade nunca so pela cor. */
  function barras(alvo, dados, sufixo) {
    var maior = Math.max.apply(null, dados.map(function (d) { return d.v; }));
    $(alvo).innerHTML = dados.map(function (d) {
      var larg = maior ? Math.max(2, 100 * d.v / maior) : 0;
      var cor = COR_GRAFICO[d.linha] || "var(--marca-texto)";
      return '<div class="barra" title="' + esc(d.rot) + ": " + d.v + " " +
             esc(sufixo) + '">' +
             '<span class="rot">' + esc(d.rot) + "</span>" +
             '<span class="trilho"><span class="preenche" style="width:' +
             larg.toFixed(1) + "%;background:" + cor + '"></span></span>' +
             '<span class="val">' + d.v + "</span></div>";
    }).join("");
  }

  function montarPanorama() {
    var lista = filtrar();
    var praças = escolhidos("cid");
    var cidades = cidadesComRede(lista);

    var hospitais = lista.filter(function (p) {
      return tipoDe(p) === "Hospitais";
    }).length;
    var exames = lista.filter(function (p) {
      return tipoDe(p) === "Laboratorios e imagem";
    }).length;
    var consultorios = lista.filter(function (p) {
      return tipoDe(p) === "Clinicas e consultorios";
    }).length;

    $("panNumeros").innerHTML = [
      [lista.length, "prestadores"],
      [cidades.length, cidades.length === 1 ? "cidade" : "cidades"],
      [hospitais, "hospitais"],
      [exames, "exames e laboratórios"],
      [consultorios, "clínicas e consultórios"]
    ].map(function (n) {
      return '<div class="n"><b>' + n[0] + "</b><span>" + esc(n[1]) + "</span></div>";
    }).join("");

    $("panNota").textContent = praças.length
      ? "Rede que a Amil devolve para " + praças.map(bonito).join(", ") +
        ". Parte dos prestadores fica em municípios vizinhos — use a aba " +
        "Rede completa para ver cidade por cidade."
      /* "inteira" so vale em estado varrido por completo - havendo nota de
         recorte, essa palavra desmentiria o aviso do cabecalho. */
      : (D.nota
          ? "Tudo que já foi levantado em " + (D.estado || D.uf) + " — " +
            D.nota + ". Escolha uma praça no filtro da aba Rede completa " +
            "para recortar este panorama."
          : "Rede de " + (D.estado || D.uf) + " inteira. Escolha uma praça " +
            "no filtro da aba Rede completa para recortar este panorama.");

    // ---- graficos por produto
    var porProduto = D.produtos.map(function (pr) {
      var quem = lista.filter(function (p) {
        return produtosDe(p).indexOf(pr.codigo) >= 0;
      });
      var onde = {};
      quem.forEach(function (p) {
        ((p.cr && p.cr.length) ? p.cr : p.cid).forEach(function (c) { onde[c] = 1; });
      });
      return { rot: rotuloProduto(pr), linha: pr.linha,
               n: quem.length, cid: Object.keys(onde).length };
    });

    barras("grPrestadores", porProduto.slice()
      .sort(function (a, b) { return b.n - a.n; })
      .map(function (d) { return { rot: d.rot, linha: d.linha, v: d.n }; }),
      "prestadores");

    barras("grCidades", porProduto.slice()
      .sort(function (a, b) { return b.cid - a.cid; })
      .map(function (d) { return { rot: d.rot, linha: d.linha, v: d.cid }; }),
      "cidades");

    var linhas = {};
    D.produtos.forEach(function (p) { linhas[p.linha] = 1; });
    $("legendaLinhas").innerHTML = Object.keys(linhas).map(function (l) {
      return '<span class="item"><span class="marca" style="background:' +
             (COR_GRAFICO[l] || "var(--marca-texto)") + '"></span>' +
             esc(l === "Adesao" ? "Adesão" : l) + "</span>";
    }).join("");

    desenharMapa(cidades);
  }

  /* ================================================== ENTRE DOIS PLANOS === */

  /* Base da comparacao: tudo que passa nos filtros de lugar, IGNORANDO a
     selecao de produtos - aqui quem define o recorte sao os dois planos
     escolhidos, nao as fichas marcadas na outra aba. */
  function baseEntre() {
    var q = semAcento($("q").value.trim());
    return D.prestadores.filter(function (p) {
      if (temEscolha("cid") && !algum(p.cid, estado.f.cid)) return false;
      if (temEscolha("cidr") && !algum(p.cr && p.cr.length ? p.cr : p.cid,
                                       estado.f.cidr)) return false;
      if (temEscolha("cat") && !algum(catsDe(p), estado.f.cat)) return false;
      if (temEscolha("esp") && !algum(p.esp, estado.f.esp)) return false;
      if (temEscolha("bairro") && !algum(p.b, estado.f.bairro)) return false;
      if (q && semAcento(p.n).indexOf(q) < 0 && (p.c || "").indexOf(q) < 0) {
        return false;
      }
      return true;
    });
  }

  function cidadesDe(lista) {
    var c = {};
    lista.forEach(function (p) {
      ((p.cr && p.cr.length) ? p.cr : p.cid).forEach(function (x) { c[x] = 1; });
    });
    return c;
  }

  function compararPlanos(codA, codB) {
    var base = baseEntre();
    var noA = base.filter(function (p) { return produtosDe(p).indexOf(codA) >= 0; });
    var noB = base.filter(function (p) { return produtosDe(p).indexOf(codB) >= 0; });
    var emB = {};
    noB.forEach(function (p) { emB[p.c || p.n] = 1; });
    var perde = noA.filter(function (p) { return !emB[p.c || p.n]; });
    var emA = {};
    noA.forEach(function (p) { emA[p.c || p.n] = 1; });
    var ganha = noB.filter(function (p) { return !emA[p.c || p.n]; });

    var cidA = cidadesDe(noA), cidB = cidadesDe(noB);
    var cidadesSomem = Object.keys(cidA).filter(function (c) { return !cidB[c]; });

    return { noA: noA, noB: noB, perde: perde, ganha: ganha,
             cidadesSomem: cidadesSomem.sort(),
             cidadesA: Object.keys(cidA).length,
             cidadesB: Object.keys(cidB).length };
  }

  function nomeProduto(cod) {
    var p = D.produtos.filter(function (x) { return x.codigo === cod; })[0];
    return p ? rotuloProduto(p) : cod;
  }

  function cartao(p, classe) {
    return '<div class="cartao-perde' + (classe || "") + '">' +
           '<div class="nome">' + esc(bonito(p.n)) + "</div>" +
           '<div class="onde">' + esc(bonito(localDe(p))) + "</div></div>";
  }

  function montarEntre() {
    var codA = $("planoA").value, codB = $("planoB").value;
    if (!codA || !codB) return;
    var r = compararPlanos(codA, codB);
    var nA = nomeProduto(codA), nB = nomeProduto(codB);

    var hospPerde = r.perde.filter(function (p) {
      return tipoDe(p) === "Hospitais";
    });
    var praças = escolhidos("cid");
    var onde = praças.length ? praças.map(bonito).join(", ")
                             : (D.estado || D.uf);

    var mantidos = r.noA.length - r.perde.length;
    var pct = r.noA.length ? Math.round(100 * mantidos / r.noA.length) : 100;

    var h = "";
    /* Planos que compartilham quase tudo (caso das Adesoes com os PME)
       merecem essa leitura antes dos numeros de perda - senao a tela
       sugere um rebaixamento que nao existe. */
    if (pct >= 95 && r.perde.length) {
      h += '<div class="quase-igual"><b>Praticamente a mesma rede.</b> ' +
        "O " + esc(nB) + " mantém <b>" + pct + "%</b> da rede do " +
        esc(nA) + " em " + esc(onde) + " — " + mantidos + " dos " +
        r.noA.length + " prestadores. A diferença está em " + r.perde.length +
        (r.perde.length === 1 ? " prestador" : " prestadores") +
        (hospPerde.length ? ", " + hospPerde.length +
          (hospPerde.length === 1 ? " deles hospital" : " deles hospitais") : "") +
        ", listados abaixo." +
        '<span class="barra-igual"><i style="width:' + pct + '%"></i></span>' +
        "</div>";
    }

    h += '<div class="perde-numeros">' +
      '<div class="n igual"><b>' + pct +
        "%</b><span>da rede mantida</span></div>" +
      '<div class="n ruim"><b>' + r.perde.length +
        "</b><span>prestadores a menos</span></div>" +
      '<div class="n ruim"><b>' + hospPerde.length +
        "</b><span>hospitais a menos</span></div>" +
      '<div class="n ruim"><b>' + r.cidadesSomem.length +
        "</b><span>cidades sem rede</span></div>" +
      (r.ganha.length ? '<div class="n igual"><b>' + r.ganha.length +
        "</b><span>que só o " + esc(nB) + " tem</span></div>" : "") +
      "</div>";

    h += '<p class="sub" style="margin-top:14px">Trocando <b>' + esc(nA) +
         "</b> por <b>" + esc(nB) + "</b> em " + esc(onde) + ": o " +
         esc(nA) + " atende " + r.noA.length + " prestadores em " +
         r.cidadesA + " cidades; o " + esc(nB) + ", " + r.noB.length +
         " em " + r.cidadesB + ".</p>";

    if (hospPerde.length) {
      h += '<div class="bloco-perde"><h3>Hospitais que o cliente deixa de ter</h3>' +
           '<p class="sub">É a perda que pesa numa internação. ' +
           "Confira caso a caso antes de recomendar a troca.</p>" +
           '<div class="lista-perde">' +
           hospPerde.sort(ordenarPorNome).map(function (p) {
             return cartao(p, "");
           }).join("") + "</div></div>";
    }

    if (r.cidadesSomem.length) {
      h += '<div class="bloco-perde"><h3>Cidades que ficam sem rede</h3>' +
           '<p class="sub">Nestas cidades o ' + esc(nB) +
           " não tem nenhum prestador credenciado.</p>" +
           '<div class="fichas-cidade">' +
           r.cidadesSomem.map(function (c) {
             return '<span class="ficha-cidade some">' + esc(bonito(c)) +
                    "</span>";
           }).join("") + "</div></div>";
    }

    var outros = r.perde.filter(function (p) {
      return tipoDe(p) !== "Hospitais";
    });
    if (outros.length) {
      var porTipo = {};
      outros.forEach(function (p) {
        var t = tipoDe(p) || "Outros";
        (porTipo[t] = porTipo[t] || []).push(p);
      });
      h += '<div class="bloco-perde"><h3>Demais prestadores fora do ' +
           esc(nB) + "</h3>";
      Object.keys(porTipo).forEach(function (t) {
        h += '<p class="sub" style="margin-top:10px"><b>' + esc(t) + "</b> — " +
             porTipo[t].length + "</p>" +
             '<div class="lista-perde">' +
             porTipo[t].sort(ordenarPorNome).slice(0, 60)
               .map(function (p) { return cartao(p, ""); }).join("") +
             "</div>";
        if (porTipo[t].length > 60) {
          h += '<p class="sub">e mais ' + (porTipo[t].length - 60) +
               " — a lista completa está no PDF e na aba Rede completa.</p>";
        }
      });
      h += "</div>";
    }

    if (!r.perde.length) {
      h += '<p class="nada-perde">Nenhuma perda: nesta praça, tudo que o ' +
           esc(nA) + " atende o " + esc(nB) + " também atende.</p>";
    }

    $("entreCorpo").innerHTML = h;
  }

  function gerarPDFEntre() {
    if (!window.FONTES || !window.PDFWeb) {
      avisar("<b>O gerador de PDF não carregou nesta página.</b>", true);
      return;
    }
    var botao = $("pdfEntre"), rotulo = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Montando…";
    setTimeout(function () {
      try {
        montarPdfEntre();
      } catch (e) {
        avisar("<b>Não consegui montar o PDF:</b> " +
               esc(e && e.message ? e.message : e), true);
      }
      botao.disabled = false;
      botao.textContent = rotulo;
    }, 30);
  }

  function montarPdfEntre() {
    var codA = $("planoA").value, codB = $("planoB").value;
    var r = compararPlanos(codA, codB);
    var nA = nomeProduto(codA), nB = nomeProduto(codB);
    var prodA = D.produtos.filter(function (p) { return p.codigo === codA; })[0];
    var praças = escolhidos("cid");
    var onde = praças.length
      ? praças.map(function (c) { return bonito(c); }).join(", ")
      : (D.estado || D.uf);

    var aux = window.RelatorioAux;
    var rel = new window.Relatorio(window.FONTES, {
      produto: nA + "  para  " + nB,
      semCidadeNaCapa: false,
      cidade: onde,
      cor: aux.COR_LINHA[prodA ? prodA.linha : "PME/PJ"] || "#20456f",
      corretor: corretor,
      mapa: cidadesComRede(r.noA),
      semCidade: false
    });
    rel.carregarFontes();
    rel.capa();
    rel.novaPagina();

    var hospPerde = r.perde.filter(function (p) {
      return tipoDe(p) === "Hospitais";
    }).sort(ordenarPorNome);

    var mantidos = r.noA.length - r.perde.length;
    var pct = r.noA.length ? Math.round(100 * mantidos / r.noA.length) : 100;
    rel.titulo("O que muda de " + nA + " para " + nB,
      (pct >= 95 && r.perde.length
        ? "Praticamente a mesma rede: o " + nB + " mantém " + pct + "% do que o " +
          nA + " atende em " + onde + " (" + mantidos + " de " + r.noA.length +
          " prestadores). "
        : "Comparação da rede em " + onde + ". ") +
      "O " + nA + " atende " + r.noA.length + " prestadores em " +
      r.cidadesA + " cidades; o " + nB + ", " + r.noB.length + " em " +
      r.cidadesB + ". Levantado na busca avançada oficial da Amil.");

    rel.numeros([
      [pct + "%", "Da rede mantida"],
      [r.perde.length, "Prestadores a menos"],
      [hospPerde.length, "Hospitais a menos"],
      [r.cidadesSomem.length, "Cidades que ficam sem rede"],
      [mantidos, "Prestadores mantidos"],
      [r.noB.length, "Total no " + nB]
    ]);

    if (hospPerde.length) {
      rel.novaPagina();
      rel.faixa("Hospitais que saem da rede no " + nB, hospPerde.length);
      rel.tabela(hospPerde, true, []);
    }

    if (r.cidadesSomem.length) {
      rel.novaPagina();
      rel.titulo("Cidades que ficam sem rede",
        "Nestas cidades o " + nB + " não tem nenhum prestador credenciado. " +
        "O cliente que mora ou trabalha nelas precisaria se deslocar.");
      var txt = r.cidadesSomem.map(function (c) { return bonito(c); })
                              .join("   ·   ");
      var linhas = rel.pdf.quebrar(txt, "sans", 11, aux.UTIL);
      linhas.forEach(function (l) {
        rel.espaco(18);
        rel.pdf.texto(aux.MARGEM, rel.y, l, "sans", 11, "#a8341a");
        rel.y -= 15;
      });
      rel.y -= 10;
    }

    var outros = r.perde.filter(function (p) {
      return tipoDe(p) !== "Hospitais";
    });
    if (outros.length) {
      var porTipo = {};
      outros.forEach(function (p) {
        var t = tipoDe(p) || "Outros";
        (porTipo[t] = porTipo[t] || []).push(p);
      });
      Object.keys(porTipo).forEach(function (t) {
        rel.novaPagina();
        rel.faixa(t + " que saem no " + nB, porTipo[t].length);
        rel.tabela(porTipo[t].sort(ordenarPorNome), true, []);
      });
    }

    rel.novaPagina();
    rel.titulo("Antes de contratar");
    var aviso = "A rede credenciada é definida e alterada exclusivamente pela " +
      "operadora. Este documento compara o que a busca avançada oficial da " +
      "Amil devolveu na data da capa, para os planos " + nA + " e " + nB +
      " em " + onde + ". Confirme no portal da Amil antes de contratar ou " +
      "de recomendar a troca de plano.";
    rel.pdf.quebrar(aviso, "sans", 10, aux.UTIL * 0.8).forEach(function (l) {
      rel.pdf.texto(aux.MARGEM, rel.y, l, "sans", 10, "#1b2331");
      rel.y -= 14;
    });

    var bytes = rel.pdf.gerar();
    entregarBinario(("Amil " + nA + " x " + nB + " - " + onde + ".pdf")
                    .replace(/\//g, "-"), bytes);
  }

  function montarSelects() {
    var op = D.produtos.map(function (p) {
      return '<option value="' + esc(p.codigo) + '">' +
             esc(rotuloProduto(p)) + "</option>";
    }).join("");
    $("planoA").innerHTML = op;
    $("planoB").innerHTML = op;
    if (D.produtos.length > 1) {
      $("planoA").value = D.produtos[D.produtos.length - 1].codigo;
      $("planoB").value = D.produtos[0].codigo;
    }
  }

  function trocarAba(qual) {
    $("panorama").hidden = qual !== "panorama";
    $("entre").hidden = qual !== "entre";
    $("rede").hidden = qual !== "rede";
    Array.prototype.forEach.call($("abas").children, function (b) {
      b.classList.toggle("ativa", b.dataset.aba === qual);
    });
    if (qual === "panorama") montarPanorama();
    if (qual === "entre") montarEntre();
  }

  /* ============================================ DADOS DO CORRETOR ======= */

  /* O link e compartilhado entre corretores e cada um assina o proprio
     material. Fica no navegador de quem usa: nunca sai da maquina dele. */
  var CHAVE_CORRETOR = "mazza.corretor.v1";
  /* A marca do material nao e configuravel: o corretor assina com o
     contato dele, a corretora continua sendo a dona do material. */
  var CORRETORA_FIXA = "Mazza Broker";
  var corretor = null;

  function corretorPadrao() {
    var d = window.CORRETOR || {};
    return { nome: d.nome || "", corretora: CORRETORA_FIXA,
             email: d.email || "", fone: d.fone || "" };
  }

  function lerCorretor() {
    try {
      var cru = localStorage.getItem(CHAVE_CORRETOR);
      if (cru) {
        var d = JSON.parse(cru);
        if (d && d.nome) {
          d.corretora = CORRETORA_FIXA;   // ignora marca gravada antes
          return d;
        }
      }
    } catch (e) { /* navegador anonimo ou sem permissao: usa o padrao */ }
    return corretorPadrao();
  }

  function gravarCorretor(d) {
    corretor = d;
    try { localStorage.setItem(CHAVE_CORRETOR, JSON.stringify(d)); }
    catch (e) { /* sem storage: vale so nesta sessao */ }
    pintarCorretor();
  }

  function pintarCorretor() {
    $("quemAssina").textContent = corretor.nome || "definir";
    $("assinaRodape").textContent =
      (corretor.corretora || "") + (corretor.nome ? " · " + corretor.nome : "");
  }

  function abrirCorretor() {
    $("cNome").value = corretor.nome || "";
    $("cEmail").value = corretor.email || "";
    $("cFone").value = corretor.fone || "";
    $("painelCorretor").hidden = false;
    $("cNome").focus();
  }

  function gerarPDF() {
    var produtos = produtosEscolhidos();
    if (!produtos.length) {
      avisar("<b>Marque pelo menos um produto.</b> Um produto gera o PDF " +
             "detalhado, com as especialidades; vários geram o comparativo, " +
             "com uma coluna por plano.");
      return;
    }
    if (produtos.length > MAX_COLUNAS_PDF) {
      avisar("<b>" + produtos.length + " produtos não cabem na página.</b> " +
             "O comparativo aceita até " + MAX_COLUNAS_PDF +
             " colunas — desmarque alguns e gere de novo.", true);
      return;
    }
    if (!window.FONTES || !window.PDFWeb) {
      avisar("<b>O gerador de PDF não carregou nesta página.</b>", true);
      return;
    }
    var botao = $("pdf");
    botao.disabled = true;
    var rotuloAnterior = botao.textContent;
    botao.textContent = "Montando…";

    setTimeout(function () {
      try {
        montarEEntregar(produtos);
      } catch (e) {
        avisar("<b>Não consegui montar o PDF:</b> " +
               esc(e && e.message ? e.message : e), true);
      }
      botao.disabled = false;
      botao.textContent = rotuloAnterior;
    }, 30);
  }

  function apelidoCidade() {
    // se você filtrou por onde o prestador fica, é esse o recorte do material
    var c = temEscolha("cidr") ? escolhidos("cidr") : escolhidos("cid");
    if (!c.length) return D.estado || D.uf;
    if (c.length === 1) return c[0];
    if (c.length === 2) return c[0] + " e " + c[1];
    return c[0] + " e mais " + (c.length - 1) + " cidades";
  }

  function montarEEntregar(produtos) {
    var comparativo = produtos.length > 1;
    var produto = produtos[0];
    var lista = filtrar();
    var bruto = apelidoCidade();
    var rotuloCidade = bruto.replace(/(^|\s)(\S)(\S*)/g, function (m, a, b, c) {
      return a + b.toUpperCase() + c.toLowerCase();
    }).replace(/\bE\b/g, "e");
    var nomes = produtos.map(function (p) {
      return rotuloProduto(p);
    });
    var aux = window.RelatorioAux;
    var rel = new window.Relatorio(window.FONTES, {
      /* Com um produto o PDF e a rede daquele plano; com varios ele vira
         comparativo e a capa precisa dizer isso. */
      produto: comparativo
        ? (nomes.length <= 3 ? nomes.join("  \u00b7  ")
                             : nomes.length + " planos comparados")
        : nomes[0],
      semCidadeNaCapa: true,      // o rotulo acima do titulo ja diz a cidade
      mapa: cidadesComRede(lista),          // constelacao da capa
      produtos: produtos,
      cores: produtos.map(function (p) {
        return aux.COR_LINHA[p.linha] || "#20456f";
      }),
      comparativo: comparativo,
      listaProdutos: nomes,
      cidade: rotuloCidade,
      cor: aux.COR_LINHA[produto.linha] || "#20456f",
      corretor: corretor
    });
    rel.carregarFontes();
    rel.capa();
    rel.novaPagina();

    // por categoria, usando as especialidades daquela categoria
    function daCategoria(cat) {
      return lista.filter(function (p) {
        if (!(p.pc && p.pc[cat] && p.pc[cat].length)) return false;
        // tipo de lugar e exclusivo tambem no PDF; servico continua somando
        if (TIPO_LUGAR[cat] && tipoDe(p) !== cat) return false;
        return true;
      }).map(function (p) {
        var q = {}; for (var k in p) q[k] = p[k];
        q.meus = produtosDe(p);          // quais planos, para o comparativo
        // filtrou especialidade? o PDF lista só ela, não a agenda inteira
        q.esp = temEscolha("esp")
          ? p.pc[cat].filter(function (e) { return estado.f.esp[e]; })
          : p.pc[cat];
        return q;
      }).filter(function (p) { return p.esp.length; }).sort(function (a, b) {
        return b.esp.length - a.esp.length || ordenarPorNome(a, b);
      });
    }

    var hosp = daCategoria("Hospitais");
    var ps = daCategoria("Pronto-socorro 24h");
    var pa = daCategoria("Pronto atendimento");
    var lab = daCategoria("Laboratorios e imagem");
    var hemo = daCategoria("Hemodialise");
    var tea = daCategoria("TEA");
    var tele = daCategoria("Telemedicina");
    var cons = daCategoria("Clinicas e consultorios");

    var porGrupo = {};
    lab.forEach(function (p) {
      p.esp.forEach(function (e) {
        var g = grupoExame(e);
        porGrupo[g] = porGrupo[g] || {};
        if (!porGrupo[g][p.n]) {
          var q = {}; for (var k in p) q[k] = p[k];
          q.esp = [];
          porGrupo[g][p.n] = q;
        }
        porGrupo[g][p.n].esp.push(e);
      });
    });

    rel.titulo("A sua rede em números",
      (comparativo
        ? "Prestadores que atendem em pelo menos um dos planos comparados (" +
          nomes.join(", ") + ") em " + rotuloCidade + ". As colunas de cada " +
          "seção mostram quais planos cobrem cada prestador."
        : "Tudo que o plano " + nomes[0] + " cobre em " + rotuloCidade + ".") +
      " Levantado na busca avançada oficial da Amil.");
    /* Contar hospital como "laboratorio" incha o numero e promete o que o
       cliente nao usa no dia a dia: aqui entram so os centros e laboratorios. */
    function contarCentros(grupo) {
      var d = porGrupo[grupo] || {};
      return Object.keys(d).filter(function (k) {
        return !ehHospital(d[k]);
      }).length;
    }
    var nAnalises = contarCentros("Análises clínicas e patologia");
    var nImagem = contarCentros("Diagnóstico por imagem");
    rel.numeros([
      [hosp.length, "Hospitais para internação"],
      [ps.length, "Pronto-socorro 24 horas"],
      [nAnalises, "Laboratórios de análises clínicas"],
      [nImagem, "Centros de diagnóstico por imagem"],
      [cons.length, "Clínicas e consultórios"],
      [lista.length, "Prestadores no total"]
    ]);

    if (hosp.length) {
      rel.titulo("Principais referências hospitalares",
        "Os hospitais de maior cobertura na sua rede. A marca ACRED. indica " +
        "programa de acreditação reconhecido pela operadora.");
      rel.referencias(hosp.slice(0, 10));
    }

    function secao(nome, itens, comEsp) {
      if (!itens.length) return;
      /* Antes toda secao abria pagina nova - uma secao de 3 prestadores
         gastava uma folha inteira. Agora so vira a pagina se o que sobrou
         nao comporta o cabecalho e algumas linhas. */
      rel.espaco(Math.min(110, 46 + itens.length * 16));
      rel.faixa(nome, itens.length);
      rel.tabela(itens, comEsp !== false, produtos);
    }

    secao("Hospitais para internação", hosp);
    secao("Pronto-socorro 24 horas", ps);
    secao("Pronto atendimento", pa);

    var nomesGrupo = ["Análises clínicas e patologia", "Diagnóstico por imagem",
                      "Exames funcionais", "Endoscopia e procedimentos",
                      "Oncologia", "Outros exames"];
    var temExame = nomesGrupo.some(function (g) {
      return porGrupo[g] && Object.keys(porGrupo[g]).length;
    });
    if (temExame) {
      rel.novaPagina();
      rel.titulo("Exames e diagnóstico",
        "Separados por natureza do exame. Para exame eletivo, procure os " +
        "centros de diagnóstico e laboratórios listados primeiro em cada " +
        "grupo. Os hospitais aparecem em bloco à parte: eles realizam esses " +
        "exames, mas em regra para pacientes internados e em urgência — " +
        "confirme a agenda ambulatorial antes de encaminhar.");
      nomesGrupo.forEach(function (g) {
        var itens = Object.keys(porGrupo[g] || {}).map(function (k) {
          return porGrupo[g][k];
        }).sort(ordenarPorNome);
        if (!itens.length) return;
        var centros = itens.filter(function (p) { return !ehHospital(p); });
        var hospitais = itens.filter(ehHospital);
        if (centros.length) {
          rel.faixa(g, centros.length);
          rel.tabela(centros, true, produtos);
        }
        if (hospitais.length) {
          rel.faixa(g + " — em hospitais: pronto-socorro e internação, " +
                    "não para exame eletivo", hospitais.length);
          rel.tabela(hospitais, true, produtos);
        }
      });
    }

    secao("Hemodiálise", hemo);
    secao("TEA — transtorno do espectro autista", tea);
    secao("Telemedicina", tele);

    if (cons.length) {
      rel.novaPagina();
      rel.faixa("Clínicas e consultórios", cons.length);
      var porEsp = {};
      cons.forEach(function (p) {
        p.esp.forEach(function (e) {
          (porEsp[e] = porEsp[e] || []).push(p);
        });
      });
      Object.keys(porEsp).sort(function (a, b) {
        return semAcento(a) < semAcento(b) ? -1 : 1;
      }).forEach(function (e) {
        rel.espaco(40);
        rel.pdf.texto(aux.MARGEM, rel.y, aux.capitalizar(e), "serifB", 10,
                      "#20456f");
        rel.y -= 14;
        rel.tabela(porEsp[e].sort(ordenarPorNome), false, produtos);
      });
    }

    rel.novaPagina();
    rel.titulo("Antes de contratar");
    var aviso = "Cada plano deste material representa uma rede: enfermaria e " +
      "apartamento compartilham a mesma rede credenciada, e a linha de Adesão " +
      "usa a rede do PME/PJ correspondente. " +
      "A rede credenciada é definida e alterada exclusivamente pela " +
      "operadora. Este documento é o retrato do que a busca avançada oficial " +
      "da Amil apresentava na data da capa e não substitui a consulta ao " +
      "portal. Confirme no portal da Amil antes de contratar.";
    rel.pdf.quebrar(aviso, "sans", 9, aux.UTIL * 0.62).forEach(function (l) {
      rel.pdf.texto(aux.MARGEM, rel.y, l, "sans", 9, aux.TINTA);
      rel.y -= 13;
    });
    rel.y -= 18;
    rel.pdf.texto(aux.MARGEM, rel.y, corretor.nome, "sansB", 9,
                  aux.NAVY);
    rel.y -= 13;
    [corretor.corretora, corretor.email, corretor.fone]
      .forEach(function (t) {
        rel.pdf.texto(aux.MARGEM, rel.y, t, "sans", 9, aux.CINZA);
        rel.y -= 13;
      });

    var bytes = rel.pdf.gerar();
    var nome = "Rede Amil " +
               (comparativo
                 ? (nomes.length <= 3 ? nomes.join(" x ")
                                      : nomes.length + " planos")
                 : nomes[0]) +
               " - " + rotuloCidade + ".pdf";
    entregarBinario(nome.replace(/\//g, "-"), bytes);
  }

  function entregarBinario(nome, bytes) {
    salvar(nome, bytes.buffer, "application/pdf");
  }

  /* Zera todo filtro escolhido. Sai daqui e do botao Limpar - trocar de
     estado precisa zerar igual, senao sobra "Curitiba" marcado em SC. */
  function limparTudo() {
    $("q").value = "";
    estado.f = { cid: {}, cidr: {}, cat: {}, esp: {}, bairro: {} };
    estado.produtos = {};
    estado.perto = null;
    estado.teto = POR_VEZ;
    $("perto").classList.remove("tem");
    $("perto").querySelector(".resumo").textContent = "Não ordenar";
    CAMPOS.forEach(pintarSeletor);
  }

  /* Carrega o estado ativo. Os dados dos dois estados ja vieram no arquivo;
     aqui so trocamos qual deles a pagina esta mostrando. */
  function carregar() {
    $("dataColeta").textContent = "atualizado em " + D.gerado_em;
    var recorte = $("recorteUf");
    recorte.textContent = D.nota || "";
    recorte.hidden = !D.nota;
    $("tituloEstado").textContent = D.estado || D.uf;
    var cidades = {};
    D.prestadores.forEach(function (p) {
      (p.cid || []).forEach(function (c) { cidades[c] = 1; });
    });
    opcoes.cid = Object.keys(cidades).sort(function (a, b) {
      return semAcento(a) < semAcento(b) ? -1 : 1;
    });
    mapearEspecialidadesDeExame();
    montarSelects();
    limparTudo();
    dependentes();
    montarProdutos();
    desenhar();
    if (!$("panorama").hidden) montarPanorama();
  }

  function montarEstados() {
    var ordem = window.ORDEM_UF || [];
    if (ordem.length < 2) return;            // um estado so: nem mostra
    var alvo = $("estados");
    alvo.hidden = false;
    ordem.forEach(function (uf) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = (window.DADOS_UF[uf].estado || uf);
      b.classList.toggle("ativo", uf === D.uf);
      b.onclick = function () {
        if (uf === D.uf) return;
        D = window.DADOS = window.DADOS_UF[uf];
        Array.prototype.forEach.call(alvo.children, function (o) {
          o.classList.toggle("ativo", o === b);
        });
        carregar();
        window.scrollTo(0, 0);
      };
      alvo.appendChild(b);
    });
  }

  montarEstados();
  carregar();

  corretor = lerCorretor();
  pintarCorretor();

  $("q").oninput = desenhar;

  // abre e fecha as listas de escolha múltipla
  Array.prototype.forEach.call(document.querySelectorAll(".seletor"),
    function (b) {
      b.onclick = function (e) {
        e.stopPropagation();
        var campo = b.dataset.campo;
        if (estado.aberto === campo) { fecharLista(); return; }
        abrirLista(campo);
      };
    });
  $("listaFlutuante").onclick = function (e) { e.stopPropagation(); };
  $("opcoesLista").onchange = function (e) {
    if (!e.target) return;
    if (e.target.type === "radio") {
      var chave = e.target.value;
      estado.perto = chave
        ? { chave: chave, bairro: chave.split("|")[0],
            cidade: chave.split("|")[1],
            xy: [D.centros[chave][0], D.centros[chave][1]] }
        : null;
      $("perto").classList.toggle("tem", !!estado.perto);
      $("perto").querySelector(".resumo").textContent =
        estado.perto ? estado.perto.bairro : "Não ordenar";
      desenharLista();
      desenhar();
      return;
    }
    if (e.target.type === "checkbox") {
      alternar(estado.aberto, e.target.value);
      desenharLista();
    }
  };
  $("perto").onclick = function (e) {
    e.stopPropagation();
    if (estado.aberto === "perto") { fecharLista(); return; }
    abrirPerto();
  };
  $("buscaLista").oninput = function () { desenharLista(); posicionar(); };
  $("fecharX").onclick = fecharLista;
  $("prontoLista").onclick = fecharLista;
  $("limparLista").onclick = function () {
    estado.f[estado.aberto] = {};
    if (estado.aberto === "cid") dependentes();
    pintarSeletor(estado.aberto);
    marcasEscolhidas();
    desenharLista();
    desenhar();
  };
  $("escolhidos").onclick = function (e) {
    var b = e.target.closest("button[data-campo]");
    if (b) alternar(b.dataset.campo, b.dataset.valor);
  };
  document.addEventListener("click", function () {
    if (estado.aberto) fecharLista();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && estado.aberto) fecharLista();
  });
  window.addEventListener("resize", posicionar);
  window.addEventListener("scroll", posicionar, true);
  $("modo").onclick = function (e) {
    var m = e.target.dataset.m;
    if (!m) return;
    estado.modo = m;
    Array.prototype.forEach.call($("modo").children, function (s) {
      s.classList.toggle("ativo", s === e.target);
    });
    desenhar();
  };
  $("limpar").onclick = function () {
    limparTudo();
    Array.prototype.forEach.call(document.querySelectorAll(".ficha"), function (b) {
      b.classList.remove("ativa");
      b.setAttribute("aria-pressed", "false");
    });
    dependentes();
    desenhar();
  };
  $("abrirCorretor").onclick = abrirCorretor;
  $("fecharCorretor").onclick = function () {
    $("painelCorretor").hidden = true;
  };
  $("painelCorretor").onclick = function (e) {
    if (e.target === $("painelCorretor")) $("painelCorretor").hidden = true;
  };
  $("salvarCorretor").onclick = function () {
    gravarCorretor({
      nome: $("cNome").value.trim(),
      corretora: CORRETORA_FIXA,
      email: $("cEmail").value.trim(),
      fone: $("cFone").value.trim()
    });
    $("painelCorretor").hidden = true;
    avisar("Pronto — os PDFs passam a sair com <b>" +
           esc(corretor.nome || corretor.corretora) + "</b>.");
  };
  $("restaurarCorretor").onclick = function () {
    try { localStorage.removeItem(CHAVE_CORRETOR); } catch (e) {}
    corretor = corretorPadrao();
    pintarCorretor();
    abrirCorretor();
  };
  $("limparSel").onclick = function () {
    estado.produtos = {};
    Array.prototype.forEach.call(document.querySelectorAll(".ficha"),
      function (b) {
        b.classList.remove("ativa");
        b.setAttribute("aria-pressed", "false");
      });
    desenhar();
  };
  $("pdfEntre").onclick = gerarPDFEntre;
  $("planoA").onchange = montarEntre;
  $("planoB").onchange = montarEntre;
  $("abas").onclick = function (e) {
    var qual = e.target.dataset && e.target.dataset.aba;
    if (qual) trocarAba(qual);
  };
  $("csv").onclick = baixarCsv;
  $("pdf").onclick = gerarPDF;
  desenhar();
})();
