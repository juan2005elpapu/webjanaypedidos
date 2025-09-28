"""Funciones auxiliares para la integración con la pasarela Wompi."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib import error, request


class WompiAPIError(Exception):
    """Error genérico al comunicarse con los servicios de Wompi."""


@dataclass
class WompiEnvironment:
    """Representa la configuración base según el entorno."""

    api_url: str
    widget_js_url: str
    widget_js_urls: Tuple[str, ...]


def get_wompi_base_url(environment: str) -> WompiEnvironment:
    """Obtiene las URLs base para el entorno configurado."""

    environment = (environment or 'test').lower()
    if environment == 'production':
        return WompiEnvironment(
            api_url='https://production.wompi.co',
            widget_js_url='https://checkout.wompi.co/widget.js',
            widget_js_urls=(
                'https://checkout.wompi.co/widget.js',
                'https://cdn.wompi.co/widget.js',
            ),
        )
    return WompiEnvironment(
        api_url='https://sandbox.wompi.co',
        widget_js_url='https://checkout.wompi.co/widget.js',
        widget_js_urls=(
            'https://checkout.wompi.co/widget.js',
            'https://cdn.wompi.co/widget.js',
        ),
    )


def _perform_get(url: str, *, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Realiza un GET simple y devuelve el JSON de respuesta."""

    req = request.Request(url, headers=headers or {})
    try:
        with request.urlopen(req, timeout=15) as response:
            payload = response.read().decode('utf-8')
    except error.HTTPError as exc:  # pragma: no cover - controlamos el mensaje
        raise WompiAPIError(
            f"Wompi respondió con un error HTTP {exc.code}: {exc.reason}"
        ) from exc
    except error.URLError as exc:  # pragma: no cover - dependerá de la red
        raise WompiAPIError('No fue posible conectarse con Wompi. Intenta nuevamente.') from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - respuesta inesperada
        raise WompiAPIError('La respuesta de Wompi no es válida.') from exc


def get_acceptance_information(public_key: str, environment: str) -> Dict[str, Any]:
    """Obtiene información de aceptación (términos y token) para el comercio."""

    public_key = (public_key or '').strip()
    if not public_key:
        raise WompiAPIError('No se configuró la llave pública de Wompi.')

    env = get_wompi_base_url(environment)
    data = _perform_get(f"{env.api_url}/v1/merchants/{public_key}")
    return data.get('data', {})


def get_transaction_information(
    transaction_id: str,
    environment: str,
    *,
    public_key: Optional[str] = None,
    private_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Consulta el estado de una transacción específica."""

    transaction_id = (transaction_id or '').strip()
    if not transaction_id:
        raise WompiAPIError('No se proporcionó el identificador de la transacción.')

    env = get_wompi_base_url(environment)
    headers: Dict[str, str] = {}
    token = (private_key or public_key or '').strip()
    if token:
        headers['Authorization'] = f'Bearer {token}'

    data = _perform_get(f"{env.api_url}/v1/transactions/{transaction_id}", headers=headers)
    return data.get('data', {})


__all__ = [
    'WompiAPIError',
    'get_acceptance_information',
    'get_transaction_information',
    'get_wompi_base_url',
]


def split_phone_number(
    phone_number: str,
    *,
    default_prefix: str = '57',
) -> Tuple[Optional[str], Optional[str]]:
    """Divide un teléfono en prefijo y número para el widget de Wompi."""

    digits = re.sub(r'\D+', '', phone_number or '')
    if not digits:
        return None, None

    # Eliminar prefijos internacionales comunes "00"
    if digits.startswith('00'):
        digits = digits[2:]

    if not digits:
        return None, None

    # La integración en Colombia usa "57" como prefijo internacional
    default_prefix = re.sub(r'\D+', '', default_prefix or '') or '57'

    prefix: Optional[str] = None
    local_number: Optional[str] = None

    if digits.startswith('57') and len(digits) > 2:
        prefix = '57'
        local_number = digits[2:]
    elif digits.startswith(default_prefix) and len(digits) > len(default_prefix):
        prefix = default_prefix
        local_number = digits[len(default_prefix):]
    else:
        prefix = default_prefix
        local_number = digits[-10:] if len(digits) > 10 else digits

    if not local_number:
        return None, None

    # Asegurar que no existan ceros a la izquierda innecesarios
    local_number = local_number.lstrip('0') or local_number

    if len(local_number) < 6:  # Wompi requiere al menos 6 dígitos significativos
        return None, None

    return prefix, local_number


__all__.append('split_phone_number')
