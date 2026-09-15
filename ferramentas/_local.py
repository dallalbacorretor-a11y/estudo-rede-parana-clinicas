# -*- coding: utf-8 -*-
"""Caminhos fixos, para os scripts rodarem de qualquer diretorio.

Importar isto antes de abrir qualquer arquivo: ele leva o processo para a pasta
ferramentas/, entao todo caminho relativo ("dados/x.json") passa a valer aqui
dentro, e RAIZ aponta para a pasta do estudo.
"""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DADOS = os.path.join(AQUI, "dados")
BASE = os.path.join(AQUI, "base")
os.chdir(AQUI)
os.makedirs(DADOS, exist_ok=True)
