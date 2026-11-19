"""Calculadora de carga térmica (BTU/h) para un ambiente.

Estima la capacidad de aire acondicionado necesaria para una habitación,
oficina o local pequeño mediante un método simplificado de factores, del tipo
que se usa para presupuestar equipos split. Suma:

* Envolvente (paredes, techo, infiltración) según área, altura y clima.
* Ganancia solar por ventanas según su exposición al sol.
* Personas según su nivel de actividad (calor sensible + latente).
* Equipos e iluminación (cada vatio eléctrico = 3,412 BTU/h).
* Un factor de seguridad.

Es una estimación preliminar: para proyectos formales debe hacerse un
cálculo detallado (ASHRAE, Manual J / Manual N, etc.).

Uso desde la terminal:
    python carga_termica/carga_termica.py --area 20 --personas 2 --ventanas 3 \
        --exposicion media --equipos 400 --clima calido
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

BTU_H_POR_W = 3.412142
BTU_H_POR_TR = 12000.0
ALTURA_REFERENCIA_M = 2.5

# BTU/h por m² de piso (techo de 2,5 m), incluye muros, techo e infiltración.
FACTOR_CLIMA = {
    "templado": 450.0,
    "calido": 550.0,
    "muy_calido": 650.0,
}

# BTU/h por m² de vidrio sin protección solar.
FACTOR_VENTANA = {
    "sombra": 80.0,  # siempre a la sombra o con protección exterior
    "baja": 160.0,
    "media": 320.0,
    "alta": 550.0,  # sol directo de tarde (fachada poniente) sin cortinas
}

# BTU/h por persona (sensible + latente).
FACTOR_PERSONA = {
    "sedentaria": 450.0,  # sentado: dormitorio, sala, oficina
    "ligera": 600.0,  # de pie, comercio, cocina
    "intensa": 1000.0,  # gimnasio, trabajo físico
}

# Capacidades nominales habituales de equipos split / compactos (BTU/h).
CAPACIDADES_COMERCIALES = (9000, 12000, 18000, 24000, 30000, 36000, 48000, 60000)


@dataclass
class Ambiente:
    area_m2: float
    altura_m: float = ALTURA_REFERENCIA_M
    clima: str = "calido"
    personas: int = 1
    actividad: str = "sedentaria"
    ventanas_m2: float = 0.0
    exposicion: str = "media"
    equipos_w: float = 0.0
    factor_seguridad: float = 0.10

    def validar(self) -> None:
        if self.area_m2 <= 0:
            raise ValueError("El área debe ser mayor que cero")
        if self.altura_m <= 0:
            raise ValueError("La altura debe ser mayor que cero")
        if self.personas < 0 or self.ventanas_m2 < 0 or self.equipos_w < 0:
            raise ValueError("Personas, ventanas y equipos no pueden ser negativos")
        if not 0 <= self.factor_seguridad <= 0.5:
            raise ValueError("El factor de seguridad debe estar entre 0 y 0,5")
        for valor, opciones, nombre in (
            (self.clima, FACTOR_CLIMA, "clima"),
            (self.actividad, FACTOR_PERSONA, "actividad"),
            (self.exposicion, FACTOR_VENTANA, "exposición"),
        ):
            if valor not in opciones:
                raise ValueError(
                    f"{nombre} inválido: {valor!r}. Opciones: {', '.join(opciones)}"
                )


@dataclass
class ResultadoCarga:
    desglose_btu_h: dict[str, float] = field(default_factory=dict)
    subtotal_btu_h: float = 0.0
    total_btu_h: float = 0.0
    equipo_sugerido_btu_h: int | None = None

    @property
    def total_kw(self) -> float:
        return self.total_btu_h / BTU_H_POR_W / 1000.0

    @property
    def total_tr(self) -> float:
        return self.total_btu_h / BTU_H_POR_TR


def equipo_sugerido(carga_btu_h: float) -> int | None:
    """Menor capacidad comercial que cubre la carga, o None si excede 60 000 BTU/h."""
    for capacidad in CAPACIDADES_COMERCIALES:
        if capacidad >= carga_btu_h:
            return capacidad
    return None


def calcular_carga(ambiente: Ambiente) -> ResultadoCarga:
    """Calcula la carga térmica de enfriamiento de un ambiente."""
    ambiente.validar()
    envolvente = (
        ambiente.area_m2
        * FACTOR_CLIMA[ambiente.clima]
        * (ambiente.altura_m / ALTURA_REFERENCIA_M)
    )
    desglose = {
        "envolvente": envolvente,
        "ventanas": ambiente.ventanas_m2 * FACTOR_VENTANA[ambiente.exposicion],
        "personas": ambiente.personas * FACTOR_PERSONA[ambiente.actividad],
        "equipos": ambiente.equipos_w * BTU_H_POR_W,
    }
    subtotal = sum(desglose.values())
    desglose["seguridad"] = subtotal * ambiente.factor_seguridad
    total = subtotal + desglose["seguridad"]
    return ResultadoCarga(
        desglose_btu_h=desglose,
        subtotal_btu_h=subtotal,
        total_btu_h=total,
        equipo_sugerido_btu_h=equipo_sugerido(total),
    )


def informe(resultado: ResultadoCarga) -> str:
    """Texto legible con el desglose y la recomendación."""
    lineas = ["Desglose de carga térmica", "-" * 34]
    for concepto, valor in resultado.desglose_btu_h.items():
        lineas.append(f"{concepto.capitalize():<14}{valor:>12,.0f} BTU/h")
    lineas.append("-" * 34)
    lineas.append(f"{'TOTAL':<14}{resultado.total_btu_h:>12,.0f} BTU/h")
    lineas.append(f"{'':<14}{resultado.total_kw:>12,.2f} kW")
    lineas.append(f"{'':<14}{resultado.total_tr:>12,.2f} TR")
    if resultado.equipo_sugerido_btu_h:
        lineas.append(
            f"\nEquipo sugerido: {resultado.equipo_sugerido_btu_h:,} BTU/h "
            f"({resultado.equipo_sugerido_btu_h / BTU_H_POR_TR:g} TR)"
        )
    else:
        lineas.append(
            "\nLa carga supera 60 000 BTU/h: considere varios equipos o un sistema central."
        )
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculadora de carga térmica (BTU/h)")
    parser.add_argument("--area", type=float, required=True, help="área del piso en m²")
    parser.add_argument("--altura", type=float, default=ALTURA_REFERENCIA_M, help="altura en m")
    parser.add_argument("--clima", choices=FACTOR_CLIMA, default="calido")
    parser.add_argument("--personas", type=int, default=1)
    parser.add_argument("--actividad", choices=FACTOR_PERSONA, default="sedentaria")
    parser.add_argument("--ventanas", type=float, default=0.0, help="área de vidrio en m²")
    parser.add_argument("--exposicion", choices=FACTOR_VENTANA, default="media")
    parser.add_argument("--equipos", type=float, default=0.0, help="potencia de equipos e iluminación en W")
    parser.add_argument("--seguridad", type=float, default=0.10, help="factor de seguridad (0.10 = 10 %%)")
    args = parser.parse_args(argv)

    ambiente = Ambiente(
        area_m2=args.area,
        altura_m=args.altura,
        clima=args.clima,
        personas=args.personas,
        actividad=args.actividad,
        ventanas_m2=args.ventanas,
        exposicion=args.exposicion,
        equipos_w=args.equipos,
        factor_seguridad=args.seguridad,
    )
    try:
        print(informe(calcular_carga(ambiente)))
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
