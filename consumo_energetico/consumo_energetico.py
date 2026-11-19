"""Estimador de consumo eléctrico y costo de equipos de aire acondicionado.

Calcula la potencia eléctrica, el consumo (kWh) y el costo mensual y anual de
un equipo a partir de su capacidad y su eficiencia (SEER, EER, COP o kW/TR).
También compara dos equipos y calcula el ahorro y el periodo de retorno de la
inversión.

Uso desde la terminal:
    python consumo_energetico/consumo_energetico.py calcular \
        --capacidad 12000 --eficiencia 13 --tipo SEER --horas 8 --tarifa 0.15

    python consumo_energetico/consumo_energetico.py comparar \
        --capacidad 18000 --horas 10 --tarifa 0.18 \
        --equipo-a SEER 13 450 --equipo-b SEER 22 750
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

BTU_H_POR_W = 3.412142
TIPOS_EFICIENCIA = ("SEER", "EER", "COP", "kW/TR")


def eer_equivalente(valor: float, tipo: str) -> float:
    """Convierte cualquier índice de eficiencia a BTU/h por W (EER/SEER)."""
    if valor <= 0:
        raise ValueError("La eficiencia debe ser positiva")
    if tipo in ("SEER", "EER"):
        return valor
    if tipo == "COP":
        return valor * BTU_H_POR_W
    if tipo == "kW/TR":
        return 12.0 / valor
    raise ValueError(f"Tipo de eficiencia desconocido: {tipo!r}. Opciones: {', '.join(TIPOS_EFICIENCIA)}")


@dataclass
class Consumo:
    potencia_kw: float
    kwh_dia: float
    kwh_mes: float
    kwh_anual: float
    costo_mes: float
    costo_anual: float


def calcular_consumo(
    capacidad_btu_h: float,
    eficiencia: float,
    tipo: str = "SEER",
    horas_dia: float = 8,
    dias_mes: float = 30,
    meses_anio: float = 12,
    tarifa_kwh: float = 0.15,
    factor_uso: float = 1.0,
) -> Consumo:
    """Consumo de un equipo.

    ``factor_uso`` es la fracción del tiempo encendido en que trabaja el
    compresor (1.0 = estimación conservadora). Con SEER, la eficiencia ya
    representa el promedio de temporada.
    """
    if capacidad_btu_h <= 0:
        raise ValueError("La capacidad debe ser positiva")
    if not 0 <= horas_dia <= 24:
        raise ValueError("Las horas por día deben estar entre 0 y 24")
    if not 0 <= dias_mes <= 31 or not 0 <= meses_anio <= 12:
        raise ValueError("Días por mes (0-31) o meses por año (0-12) fuera de rango")
    if tarifa_kwh < 0:
        raise ValueError("La tarifa no puede ser negativa")
    if not 0 < factor_uso <= 1:
        raise ValueError("El factor de uso debe estar entre 0 y 1")

    potencia_kw = capacidad_btu_h / eer_equivalente(eficiencia, tipo) / 1000.0
    kwh_dia = potencia_kw * horas_dia * factor_uso
    kwh_mes = kwh_dia * dias_mes
    kwh_anual = kwh_mes * meses_anio
    return Consumo(
        potencia_kw=potencia_kw,
        kwh_dia=kwh_dia,
        kwh_mes=kwh_mes,
        kwh_anual=kwh_anual,
        costo_mes=kwh_mes * tarifa_kwh,
        costo_anual=kwh_anual * tarifa_kwh,
    )


@dataclass
class Comparacion:
    equipo_a: Consumo
    equipo_b: Consumo
    ahorro_anual: float  # positivo si B consume menos que A
    diferencia_precio: float  # precio B - precio A
    retorno_anios: float | None  # None si nunca se recupera


def comparar_equipos(
    capacidad_btu_h: float,
    eficiencia_a: float,
    precio_a: float,
    eficiencia_b: float,
    precio_b: float,
    tipo_a: str = "SEER",
    tipo_b: str = "SEER",
    **uso,
) -> Comparacion:
    """Compara dos equipos de igual capacidad (precio en la moneda de la tarifa)."""
    a = calcular_consumo(capacidad_btu_h, eficiencia_a, tipo_a, **uso)
    b = calcular_consumo(capacidad_btu_h, eficiencia_b, tipo_b, **uso)
    ahorro = a.costo_anual - b.costo_anual
    diferencia = precio_b - precio_a
    if diferencia <= 0:
        retorno = 0.0 if ahorro >= 0 else None
    else:
        retorno = diferencia / ahorro if ahorro > 0 else None
    return Comparacion(a, b, ahorro, diferencia, retorno)


def _formato_consumo(c: Consumo, moneda: str) -> list[str]:
    return [
        f"Potencia eléctrica   {c.potencia_kw:.2f} kW",
        f"Consumo diario       {c.kwh_dia:.1f} kWh",
        f"Consumo mensual      {c.kwh_mes:,.0f} kWh  ->  {moneda}{c.costo_mes:,.2f}",
        f"Consumo anual        {c.kwh_anual:,.0f} kWh  ->  {moneda}{c.costo_anual:,.2f}",
    ]


def informe_consumo(c: Consumo, moneda: str = "$") -> str:
    return "\n".join(_formato_consumo(c, moneda))


def informe_comparacion(r: Comparacion, moneda: str = "$") -> str:
    lineas = ["Equipo A", *_formato_consumo(r.equipo_a, moneda), "", "Equipo B",
              *_formato_consumo(r.equipo_b, moneda), ""]
    if r.ahorro_anual >= 0:
        lineas.append(f"El equipo B ahorra {moneda}{r.ahorro_anual:,.2f} al año.")
    else:
        lineas.append(f"El equipo B cuesta {moneda}{-r.ahorro_anual:,.2f} más al año.")
    if r.retorno_anios is None:
        lineas.append("La diferencia de precio no se recupera con el ahorro.")
    elif r.retorno_anios == 0:
        lineas.append("El equipo B no cuesta más: conviene desde el primer día.")
    else:
        lineas.append(
            f"Sobrecosto de {moneda}{r.diferencia_precio:,.2f} recuperado en "
            f"{r.retorno_anios:.1f} años ({r.retorno_anios * 12:.0f} meses)."
        )
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consumo eléctrico de equipos de A/C")
    sub = parser.add_subparsers(dest="comando", required=True)

    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--capacidad", type=float, required=True, help="BTU/h")
    comunes.add_argument("--horas", type=float, default=8, help="horas de uso por día")
    comunes.add_argument("--dias", type=float, default=30, help="días de uso por mes")
    comunes.add_argument("--meses", type=float, default=12, help="meses de uso por año")
    comunes.add_argument("--tarifa", type=float, default=0.15, help="costo por kWh")
    comunes.add_argument("--factor-uso", type=float, default=1.0)
    comunes.add_argument("--moneda", default="$")

    calc = sub.add_parser("calcular", parents=[comunes], help="consumo de un equipo")
    calc.add_argument("--eficiencia", type=float, required=True)
    calc.add_argument("--tipo", choices=TIPOS_EFICIENCIA, default="SEER")

    comp = sub.add_parser("comparar", parents=[comunes], help="compara dos equipos")
    for letra in ("a", "b"):
        comp.add_argument(
            f"--equipo-{letra}",
            nargs=3,
            required=True,
            metavar=("TIPO", "EFICIENCIA", "PRECIO"),
        )

    args = parser.parse_args(argv)
    uso = dict(
        horas_dia=args.horas,
        dias_mes=args.dias,
        meses_anio=args.meses,
        tarifa_kwh=args.tarifa,
        factor_uso=args.factor_uso,
    )
    try:
        if args.comando == "calcular":
            consumo = calcular_consumo(args.capacidad, args.eficiencia, args.tipo, **uso)
            print(informe_consumo(consumo, args.moneda))
        else:
            tipo_a, ef_a, precio_a = args.equipo_a
            tipo_b, ef_b, precio_b = args.equipo_b
            resultado = comparar_equipos(
                args.capacidad,
                float(ef_a),
                float(precio_a),
                float(ef_b),
                float(precio_b),
                tipo_a=tipo_a,
                tipo_b=tipo_b,
                **uso,
            )
            print(informe_comparacion(resultado, args.moneda))
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
