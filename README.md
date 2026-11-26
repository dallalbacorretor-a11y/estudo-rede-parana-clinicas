# Estudo de Rede Credenciada — Paraná Clínicas

Levantamento da rede credenciada da **Paraná Clínicas** para os três planos comercializados,
consultado em **26/11/2026** na busca oficial de rede credenciada da operadora
(<https://www.paranaclinicas.com.br/beneficiario/rede-credenciada/>). A consulta anterior era
de 12/09/2026.

### 👉 [Consultar a rede](https://dallalbacorretor-a11y.github.io/estudo-rede-parana-clinicas/)

Página interativa, no mesmo padrão da [rede Amil](https://dallalbacorretor-a11y.github.io/rede-amil/):
visão geral com mapa e gráficos, comparação entre dois planos, rede completa com busca
por prestador/CNPJ e filtros por cidade, categoria, especialidade e bairro, além de
exportação em CSV e **geração de PDF** assinado pelo corretor.

> **A rede credenciada é definida e alterada exclusivamente pela operadora.**
> Este material tem caráter informativo e reflete a consulta feita na data acima.
> **Confirme sempre no portal da Paraná Clínicas antes de contratar.**

## Planos analisados

| Plano | Registro ANS | Contratação | Prestadores | Por direcionamento (D) | Cidades |
|---|---|---|---|---|---|
| Paraná 400 AHO QP COPART SR | 507887263 | Coletivo empresarial | 463 | +3 por direcionamento | 17 |
| Paraná 600 AHO QC COPART SR | 507885267 | Coletivo empresarial | 555 | — | 17 |
| Paraná CIM AHO QC COPART SR | 507888261 | Coletivo empresarial | 235 | +4 por direcionamento | 10 |

Rede consolidada (união dos três): **562 prestadores**. A divisão por categoria e por
cidade de cada plano está no [RESUMO](01%20-%20REDE%20CREDENCIADA/Paran%C3%A1%20Cl%C3%ADnicas/RESUMO.md).

Contagem por endereço de atendimento: cada prestador conta uma vez em cada endereço
(um laboratório com 3 unidades conta 3). Os hospitais marcados com **D** (direcionamento
interno, informação do corretor, não da busca oficial) aparecem na lista, mas ficam fora
do total do plano e são contados à parte: Erasto Gaertner, Erastinho e Pequeno Príncipe
no 400 e no CIM, e Novaclínica no CIM.

`QC` = quarto coletivo (enfermaria) · `QP` = quarto privativo (apartamento).
As variantes de acomodação do mesmo produto compartilham a mesma rede, por isso os planos
Paraná 400 AHO QC (ANS 507886265) e Paraná 600 AHO QP (ANS 507889260) não foram tabulados à parte.

## Destaques

- O **Paraná 600** é o de rede mais ampla: tem 97 prestadores que só ele tem na busca
  oficial, entre eles Nossa Senhora das Graças, Vita Batel, Vita Curitiba, Instituto da
  Criança, IPO, Nossa Senhora do Pilar e Porto Seguro Psiquiátrico (Erasto Gaertner,
  Erastinho e Pequeno Príncipe também estão nessa conta: o 400 e o CIM chegam a eles
  só por direcionamento).
- **229 prestadores estão nos três planos** — é o piso comum da rede.
- O **Paraná CIM** é o mais restrito: 10 cidades contra 17, e quase toda a sua rede é compartilhada.
- As unidades próprias **CIM** (Centros Integrados de Medicina — Água Verde, CIC,
  São José dos Pinhais e Araucária) aparecem como tipo de prestador separado, com os
  profissionais listados individualmente pela operadora.

## Conteúdo

```
index.html                                    a página de consulta publicada acima

01 - REDE CREDENCIADA/Paraná Clínicas/
    REDE PARANA 400 AHO QP COPART SR.xlsx    rede do plano (abas Rede + Resumo)
    REDE PARANA 600 AHO QC COPART SR.xlsx
    REDE PARANA CIM AHO QC COPART SR.xlsx
    RESUMO.md                                 números por plano, categoria e cidade

02 - COMPARATIVOS DE REDE/
    COMPARATIVO ... - CLIENTES (Principais).pdf   estabelecimentos (hospitais, CIM, clínicas, labs)
    COMPARATIVO ... - Apresentacao.pdf            rede completa
    COMPARATIVO ... .xlsx                          555 linhas, uma coluna por plano
    COMPARATIVO ... .html                          versão interativa, com busca e filtros

03 - MATERIAIS ORIGINAIS (PDFs das operadoras)/
    (vazio — a Paraná Clínicas não publica lista de rede por linha de plano em PDF,
     apenas o buscador online)
```

Nos comparativos, ✔ indica que o prestador consta na rede daquele plano e **D**, que o
acesso é por direcionamento interno, com uma cor por plano — a mesma na página, nas
planilhas, no comparativo HTML e nos PDFs:
<span>400 QP</span> vermelho (`#a80a32`) · <span>600 QC</span> roxo (`#6b3f8f`) ·
<span>CIM QC</span> âmbar (`#b5761b`).

## Contato

**Mazza Broker** — Alan Vinicius Dall Alba
(41) 99547-6715 · alan.vinicius@mazzabroker.com.br
