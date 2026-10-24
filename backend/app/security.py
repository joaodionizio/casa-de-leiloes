"""Senha (Argon2id) e token de sessão (JWT HS256) da Story 2.2.

Nenhuma senha, hash ou token é logado, devolvido ou posto em mensagem de exceção.
O relógio daqui é o da aplicação em UTC: o AD-6 vale para lance e fechamento, não
para a expiração da sessão.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

JWT_ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["sub", "role", "iat", "exp"]
SESSION_LIFETIME = timedelta(hours=8)
SESSION_MAX_AGE_SECONDS = int(SESSION_LIFETIME.total_seconds())

# Parâmetros padrão da biblioteca (Argon2id), uma instância por processo.
_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    """`False` só para senha errada; hash corrompido propaga (500 genérico)."""
    try:
        return _hasher.verify(password_hash, plain)
    except VerifyMismatchError:
        return False


@lru_cache
def _reference_hash() -> str:
    # Hash de uma senha aleatória descartada: ninguém conhece a senha dele.
    return _hasher.hash(secrets.token_urlsafe(32))


def verify_reference_password(plain: str) -> None:
    """Gasta uma verificação Argon2 quando o e-mail não existe, para o tempo de
    resposta ser comparável. O resultado é sempre ignorado."""
    verify_password(_reference_hash(), plain)


def issue_token(user_id: uuid.UUID, role: str, secret: str) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + SESSION_LIFETIME,
    }
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Levanta `jwt.InvalidTokenError` para qualquer token inválido: assinatura,
    algoritmo diferente de HS256 (inclusive `none`), expirado, `iat` futuro,
    malformado ou sem alguma claim obrigatória. Tolerância de relógio zero."""
    return jwt.decode(
        token,
        secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": REQUIRED_CLAIMS},
        leeway=0,
    )
