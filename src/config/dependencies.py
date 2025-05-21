import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import HTTPException, status
from src.config.settings import Settings, get_settings
from src.security.interfaces import JWTAuthManagerInterface


class JWTAuthManager(JWTAuthManagerInterface):
    def __init__(self, settings: Settings):
        self._access_secret = settings.SECRET_KEY_ACCESS
        self._refresh_secret = settings.SECRET_KEY_REFRESH
        self._algorithm = settings.JWT_SIGNING_ALGORITHM
        self._access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def _create_token(self, data: dict, secret: str, expires_delta: timedelta) -> str:
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = data.copy()
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, secret, algorithm=self._algorithm)

    def create_access_token(
        self, data: Dict[str, str], expires_delta: Optional[timedelta] = None
    ) -> str:
        delta = expires_delta or timedelta(minutes=self._access_token_expire_minutes)
        return self._create_token(data, self._access_secret, delta)

    def create_refresh_token(
        self, data: Dict[str, str], expires_delta: Optional[timedelta] = None
    ) -> str:
        delta = expires_delta or timedelta(days=self._refresh_token_expire_days)
        return self._create_token(data, self._refresh_secret, delta)

    def decode_access_token(self, token: str) -> Dict:
        return self._decode_token(token, self._access_secret)

    def decode_refresh_token(self, token: str) -> Dict:
        return self._decode_token(token, self._refresh_secret)

    def verify_access_token_or_raise(self, token: str) -> None:
        self.decode_access_token(token)

    def verify_refresh_token_or_raise(self, token: str) -> None:
        self.decode_refresh_token(token)

    def _decode_token(self, token: str, secret: str) -> Dict:
        try:
            return jwt.decode(token, secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )


def get_jwt_manager() -> JWTAuthManagerInterface:
    return JWTAuthManager(get_settings())
