"""Períodos horários EDA — BTN tri-horário, ciclo semanal (Açores)."""

from __future__ import annotations

from datetime import datetime, time

VAZIO = "vazio"
CHEIAS = "cheias"
PONTA = "ponta"

# Verão: junho a outubro | Inverno: novembro a maio
SCHEDULE: dict[str, dict[str, list[tuple[time, str]]]] = {
    "inverno": {
        "uteis": [
            (time(0, 0), VAZIO),
            (time(7, 0), CHEIAS),
            (time(18, 30), PONTA),
            (time(21, 30), CHEIAS),
        ],
        # confirmar sábado
        "sabado": [
            (time(0, 0), VAZIO),
            (time(9, 30), CHEIAS),
            (time(13, 0), VAZIO),
            (time(18, 30), CHEIAS),
            (time(22, 0), VAZIO),
        ],
        "domingo": [(time(0, 0), VAZIO)],
    },
    "verao": {
        "uteis": [
            (time(0, 0), VAZIO),
            (time(7, 0), CHEIAS),
            (time(10, 30), PONTA),
            (time(15, 30), CHEIAS),
        ],
        # confirmar sábado
        "sabado": [
            (time(0, 0), VAZIO),
            (time(9, 0), CHEIAS),
            (time(14, 0), VAZIO),
            (time(20, 0), CHEIAS),
            (time(22, 0), VAZIO),
        ],
        "domingo": [(time(0, 0), VAZIO)],
    },
}


def period_at(t: datetime) -> str:
    """Devolve o período tarifário num instante (hora local)."""
    season = "verao" if 6 <= t.month <= 10 else "inverno"
    wd = t.weekday()
    day = "uteis" if wd < 5 else ("sabado" if wd == 5 else "domingo")
    current = VAZIO
    for start, period in SCHEDULE[season][day]:
        if t.time() >= start:
            current = period
        else:
            break
    return current
