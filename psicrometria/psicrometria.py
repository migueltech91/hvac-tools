"""Calculadora psicrométrica (aire húmedo).

A partir de la temperatura de bulbo seco y la humedad relativa (o el bulbo
húmedo) calcula las propiedades del aire: humedad absoluta, punto de rocío,
bulbo húmedo, entalpía, volumen específico y densidad.

Usa las ecuaciones del ASHRAE Handbook - Fundamentals (capítulo 1,
Psicrometría): presión de saturación de Hyland-Wexler y relaciones de gas
ideal. La presión atmosférica puede indicarse directamente o calcularse a
partir de la altitud.

Uso desde la terminal:
    python psicrometria/psicrometria.py --tbs 25 --hr 50
    python psicrometria/psicrometria.py --tbs 30 --tbh 22 --altitud 1500
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

P_NIVEL_MAR_KPA = 101.325
RELACION_MOLAR = 0.621945  # masa molar agua / aire seco


def presion_por_altitud(altitud_m: float) -> float:
    """Presión atmosférica estándar (kPa) a una altitud dada (m)."""
    return P_NIVEL_MAR_KPA * (1 - 2.25577e-5 * altitud_m) ** 5.2559


def presion_saturacion(t_c: float) -> float:
    """Presión de saturación del vapor de agua (kPa), Hyland-Wexler.

    Válida de -100 °C a 200 °C (sobre hielo por debajo de 0 °C).
    """
    if not -100 <= t_c <= 200:
        raise ValueError("Temperatura fuera de rango (-100 a 200 °C)")
    t = t_c + 273.15
    if t_c < 0:
        ln_p = (
            -5.6745359e3 / t
            + 6.3925247
            - 9.6778430e-3 * t
            + 6.2215701e-7 * t**2
            + 2.0747825e-9 * t**3
            - 9.4840240e-13 * t**4
            + 4.1635019 * math.log(t)
        )
    else:
        ln_p = (
            -5.8002206e3 / t
            + 1.3914993
            - 4.8640239e-2 * t
            + 4.1764768e-5 * t**2
            - 1.4452093e-8 * t**3
            + 6.5459673 * math.log(t)
        )
    return math.exp(ln_p) / 1000.0


def humedad_absoluta_desde_pv(pv_kpa: float, p_kpa: float) -> float:
    """Relación de humedad W (kg agua / kg aire seco)."""
    return RELACION_MOLAR * pv_kpa / (p_kpa - pv_kpa)


def pv_desde_humedad_absoluta(w: float, p_kpa: float) -> float:
    return p_kpa * w / (RELACION_MOLAR + w)


def humedad_absoluta_desde_bulbo_humedo(tbs: float, tbh: float, p_kpa: float) -> float:
    """W a partir de bulbo seco y bulbo húmedo (ASHRAE, ecs. 33 y 35)."""
    ws = humedad_absoluta_desde_pv(presion_saturacion(tbh), p_kpa)
    if tbh >= 0:
        return ((2501 - 2.326 * tbh) * ws - 1.006 * (tbs - tbh)) / (
            2501 + 1.86 * tbs - 4.186 * tbh
        )
    return ((2830 - 0.24 * tbh) * ws - 1.006 * (tbs - tbh)) / (
        2830 + 1.86 * tbs - 2.1 * tbh
    )


def _biseccion(funcion, a: float, b: float, tol: float = 1e-6) -> float:
    fa = funcion(a)
    for _ in range(200):
        medio = (a + b) / 2
        fm = funcion(medio)
        if abs(b - a) < tol:
            break
        if (fm > 0) == (fa > 0):
            a, fa = medio, fm
        else:
            b = medio
    return (a + b) / 2


def punto_de_rocio(pv_kpa: float) -> float:
    """Temperatura de rocío (°C) para una presión de vapor dada."""
    if pv_kpa <= 0:
        raise ValueError("La presión de vapor debe ser positiva")
    return _biseccion(lambda t: presion_saturacion(t) - pv_kpa, -100.0, 200.0)


@dataclass
class EstadoAire:
    tbs_c: float  # temperatura de bulbo seco
    hr_pct: float  # humedad relativa
    tbh_c: float  # temperatura de bulbo húmedo
    rocio_c: float  # punto de rocío
    w_kg_kg: float  # relación de humedad
    entalpia_kj_kg: float  # por kg de aire seco
    volumen_m3_kg: float  # por kg de aire seco
    densidad_kg_m3: float  # aire húmedo
    presion_kpa: float

    @property
    def w_g_kg(self) -> float:
        return self.w_kg_kg * 1000.0


def _estado(tbs: float, w: float, p_kpa: float) -> EstadoAire:
    pv = pv_desde_humedad_absoluta(w, p_kpa)
    pws = presion_saturacion(tbs)
    hr = 100.0 * pv / pws
    if hr > 100.0 + 1e-6:
        raise ValueError("Estado imposible: el aire estaría sobresaturado")
    entalpia = 1.006 * tbs + w * (2501 + 1.86 * tbs)
    volumen = 0.287042 * (tbs + 273.15) * (1 + 1.607858 * w) / p_kpa
    rocio = punto_de_rocio(pv) if pv > 0 else float("-inf")
    tbh = _biseccion(
        lambda t: humedad_absoluta_desde_bulbo_humedo(tbs, t, p_kpa) - w,
        max(rocio, -100.0),
        tbs,
    )
    return EstadoAire(
        tbs_c=tbs,
        hr_pct=min(hr, 100.0),
        tbh_c=tbh,
        rocio_c=rocio,
        w_kg_kg=w,
        entalpia_kj_kg=entalpia,
        volumen_m3_kg=volumen,
        densidad_kg_m3=(1 + w) / volumen,
        presion_kpa=p_kpa,
    )


def estado_desde_hr(tbs: float, hr_pct: float, p_kpa: float = P_NIVEL_MAR_KPA) -> EstadoAire:
    """Propiedades del aire a partir de bulbo seco (°C) y humedad relativa (%)."""
    if not 0 <= hr_pct <= 100:
        raise ValueError("La humedad relativa debe estar entre 0 y 100 %")
    pv = hr_pct / 100.0 * presion_saturacion(tbs)
    return _estado(tbs, humedad_absoluta_desde_pv(pv, p_kpa), p_kpa)


def estado_desde_bulbo_humedo(
    tbs: float, tbh: float, p_kpa: float = P_NIVEL_MAR_KPA
) -> EstadoAire:
    """Propiedades del aire a partir de bulbo seco y bulbo húmedo (°C)."""
    if tbh > tbs:
        raise ValueError("El bulbo húmedo no puede ser mayor que el bulbo seco")
    w = humedad_absoluta_desde_bulbo_humedo(tbs, tbh, p_kpa)
    if w < 0:
        raise ValueError("Combinación de temperaturas imposible (W < 0)")
    return _estado(tbs, w, p_kpa)


def informe(e: EstadoAire) -> str:
    filas = [
        ("Bulbo seco", f"{e.tbs_c:.2f} °C"),
        ("Humedad relativa", f"{e.hr_pct:.1f} %"),
        ("Bulbo húmedo", f"{e.tbh_c:.2f} °C"),
        ("Punto de rocío", f"{e.rocio_c:.2f} °C"),
        ("Humedad absoluta", f"{e.w_g_kg:.2f} g/kg aire seco"),
        ("Entalpía", f"{e.entalpia_kj_kg:.2f} kJ/kg aire seco"),
        ("Volumen específico", f"{e.volumen_m3_kg:.4f} m³/kg aire seco"),
        ("Densidad", f"{e.densidad_kg_m3:.4f} kg/m³"),
        ("Presión", f"{e.presion_kpa:.3f} kPa"),
    ]
    return "\n".join(f"{nombre:<20}{valor}" for nombre, valor in filas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculadora psicrométrica")
    parser.add_argument("--tbs", type=float, required=True, help="bulbo seco en °C")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--hr", type=float, help="humedad relativa en %%")
    grupo.add_argument("--tbh", type=float, help="bulbo húmedo en °C")
    presion = parser.add_mutually_exclusive_group()
    presion.add_argument("--presion", type=float, help="presión atmosférica en kPa")
    presion.add_argument("--altitud", type=float, help="altitud sobre el nivel del mar en m")
    args = parser.parse_args(argv)

    if args.presion is not None:
        p = args.presion
    elif args.altitud is not None:
        p = presion_por_altitud(args.altitud)
    else:
        p = P_NIVEL_MAR_KPA

    try:
        if args.hr is not None:
            estado = estado_desde_hr(args.tbs, args.hr, p)
        else:
            estado = estado_desde_bulbo_humedo(args.tbs, args.tbh, p)
        print(informe(estado))
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
