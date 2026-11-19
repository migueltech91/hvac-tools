"""Dimensionamiento de ductos de aire.

Calcula el tamaño de un ducto (circular y rectangular equivalente) para un
caudal dado, por dos métodos:

* Velocidad: se fija la velocidad del aire (m/s).
* Pérdida de carga constante (fricción igual): se fija la pérdida por
  fricción por metro de ducto (Pa/m).

La fricción se calcula con Darcy-Weisbach y la ecuación de Colebrook, y la
equivalencia rectangular con la fórmula de Huebscher (ASHRAE).

Uso desde la terminal:
    python ductos/ductos.py --caudal 1000 --velocidad 5
    python ductos/ductos.py --caudal 600 --unidad CFM --friccion 0.8 --relacion 2
    python ductos/ductos.py --caudal 1000 --velocidad 5 --alto 200
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

DENSIDAD_AIRE = 1.204  # kg/m³ a 20 °C, nivel del mar
VISCOSIDAD_AIRE = 1.81e-5  # Pa·s
RUGOSIDAD_GALVANIZADO = 0.00009  # m (ASHRAE, acero galvanizado)
CFM_A_M3H = 1.6990108
PASO_COMERCIAL_MM = 50

# Rangos de velocidad recomendados (m/s), orientativos para bajo ruido.
VELOCIDADES_RECOMENDADAS = {
    "residencial": (2.5, 5.0),
    "principal": (5.0, 8.0),
    "ramal": (3.0, 5.0),
    "retorno": (2.5, 5.0),
}


def numero_reynolds(velocidad: float, diametro: float) -> float:
    return DENSIDAD_AIRE * velocidad * diametro / VISCOSIDAD_AIRE


def factor_friccion(reynolds: float, diametro: float, rugosidad: float = RUGOSIDAD_GALVANIZADO) -> float:
    """Factor de fricción de Darcy (Colebrook; laminar si Re < 2300)."""
    if reynolds <= 0:
        raise ValueError("El número de Reynolds debe ser positivo")
    if reynolds < 2300:
        return 64.0 / reynolds
    rel = rugosidad / diametro
    # Valor inicial de Swamee-Jain y refinamiento iterativo de Colebrook.
    f = 0.25 / math.log10(rel / 3.7 + 5.74 / reynolds**0.9) ** 2
    for _ in range(50):
        nuevo = (-2.0 * math.log10(rel / 3.7 + 2.51 / (reynolds * math.sqrt(f)))) ** -2
        if abs(nuevo - f) < 1e-12:
            return nuevo
        f = nuevo
    return f


def perdida_por_friccion(caudal_m3s: float, diametro: float, rugosidad: float = RUGOSIDAD_GALVANIZADO) -> float:
    """Pérdida de presión por fricción (Pa/m) en un ducto circular."""
    area = math.pi * diametro**2 / 4
    velocidad = caudal_m3s / area
    f = factor_friccion(numero_reynolds(velocidad, diametro), diametro, rugosidad)
    return f / diametro * DENSIDAD_AIRE * velocidad**2 / 2


def diametro_por_velocidad(caudal_m3s: float, velocidad: float) -> float:
    if caudal_m3s <= 0 or velocidad <= 0:
        raise ValueError("Caudal y velocidad deben ser positivos")
    return math.sqrt(4 * caudal_m3s / (math.pi * velocidad))


def diametro_por_friccion(caudal_m3s: float, friccion_pa_m: float, rugosidad: float = RUGOSIDAD_GALVANIZADO) -> float:
    """Diámetro que produce la pérdida por fricción indicada (bisección)."""
    if caudal_m3s <= 0 or friccion_pa_m <= 0:
        raise ValueError("Caudal y fricción deben ser positivos")
    a, b = 0.01, 5.0
    for _ in range(200):
        medio = (a + b) / 2
        if perdida_por_friccion(caudal_m3s, medio, rugosidad) > friccion_pa_m:
            a = medio  # ducto demasiado pequeño
        else:
            b = medio
        if b - a < 1e-7:
            break
    return (a + b) / 2


def diametro_equivalente(ancho: float, alto: float) -> float:
    """Diámetro circular equivalente de un ducto rectangular (Huebscher)."""
    return 1.30 * (ancho * alto) ** 0.625 / (ancho + alto) ** 0.25


def rectangular_por_relacion(diametro: float, relacion: float) -> tuple[float, float]:
    """Ancho y alto (m) con relación de aspecto ancho/alto equivalentes a un diámetro."""
    if relacion < 1:
        raise ValueError("La relación de aspecto debe ser >= 1")
    alto = diametro * (relacion + 1) ** 0.25 / (1.30 * relacion**0.625)
    return relacion * alto, alto


def rectangular_por_alto(diametro: float, alto: float) -> float:
    """Ancho (m) necesario para un alto fijo, equivalente a un diámetro dado."""
    if alto <= 0:
        raise ValueError("El alto debe ser positivo")
    a, b = 1e-4, 50.0
    if diametro_equivalente(b, alto) < diametro:
        raise ValueError("El alto indicado es demasiado pequeño para este caudal")
    for _ in range(200):
        medio = (a + b) / 2
        if diametro_equivalente(medio, alto) < diametro:
            a = medio
        else:
            b = medio
        if b - a < 1e-7:
            break
    return (a + b) / 2


def redondear_comercial(medida_m: float, paso_mm: int = PASO_COMERCIAL_MM) -> int:
    """Redondea hacia arriba a la medida comercial (mm) más próxima."""
    return int(math.ceil(round(medida_m * 1000, 6) / paso_mm) * paso_mm)


@dataclass
class ResultadoDucto:
    caudal_m3h: float
    diametro_m: float
    velocidad_ms: float
    friccion_pa_m: float
    ancho_m: float
    alto_m: float

    @property
    def diametro_comercial_mm(self) -> int:
        return redondear_comercial(self.diametro_m)

    @property
    def rectangular_comercial_mm(self) -> tuple[int, int]:
        return redondear_comercial(self.ancho_m), redondear_comercial(self.alto_m)


def dimensionar(
    caudal_m3h: float,
    velocidad: float | None = None,
    friccion: float | None = None,
    relacion: float = 1.5,
    alto_m: float | None = None,
) -> ResultadoDucto:
    """Dimensiona un ducto por velocidad o por fricción (indicar solo uno)."""
    if (velocidad is None) == (friccion is None):
        raise ValueError("Indique la velocidad o la fricción (solo una)")
    q = caudal_m3h / 3600
    if velocidad is not None:
        diametro = diametro_por_velocidad(q, velocidad)
    else:
        diametro = diametro_por_friccion(q, friccion)
    if alto_m is not None:
        ancho, alto = rectangular_por_alto(diametro, alto_m), alto_m
    else:
        ancho, alto = rectangular_por_relacion(diametro, relacion)
    return ResultadoDucto(
        caudal_m3h=caudal_m3h,
        diametro_m=diametro,
        velocidad_ms=q / (math.pi * diametro**2 / 4),
        friccion_pa_m=perdida_por_friccion(q, diametro),
        ancho_m=ancho,
        alto_m=alto,
    )


def advertencias(resultado: ResultadoDucto, tipo: str = "principal") -> list[str]:
    """Avisos si la velocidad sale del rango recomendado para el tipo de tramo."""
    minimo, maximo = VELOCIDADES_RECOMENDADAS[tipo]
    avisos = []
    velocidad = round(resultado.velocidad_ms, 3)  # evita avisos por redondeo
    if velocidad > maximo:
        avisos.append(
            f"Velocidad {resultado.velocidad_ms:.1f} m/s mayor que la recomendada "
            f"({maximo} m/s) para tramo {tipo}: posible ruido."
        )
    elif velocidad < minimo:
        avisos.append(
            f"Velocidad {resultado.velocidad_ms:.1f} m/s menor que la recomendada "
            f"({minimo} m/s) para tramo {tipo}: ducto sobredimensionado."
        )
    if resultado.friccion_pa_m > 2.0:
        avisos.append("Pérdida por fricción alta (> 2 Pa/m): revise el ventilador.")
    return avisos


def informe(r: ResultadoDucto, tipo: str = "principal") -> str:
    ancho_c, alto_c = r.rectangular_comercial_mm
    lineas = [
        f"Caudal               {r.caudal_m3h:,.0f} m³/h ({r.caudal_m3h / CFM_A_M3H:,.0f} CFM)",
        f"Diámetro calculado   {r.diametro_m * 1000:.0f} mm  -> comercial {r.diametro_comercial_mm} mm",
        f"Rectangular          {r.ancho_m * 1000:.0f} x {r.alto_m * 1000:.0f} mm"
        f"  -> comercial {ancho_c} x {alto_c} mm",
        f"Velocidad            {r.velocidad_ms:.2f} m/s",
        f"Pérdida por fricción {r.friccion_pa_m:.3f} Pa/m",
    ]
    lineas += [f"AVISO: {a}" for a in advertencias(r, tipo)]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dimensionamiento de ductos de aire")
    parser.add_argument("--caudal", type=float, required=True)
    parser.add_argument("--unidad", choices=("m3/h", "CFM"), default="m3/h")
    metodo = parser.add_mutually_exclusive_group(required=True)
    metodo.add_argument("--velocidad", type=float, help="velocidad del aire en m/s")
    metodo.add_argument("--friccion", type=float, help="pérdida por fricción en Pa/m")
    forma = parser.add_mutually_exclusive_group()
    forma.add_argument("--relacion", type=float, default=1.5, help="relación ancho/alto")
    forma.add_argument("--alto", type=float, help="alto fijo del ducto rectangular en mm")
    parser.add_argument("--tipo", choices=VELOCIDADES_RECOMENDADAS, default="principal")
    args = parser.parse_args(argv)

    caudal = args.caudal * CFM_A_M3H if args.unidad == "CFM" else args.caudal
    try:
        resultado = dimensionar(
            caudal,
            velocidad=args.velocidad,
            friccion=args.friccion,
            relacion=args.relacion,
            alto_m=args.alto / 1000 if args.alto else None,
        )
        print(informe(resultado, args.tipo))
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
