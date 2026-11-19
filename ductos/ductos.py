"""Dimensionamiento y verificación de ductos de aire.

Dos modos de trabajo:

1. Dimensionar: calcula el tamaño de un ducto (circular y rectangular
   equivalente) para un caudal dado, por velocidad (m/s) o por pérdida de
   carga constante (Pa/m).
2. Verificar: revisa un ducto existente o propuesto (medidas en cm o mm) y
   calcula la velocidad real del aire y la pérdida por fricción. Si la
   velocidad es demasiado alta, avisa del ruido en difusores y rejillas y
   sugiere el tamaño mínimo recomendado.

La fricción se calcula con Darcy-Weisbach y la ecuación de Colebrook, y la
equivalencia rectangular con la fórmula de Huebscher (ASHRAE).

Uso desde la terminal (medidas en cm por defecto):
    python ductos/ductos.py --caudal 1000 --velocidad 5
    python ductos/ductos.py --caudal 600 --unidad CFM --friccion 0.8 --relacion 2
    python ductos/ductos.py --caudal 1000 --velocidad 5 --alto 20
    python ductos/ductos.py --caudal 3000 --medida 20 30
    python ductos/ductos.py --caudal 800 --diametro 25 --tipo ramal
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
FRICCION_MAXIMA_PA_M = 2.0

# Unidades de longitud aceptadas para las medidas del ducto (metros por unidad).
UNIDADES_MEDIDA = {"cm": 0.01, "mm": 0.001}

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


def a_metros(valor: float, unidad: str = "cm") -> float:
    """Convierte una medida en cm o mm a metros."""
    if unidad not in UNIDADES_MEDIDA:
        raise ValueError(f"Unidad de medida inválida: {unidad!r}. Opciones: cm, mm")
    return valor * UNIDADES_MEDIDA[unidad]


def formatear_medida(medida_m: float, unidad: str = "cm", decimales: int = 1) -> str:
    """Texto de una medida en cm o mm (los mm siempre sin decimales)."""
    valor = medida_m / UNIDADES_MEDIDA[unidad]
    if unidad == "mm":
        decimales = 0
    return f"{valor:.{decimales}f}".rstrip("0").rstrip(".") if decimales else f"{valor:.0f}"


# --------------------------------------------------------------------------
# Modo dimensionar
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# Modo verificar
# --------------------------------------------------------------------------


@dataclass
class VerificacionDucto:
    caudal_m3h: float
    forma: str  # "rectangular" o "circular"
    ancho_m: float | None
    alto_m: float | None
    diametro_m: float  # real (circular) o equivalente (rectangular)
    area_m2: float
    velocidad_ms: float  # velocidad real: caudal / área
    friccion_pa_m: float


def verificar(
    caudal_m3h: float,
    ancho_m: float | None = None,
    alto_m: float | None = None,
    diametro_m: float | None = None,
) -> VerificacionDucto:
    """Velocidad y fricción de un ducto existente (rectangular o circular)."""
    if caudal_m3h <= 0:
        raise ValueError("El caudal debe ser positivo")
    rectangular = ancho_m is not None or alto_m is not None
    if rectangular == (diametro_m is not None):
        raise ValueError("Indique ancho y alto (rectangular) o el diámetro (circular)")
    q = caudal_m3h / 3600
    if rectangular:
        if not ancho_m or not alto_m or ancho_m <= 0 or alto_m <= 0:
            raise ValueError("El ancho y el alto deben ser positivos")
        area = ancho_m * alto_m
        diametro = diametro_equivalente(ancho_m, alto_m)
    else:
        if diametro_m <= 0:
            raise ValueError("El diámetro debe ser positivo")
        area = math.pi * diametro_m**2 / 4
        diametro = diametro_m
    return VerificacionDucto(
        caudal_m3h=caudal_m3h,
        forma="rectangular" if rectangular else "circular",
        ancho_m=ancho_m,
        alto_m=alto_m,
        diametro_m=diametro,
        area_m2=area,
        velocidad_ms=q / area,
        # Huebscher: el diámetro equivalente da la misma fricción con el mismo caudal.
        friccion_pa_m=perdida_por_friccion(q, diametro),
    )


def tamano_recomendado(v: VerificacionDucto, tipo: str = "principal") -> dict | None:
    """Tamaño comercial mínimo si la velocidad supera el máximo recomendado.

    En ductos rectangulares conserva el alto (normalmente limitado por el
    cielo raso) y agranda el ancho. Devuelve None si el ducto es adecuado.
    """
    _, maximo = VELOCIDADES_RECOMENDADAS[tipo]
    if round(v.velocidad_ms, 3) <= maximo:
        return None
    area_minima = v.caudal_m3h / 3600 / maximo
    if v.forma == "rectangular":
        alto_mm = redondear_comercial(v.alto_m)
        ancho_mm = redondear_comercial(area_minima / (alto_mm / 1000))
        area = ancho_mm * alto_mm / 1e6
        return {
            "forma": "rectangular",
            "ancho_m": ancho_mm / 1000,
            "alto_m": alto_mm / 1000,
            "velocidad_ms": v.caudal_m3h / 3600 / area,
        }
    diametro_mm = redondear_comercial(math.sqrt(4 * area_minima / math.pi))
    area = math.pi * (diametro_mm / 1000) ** 2 / 4
    return {
        "forma": "circular",
        "diametro_m": diametro_mm / 1000,
        "velocidad_ms": v.caudal_m3h / 3600 / area,
    }


# --------------------------------------------------------------------------
# Avisos e informes
# --------------------------------------------------------------------------


def advertencias(resultado: ResultadoDucto | VerificacionDucto, tipo: str = "principal") -> list[str]:
    """Avisos si la velocidad sale del rango recomendado para el tipo de tramo."""
    minimo, maximo = VELOCIDADES_RECOMENDADAS[tipo]
    avisos = []
    velocidad = round(resultado.velocidad_ms, 3)  # evita avisos por redondeo
    if velocidad > maximo:
        exceso = "muy por encima del" if velocidad > 1.5 * maximo else "mayor que el"
        avisos.append(
            f"Velocidad {velocidad:.1f} m/s {exceso} máximo recomendado ({maximo:g} m/s) "
            f"para tramo {tipo}: ducto demasiado pequeño, generará ruido en "
            "difusores y rejillas."
        )
    elif velocidad < minimo:
        avisos.append(
            f"Velocidad {velocidad:.1f} m/s menor que la recomendada "
            f"({minimo:g} m/s) para tramo {tipo}: ducto sobredimensionado."
        )
    if resultado.friccion_pa_m > FRICCION_MAXIMA_PA_M:
        avisos.append(
            f"Pérdida por fricción alta ({resultado.friccion_pa_m:.1f} Pa/m > "
            f"{FRICCION_MAXIMA_PA_M:g} Pa/m): el ventilador necesitará más presión."
        )
    return avisos


def _caudal_txt(caudal_m3h: float) -> str:
    return f"{caudal_m3h:,.0f} m³/h ({caudal_m3h / CFM_A_M3H:,.0f} CFM)"


def informe(r: ResultadoDucto, tipo: str = "principal", unidad: str = "cm") -> str:
    ancho_c, alto_c = r.rectangular_comercial_mm
    m = lambda x: formatear_medida(x, unidad)  # noqa: E731
    lineas = [
        f"Caudal               {_caudal_txt(r.caudal_m3h)}",
        f"Diámetro calculado   {m(r.diametro_m)} {unidad}"
        f"  -> comercial {m(r.diametro_comercial_mm / 1000)} {unidad}",
        f"Rectangular          {m(r.ancho_m)} x {m(r.alto_m)} {unidad}"
        f"  -> comercial {m(ancho_c / 1000)} x {m(alto_c / 1000)} {unidad}",
        f"Velocidad            {r.velocidad_ms:.2f} m/s",
        f"Pérdida por fricción {r.friccion_pa_m:.3f} Pa/m",
    ]
    lineas += [f"AVISO: {a}" for a in advertencias(r, tipo)]
    return "\n".join(lineas)


def informe_verificacion(v: VerificacionDucto, tipo: str = "principal", unidad: str = "cm") -> str:
    m = lambda x: formatear_medida(x, unidad)  # noqa: E731
    if v.forma == "rectangular":
        medida = f"{m(v.ancho_m)} x {m(v.alto_m)} {unidad} (Ø equivalente {m(v.diametro_m)} {unidad})"
    else:
        medida = f"Ø {m(v.diametro_m)} {unidad}"
    minimo, maximo = VELOCIDADES_RECOMENDADAS[tipo]
    lineas = [
        f"Caudal               {_caudal_txt(v.caudal_m3h)}",
        f"Ducto                {medida}",
        f"Área libre           {v.area_m2:.4f} m²",
        f"Velocidad del aire   {v.velocidad_ms:.2f} m/s  (recomendado {minimo:g}-{maximo:g} m/s, tramo {tipo})",
        f"Pérdida por fricción {v.friccion_pa_m:.3f} Pa/m",
    ]
    avisos = advertencias(v, tipo)
    lineas += [f"AVISO: {a}" for a in avisos] or ["Resultado: ducto adecuado para este caudal."]
    sugerido = tamano_recomendado(v, tipo)
    if sugerido:
        if sugerido["forma"] == "rectangular":
            texto = f"{m(sugerido['ancho_m'])} x {m(sugerido['alto_m'])} {unidad}"
        else:
            texto = f"Ø {m(sugerido['diametro_m'])} {unidad}"
        lineas.append(
            f"Tamaño mínimo recomendado: {texto} -> {sugerido['velocidad_ms']:.1f} m/s"
        )
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dimensionamiento y verificación de ductos de aire")
    parser.add_argument("--caudal", type=float, required=True)
    parser.add_argument("--unidad", choices=("m3/h", "CFM"), default="m3/h", help="unidad del caudal")
    parser.add_argument(
        "--unidad-medida", choices=tuple(UNIDADES_MEDIDA), default="cm",
        help="unidad de las medidas del ducto (entrada y salida)",
    )
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--velocidad", type=float, help="dimensionar: velocidad del aire en m/s")
    modo.add_argument("--friccion", type=float, help="dimensionar: pérdida por fricción en Pa/m")
    modo.add_argument("--medida", type=float, nargs=2, metavar=("ANCHO", "ALTO"),
                      help="verificar un ducto rectangular existente")
    modo.add_argument("--diametro", type=float, help="verificar un ducto circular existente")
    forma = parser.add_mutually_exclusive_group()
    forma.add_argument("--relacion", type=float, default=1.5, help="relación ancho/alto")
    forma.add_argument("--alto", type=float, help="alto fijo del ducto rectangular")
    parser.add_argument("--tipo", choices=VELOCIDADES_RECOMENDADAS, default="principal")
    args = parser.parse_args(argv)

    caudal = args.caudal * CFM_A_M3H if args.unidad == "CFM" else args.caudal
    unidad = args.unidad_medida
    try:
        if args.medida or args.diametro:
            if args.medida:
                ancho, alto = (a_metros(x, unidad) for x in args.medida)
                v = verificar(caudal, ancho_m=ancho, alto_m=alto)
            else:
                v = verificar(caudal, diametro_m=a_metros(args.diametro, unidad))
            print(informe_verificacion(v, args.tipo, unidad))
        else:
            resultado = dimensionar(
                caudal,
                velocidad=args.velocidad,
                friccion=args.friccion,
                relacion=args.relacion,
                alto_m=a_metros(args.alto, unidad) if args.alto else None,
            )
            print(informe(resultado, args.tipo, unidad))
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
