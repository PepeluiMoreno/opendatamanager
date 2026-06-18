"""
Throttle proactivo por host — cortesía que evita el baneo en vez de reaccionar a él.

`base._request` ya sabe reaccionar a 429/503 (Retry-After + backoff). Pero hay
fuentes que NO devuelven 429: simplemente vetan la IP cuando se supera un cupo.
El caso canónico es la Sede Electrónica del Catastro, cuyos servicios libres
limitan a 3.600 peticiones/hora por IP y, al superarlo, deniegan el servicio
durante CUATRO horas. Contra eso no vale reaccionar: hay que no llegar nunca.

Este módulo aporta un limitador process-wide, por host (netloc), con dos rejas:

  1. Intervalo mínimo entre peticiones  (de `rate_limit_per_second` o `request_delay_ms`).
  2. Ventana deslizante horaria          (de `max_per_hour`) — la reja que evita el baneo.

Es por HOST, no por instancia: varios workers (num_workers>1) e incluso varios
Resources distintos que ataquen el mismo host comparten el mismo presupuesto,
que es exactamente como cuenta el límite por IP del lado servidor. Thread-safe.

Opt-in puro: si una especie no fija ninguna de las tres claves, no se instancia
limitador y el comportamiento es idéntico al de siempre (coste cero).
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Dict, Optional
from urllib.parse import urlparse


class _HostLimiter:
    """Limitador de un único host: intervalo mínimo + tope horario deslizante."""

    def __init__(self, min_interval_s: float = 0.0, max_per_hour: int = 0):
        self._min_interval = max(0.0, float(min_interval_s))
        self._max_per_hour = max(0, int(max_per_hour))
        self._lock = threading.Lock()
        self._last_ts: float = 0.0
        # timestamps de las peticiones de la última hora (para la ventana deslizante)
        self._window: deque[float] = deque()

    def acquire(self) -> float:
        """Bloquea hasta que esté permitido emitir. Devuelve los segundos dormidos."""
        slept = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                wait = 0.0

                # Reja 1: intervalo mínimo desde la última petición.
                if self._min_interval > 0.0:
                    gap = now - self._last_ts
                    if gap < self._min_interval:
                        wait = max(wait, self._min_interval - gap)

                # Reja 2: ventana horaria. Purga lo que ya salió de la hora y, si
                # seguimos en el tope, espera a que el más antiguo cumpla 3600s.
                if self._max_per_hour > 0:
                    horizon = now - 3600.0
                    while self._window and self._window[0] <= horizon:
                        self._window.popleft()
                    if len(self._window) >= self._max_per_hour:
                        wait = max(wait, (self._window[0] + 3600.0) - now)

                if wait <= 0.0:
                    # Permitido: registramos y salimos con el lock aún tomado.
                    stamp = time.monotonic()
                    self._last_ts = stamp
                    if self._max_per_hour > 0:
                        self._window.append(stamp)
                    return slept

            # Dormimos FUERA del lock para no bloquear a otros workers del mismo host.
            time.sleep(wait)
            slept += wait


class ThrottleRegistry:
    """Registro process-wide de limitadores por host."""

    _lock = threading.Lock()
    _limiters: Dict[str, _HostLimiter] = {}

    @classmethod
    def for_host(cls, host: str, min_interval_s: float, max_per_hour: int) -> _HostLimiter:
        with cls._lock:
            lim = cls._limiters.get(host)
            if lim is None:
                lim = _HostLimiter(min_interval_s, max_per_hour)
                cls._limiters[host] = lim
            else:
                # Endurecer si una especie pide un límite más estricto que el ya fijado.
                if min_interval_s > lim._min_interval:
                    lim._min_interval = float(min_interval_s)
                if max_per_hour and (lim._max_per_hour == 0 or max_per_hour < lim._max_per_hour):
                    lim._max_per_hour = int(max_per_hour)
            return lim

    @classmethod
    def reset(cls) -> None:
        """Limpia el estado — sólo para tests."""
        with cls._lock:
            cls._limiters.clear()


def params_to_throttle(params: Dict) -> Optional[tuple[float, int]]:
    """Traduce los params de una especie a (min_interval_s, max_per_hour).

    Devuelve None si no hay nada que limitar (opt-in). Acepta, por orden de
    preferencia para el intervalo: `request_delay_ms` > `rate_limit_per_second`.
    """
    min_interval = 0.0
    delay_ms = params.get("request_delay_ms")
    if delay_ms not in (None, ""):
        try:
            min_interval = max(min_interval, float(delay_ms) / 1000.0)
        except (TypeError, ValueError):
            pass
    rps = params.get("rate_limit_per_second")
    if rps not in (None, ""):
        try:
            rps = float(rps)
            if rps > 0:
                min_interval = max(min_interval, 1.0 / rps)
        except (TypeError, ValueError):
            pass

    max_per_hour = 0
    mph = params.get("max_per_hour")
    if mph not in (None, ""):
        try:
            max_per_hour = int(mph)
        except (TypeError, ValueError):
            pass

    if min_interval <= 0.0 and max_per_hour <= 0:
        return None
    return (min_interval, max_per_hour)


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower() or url
