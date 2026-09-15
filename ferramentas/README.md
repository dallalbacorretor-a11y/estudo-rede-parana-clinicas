# Como a rede é levantada e a página é gerada

Tudo aqui é Python puro (só `openpyxl`, `reportlab` e `pymupdf` para os arquivos
de escritório). A rede vem da **API pública da plataforma Mosia / Mobile Saúde**,
que é o que o buscador do site da Paraná Clínicas usa por baixo.

## A ordem das coisas

```
harvest2.py    varre a rede dos 3 planos, cidade a cidade      -> dados/rede2_<cod>.json
detalhes.py    detalhe de cada prestador (CNPJ, coordenada…)   -> dados/detalhes.json
extras.py      especialidades completas + corpo clínico        -> dados/esp_full.json
                                                                  dados/corpo_clinico.json
build_dados.py junta tudo no formato da página                 -> dados/dados_pc.json
montar_site.py monta o index.html publicado                    -> ../index.html
```

E, para os arquivos de escritório (independentes da página):

```
build_comp.py       concilia os 3 planos (usado pelos de baixo)
export_xlsx.py      uma planilha por plano          -> 01 - REDE CREDENCIADA/…
build_comp_xlsx.py  comparativo + RESUMO.md         -> 02 - COMPARATIVOS DE REDE/
build_html.py       comparativo estático (template.html)
build_pdf.py        os dois PDFs de apresentação
```

Rodar tudo do zero leva cerca de **2 horas**, quase todo o tempo em espera da API
(a operadora responde em ~3-7 s por chamada). Os JSONs de `dados/` estão versionados
justamente para não precisar refazer a coleta a cada ajuste de layout: apague só o
que quiser recoletar. Todos os coletores são incrementais — releem o JSON existente
e buscam apenas o que falta, então dá para interromper e retomar.

## A API, em resumo

- Base pública: `https://api.mosiaomnichannel.com.br/publico/omni/rede_credenciada/v1/gan/`
- `bundle: br.com.mobilesaude.paranaclinicas` · `idOperadora: 33`
- Tudo POST com JSON; sem login.

As rotas e os parâmetros saem de dois `setup` (ver `api.py` e o histórico do
repositório). O que vale lembrar:

- **`idPlano` é o `codigo_legado`**, não o `id` interno — com o `id` a API responde 404.
  Hoje: `236` = Paraná 400 QP, `237` = Paraná 600 QC, `234` = Paraná CIM QC.
- `idCidade` é o código IBGE; string vazia significa "todas".
- **`buscaRede` corta em 200 linhas e não pagina.** Por isso a varredura é por
  cidade × tipo de prestador, e `harvest2.py` quebra por bairro se ainda assim
  estourar 200.
- `espagr:"S"` agrupa as especialidades numa linha por prestador/endereço — é o
  que o site faz. Nesse modo a lista vem cortada com `[...]` em alguns casos;
  quem resolve é `listaEspecialidadesPrestador`, que **exige `cpfCnpj`** e devolve
  a lista inteira, endereço por endereço.

### O que a operadora não publica

Levantado e confirmado vazio — não adianta tentar de novo sem aviso deles:

- `prestador/horarioAtendimento` → 404 em todos os prestadores
- `prestador/regimesAtendimento` → erro 500 (a tabela não existe no servidor deles)
- campo `acreditacoes` → vazio nos 463 prestadores
- campo `atend_24_horas` → vazio em todos

## A página

`montar_site.py` **não escreve a página do zero**: ela reaproveita o app que já
roda em [rede-amil](https://dallalbacorretor-a11y.github.io/rede-amil/) (mesma
casca, mesmas abas, mesmo gerador de PDF) e troca a paleta, os textos e os dados.

Os arquivos de origem (`amil_head.html`, `amil_app.js`, `amil_lib.js`) são
extraídos do HTML publicado daquele site — veja o topo de `montar_site.py`.
Toda substituição passa pela função `troca()`, que **estoura se o texto original
não existir mais**. Isso é de propósito: se o site da Amil mudar, a montagem falha
alto em vez de gerar uma página silenciosamente quebrada.

## Cores

A paleta dos planos foi validada com o script de contraste/daltonismo (OKLab):
passa nos três tipos de CVD e no contraste contra o fundo, no modo claro e no
escuro. **Não troque as cores no olho** — se precisar mexer, revalide, porque três
tons de vermelho (o instinto natural aqui) reprovam: um leitor deuteranope não
separaria os planos.

| Plano | claro | escuro |
|---|---|---|
| Paraná 400 QP | `#a80a32` | `#d1445f` |
| Paraná 600 QC | `#6b3f8f` | `#9b6ec4` |
| Paraná CIM QC | `#b5761b` | `#b08529` |

O vermelho `#8e0e28` é a marca da operadora (cabeçalho, capa do PDF) e o dourado
`#9a7513` é o acento da Mazza Broker — o mesmo do material da Amil.
