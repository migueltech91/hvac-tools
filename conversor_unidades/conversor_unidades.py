"""Conversor de unidades HVAC.

Convierte entre las unidades más usadas en climatización y refrigeración:
potencia térmica, caudal de aire, presión, energía y temperatura.

Uso desde la terminal:
    python conversor_unidades/conversor_unidades.py 12000 BTU/h TR
    python conversor_unidades/conversor_unidades.py 1500 CFM m3/h
    python conversor_unidades/conversor_unidades.py 24 C F
    python conversor_unidades/conversor_unidades.py --listar
"""

from __future__ import annotations

import argparse
import sys

# Cada magnitud tiene una unidad base; el valor indica cuántas unidades base
# equivale 1 unidad.
FACTORES: dict[str, dict[str, float]] = {
    "potencia": {  # base: W
        "W": 1.0,
        "kW": 1000.0,
        "BTU/h": 0.29307107,
        "MBH": 293.07107,  # miles de BTU/h
        "TR": 3516.8528,  # tonelada de refrigeración = 12 000 BTU/h
        "kcal/h": 1.163,
        "HP": 745.69987,
    },
    "caudal": {  # base: m3/s
        "m3/s": 1.0,
        "m3/h": 1.0 / 3600.0,
        "L/s": 0.001,
        "CFM": 0.00047194745,  # pie cúbico por minuto
    },
    "presion": {  # base: Pa
        "Pa": 1.0,
        "kPa": 1000.0,
        "bar": 100000.0,
        "psi": 6894.7573,
        "inH2O": 249.08891,  # pulgada de columna de agua
        "mmH2O": 9.80665,
        "mmHg": 133.32239,
        "inHg": 3386.3886,
    },
    "energia": {  # base: J
        "J": 1.0,
        "kJ": 1000.0,
        "Wh": 3600.0,
        "kWh": 3600000.0,
        "BTU": 1055.0559,
        "kcal": 4186.8,
    },
}

UNIDADES_TEMPERATURA = ("C", "F", "K")

# Alias aceptados (en minúsculas) -> nombre canónico.
_ALIAS: dict[str, str] = {
    "btu": "BTU",
    "btuh": "BTU/h",
    "btu/hr": "BTU/h",
    "ton": "TR",
    "tons": "TR",
    "tonelada": "TR",
    "toneladas": "TR",
    "rt": "TR",
    "m³/h": "m3/h",
    "m3h": "m3/h",
    "m³/s": "m3/s",
    "lps": "L/s",
    "pcm": "CFM",
    "°c": "C",
    "°f": "F",
    "celsius": "C",
    "fahrenheit": "F",
    "kelvin": "K",
    "inwc": "inH2O",
    "in.w.c.": "inH2O",
    "\"wc": "inH2O",
    "mmca": "mmH2O",
}


def normalizar_unidad(unidad: str) -> str:
    """Devuelve el nombre canónico de una unidad (sin distinguir mayúsculas)."""
    texto = unidad.strip()
    clave = texto.lower()
    if clave in _ALIAS:
        return _ALIAS[clave]
    for nombre in UNIDADES_TEMPERATURA:
        if clave == nombre.lower():
            return nombre
    for tabla in FACTORES.values():
        for nombre in tabla:
            if clave == nombre.lower():
                return nombre
    raise ValueError(f"Unidad desconocida: {unidad!r}")


def magnitud_de(unidad: str) -> str:
    """Indica a qué magnitud pertenece una unidad canónica."""
    if unidad in UNIDADES_TEMPERATURA:
        return "temperatura"
    for magnitud, tabla in FACTORES.items():
        if unidad in tabla:
            return magnitud
    raise ValueError(f"Unidad desconocida: {unidad!r}")


def _convertir_temperatura(valor: float, origen: str, destino: str) -> float:
    if origen == "C":
        kelvin = valor + 273.15
    elif origen == "F":
        kelvin = (valor - 32.0) * 5.0 / 9.0 + 273.15
    else:
        kelvin = valor
    if kelvin < 0:
        raise ValueError("La temperatura no puede ser menor que el cero absoluto")
    if destino == "C":
        return kelvin - 273.15
    if destino == "F":
        return (kelvin - 273.15) * 9.0 / 5.0 + 32.0
    return kelvin


def convertir(valor: float, origen: str, destino: str) -> float:
    """Convierte ``valor`` de la unidad ``origen`` a la unidad ``destino``.

    >>> round(convertir(12000, "BTU/h", "TR"), 4)
    1.0
    """
    u_origen = normalizar_unidad(origen)
    u_destino = normalizar_unidad(destino)
    m_origen = magnitud_de(u_origen)
    m_destino = magnitud_de(u_destino)
    if m_origen != m_destino:
        raise ValueError(
            f"No se puede convertir {m_origen} ({u_origen}) a {m_destino} ({u_destino})"
        )
    if m_origen == "temperatura":
        return _convertir_temperatura(valor, u_origen, u_destino)
    tabla = FACTORES[m_origen]
    return valor * tabla[u_origen] / tabla[u_destino]


def tabla_equivalencias(valor: float, origen: str) -> dict[str, float]:
    """Convierte un valor a todas las unidades de su misma magnitud."""
    u_origen = normalizar_unidad(origen)
    magnitud = magnitud_de(u_origen)
    unidades = (
        UNIDADES_TEMPERATURA if magnitud == "temperatura" else tuple(FACTORES[magnitud])
    )
    return {u: convertir(valor, u_origen, u) for u in unidades}


def _formatear(numero: float) -> str:
    if numero != 0 and (abs(numero) >= 1e7 or abs(numero) < 1e-3):
        return f"{numero:.4e}"
    return f"{numero:,.4f}".rstrip("0").rstrip(".")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Conversor de unidades HVAC")
    parser.add_argument("valor", nargs="?", type=float, help="valor a convertir")
    parser.add_argument("origen", nargs="?", help="unidad de origen, p. ej. BTU/h")
    parser.add_argument(
        "destino", nargs="?", help="unidad de destino; si se omite, muestra todas"
    )
    parser.add_argument("--listar", action="store_true", help="lista las unidades")
    args = parser.parse_args(argv)

    if args.listar:
        for magnitud, tabla in FACTORES.items():
            print(f"{magnitud:<12} {', '.join(tabla)}")
        print(f"{'temperatura':<12} {', '.join(UNIDADES_TEMPERATURA)}")
        return 0
    if args.valor is None or args.origen is None:
        parser.error("indica un valor y una unidad de origen (o usa --listar)")

    try:
        if args.destino:
            resultado = convertir(args.valor, args.origen, args.destino)
            print(
                f"{_formatear(args.valor)} {normalizar_unidad(args.origen)} = "
                f"{_formatear(resultado)} {normalizar_unidad(args.destino)}"
            )
        else:
            for unidad, resultado in tabla_equivalencias(args.valor, args.origen).items():
                print(f"{_formatear(resultado):>18}  {unidad}")
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
