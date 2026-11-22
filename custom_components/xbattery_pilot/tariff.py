"""Períodos horários EDA — BTN tri-horário, ciclo semanal (Açores)."""

from __future__ import annotations

from datetime import datetime, time

VAZIO = "vazio"
CHEIAS = "cheias"
PONTA = "ponta"

# Fonte: ERSE, "Períodos horários na energia elétrica em Portugal" (secção 3.1)
# Verão: junho a outubro | Inverno: novembro a maio
# Sábado: sem ponta (fora de vazio = cheias) | Domingo: vazio todo o dia
SCHEDULE: dict[str, dict[str, list[tuple[time, str]]]] = {
    "inverno": {
        "uteis": [
            (time(0, 0), VAZIO),
            (time(7, 0), CHEIAS),
            (time(18, 30), PONTA),
            (time(21, 30), CHEIAS),
        ],
        "sabado": [
            (time(0, 0), VAZIO),
            (time(11, 30), CHEIAS),
            (time(13, 30), VAZIO),
            (time(18, 0), CHEIAS),
            (time(23, 0), VAZIO),
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
        "sabado": [
            (time(0, 0), VAZIO),
            (time(11, 0), CHEIAS),
            (time(14, 30), VAZIO),
            (time(19, 30), CHEIAS),
            (time(23, 0), VAZIO),
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
