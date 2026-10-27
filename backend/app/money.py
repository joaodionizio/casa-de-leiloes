"""Contrato monetário único (AD-3, Story 3.1 P3).

Sem dependência de outro módulo do app: lotes, carteira e, mais tarde, lances
importam daqui. O dinheiro é sempre um inteiro de centavos, nunca `float`.
"""

from typing import Annotated

from pydantic import Field, StrictInt

# Number.MAX_SAFE_INTEGER (2.4, D3): o maior inteiro que o consumidor JavaScript
# representa sem perda. Limite técnico, não comercial; a mesma faixa vale na API, no
# serviço e nas CHECKs do banco (A4). As migrations escrevem o literal, sem importar
# este módulo, e os testes provam que os dois são iguais.
MAX_CENTS = 9_007_199_254_740_991

# Valor positivo em centavos: lance inicial, incremento e depósito.
Cents = Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]
