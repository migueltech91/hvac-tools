"""Capa de integración entre la demo web y los módulos de cálculo.

La página (index.html) carga este archivo en el navegador con Pyodide y llama
a ``ejecutar(nombre, params_json)``. Cada función recibe parámetros simples y
devuelve un diccionario serializable a JSON, de modo que la web usa
exactamente el mismo código Python que la línea de comandos y los tests.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from carga_termica.carga_termica import Ambiente, calcular_carga
from consumo_energetico.consumo_energetico import calcular_consumo, comparar_equipos
from conversor_unidades.conversor_unidades import (
    FACTORES,
    UNIDADES_TEMPERATURA,
    convertir,
    normalizar_unidad,
    tabla_equivalencias,
)
from ductos.ductos import (
    CFM_A_M3H,
    UNIDADES_MEDIDA,
    VELOCIDADES_RECOMENDADAS,
    a_metros,
    advertencias,
    dimensionar,
    tamano_recomendado,
    verificar,
)
from psicrometria.psicrometria import (
    estado_desde_bulbo_humedo,
    estado_desde_hr,
    presion_por_altitud,
)


def unidades() -> dict:
    magnitudes = {m: list(tabla) for m, tabla in FACTORES.items()}
    magnitudes["temperatura"] = list(UNIDADES_TEMPERATURA)
    return magnitudes


def carga(**p) -> dict:
    r = calcular_carga(
        Ambiente(
            area_m2=float(p["area"]),
            altura_m=float(p.get("altura", 2.5)),
            clima=p.get("clima", "calido"),
            personas=int(p.get("personas", 1)),
            actividad=p.get("actividad", "sedentaria"),
            ventanas_m2=float(p.get("ventanas", 0)),
            exposicion=p.get("exposicion", "media"),
            equipos_w=float(p.get("equipos", 0)),
            factor_seguridad=float(p.get("seguridad", 0.10)),
        )
    )
    return {
        "desglose": r.desglose_btu_h,
        "total_btu_h": r.total_btu_h,
        "total_kw": r.total_kw,
        "total_tr": r.total_tr,
        "equipo_btu_h": r.equipo_sugerido_btu_h,
    }


def conversor(**p) -> dict:
    valor = float(p["valor"])
    origen = normalizar_unidad(p["origen"])
    datos = {"origen": origen, "tabla": tabla_equivalencias(valor, origen)}
    if p.get("destino"):
        destino = normalizar_unidad(p["destino"])
        datos["destino"] = destino
        datos["resultado"] = convertir(valor, origen, destino)
    return datos


def psicrometria(**p) -> dict:
    altitud = float(p.get("altitud", 0) or 0)
    presion = presion_por_altitud(altitud)
    tbs = float(p["tbs"])
    if p.get("modo", "hr") == "hr":
        estado = estado_desde_hr(tbs, float(p["valor"]), presion)
    else:
        estado = estado_desde_bulbo_humedo(tbs, float(p["valor"]), presion)
    datos = asdict(estado)
    datos["w_g_kg"] = estado.w_g_kg
    return datos


def ductos(**p) -> dict:
    """Dimensiona (modo "dimensionar") o verifica (modo "verificar") un ducto.

    Las medidas de entrada y salida están en ``unidad_medida`` (cm o mm).
    """
    caudal = float(p["caudal"])
    if p.get("unidad", "m3/h") == "CFM":
        caudal *= CFM_A_M3H
    unidad = p.get("unidad_medida", "cm")
    tipo = p.get("tipo", "principal")
    en_unidad = lambda m: m / UNIDADES_MEDIDA[unidad]  # noqa: E731
    base = {
        "unidad_medida": unidad,
        "caudal_m3h": caudal,
        "caudal_cfm": caudal / CFM_A_M3H,
        "rango_velocidad": list(VELOCIDADES_RECOMENDADAS[tipo]),
    }

    modo = p.get("modo", "dimensionar")
    dim_ancho, dim_alto = p.get("dim_ancho"), p.get("dim_alto")
    if modo == "dimensionar" and dim_ancho and dim_alto:
        # Con ambas medidas no hay nada que dimensionar: se verifica ese ducto.
        modo, p = "verificar", {**p, "forma": "rectangular", "ancho": dim_ancho, "alto": dim_alto}
        base["desde_dimensionar"] = True

    if modo == "verificar":
        if p.get("forma", "rectangular") == "rectangular":
            v = verificar(
                caudal,
                ancho_m=a_metros(float(p["ancho"]), unidad),
                alto_m=a_metros(float(p["alto"]), unidad),
            )
        else:
            v = verificar(caudal, diametro_m=a_metros(float(p["diametro"]), unidad))
        sugerido = tamano_recomendado(v, tipo)
        if sugerido:
            # "ancho_m" -> "ancho" (en la unidad elegida), etc.
            sugerido = {
                (k[:-2] if k.endswith("_m") else k): (en_unidad(x) if k.endswith("_m") else x)
                for k, x in sugerido.items()
            }
        return {
            **base,
            "modo": "verificar",
            "forma": v.forma,
            "ancho": en_unidad(v.ancho_m) if v.ancho_m else None,
            "alto": en_unidad(v.alto_m) if v.alto_m else None,
            "diametro": en_unidad(v.diametro_m),
            "area_m2": v.area_m2,
            "velocidad_ms": v.velocidad_ms,
            "friccion_pa_m": v.friccion_pa_m,
            "avisos": advertencias(v, tipo),
            "sugerido": sugerido,
        }

    valor = float(p["valor"])
    r = dimensionar(
        caudal,
        velocidad=valor if p.get("metodo", "velocidad") == "velocidad" else None,
        friccion=valor if p.get("metodo") == "friccion" else None,
        alto_m=a_metros(float(dim_alto), unidad) if dim_alto else None,
        ancho_m=a_metros(float(dim_ancho), unidad) if dim_ancho else None,
    )
    ancho_c, alto_c = r.rectangular_comercial_mm
    return {
        **base,
        "modo": "dimensionar",
        "diametro": en_unidad(r.diametro_m),
        "diametro_comercial": en_unidad(r.diametro_comercial_mm / 1000),
        "ancho": en_unidad(r.ancho_m),
        "alto": en_unidad(r.alto_m),
        "rectangular_comercial": [en_unidad(ancho_c / 1000), en_unidad(alto_c / 1000)],
        "lado_fijo": r.lado_fijo,
        "velocidad_ms": r.velocidad_ms,
        "velocidad_rectangular_ms": r.velocidad_rectangular_ms,
        "friccion_pa_m": r.friccion_pa_m,
        "avisos": advertencias(r, tipo),
    }


def _uso(p: dict) -> dict:
    return {
        "horas_dia": float(p.get("horas", 8)),
        "dias_mes": float(p.get("dias", 30)),
        "meses_anio": float(p.get("meses", 12)),
        "tarifa_kwh": float(p.get("tarifa", 0.15)),
        "factor_uso": float(p.get("factor_uso", 1.0)),
    }


def consumo(**p) -> dict:
    c = calcular_consumo(
        float(p["capacidad"]), float(p["eficiencia"]), p.get("tipo", "SEER"), **_uso(p)
    )
    return asdict(c)


def comparar(**p) -> dict:
    r = comparar_equipos(
        float(p["capacidad"]),
        float(p["eficiencia_a"]),
        float(p["precio_a"]),
        float(p["eficiencia_b"]),
        float(p["precio_b"]),
        tipo_a=p.get("tipo_a", "SEER"),
        tipo_b=p.get("tipo_b", "SEER"),
        **_uso(p),
    )
    return {
        "equipo_a": asdict(r.equipo_a),
        "equipo_b": asdict(r.equipo_b),
        "ahorro_anual": r.ahorro_anual,
        "diferencia_precio": r.diferencia_precio,
        "retorno_anios": r.retorno_anios,
    }


FUNCIONES = {
    "unidades": unidades,
    "carga": carga,
    "conversor": conversor,
    "psicrometria": psicrometria,
    "ductos": ductos,
    "consumo": consumo,
    "comparar": comparar,
}


def ejecutar(nombre: str, params_json: str = "{}") -> str:
    """Punto de entrada para JavaScript: devuelve JSON con ``ok`` y ``datos`` o ``error``."""
    try:
        datos = FUNCIONES[nombre](**json.loads(params_json or "{}"))
        return json.dumps({"ok": True, "datos": datos})
    except (ValueError, TypeError, KeyError) as error:
        mensaje = str(error)
        if isinstance(error, KeyError):
            mensaje = f"Falta el dato {mensaje}"
        return json.dumps({"ok": False, "error": mensaje})
