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
from ductos.ductos import CFM_A_M3H, advertencias, dimensionar
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
    caudal = float(p["caudal"])
    if p.get("unidad", "m3/h") == "CFM":
        caudal *= CFM_A_M3H
    valor = float(p["valor"])
    alto_mm = p.get("alto_mm")
    r = dimensionar(
        caudal,
        velocidad=valor if p.get("metodo", "velocidad") == "velocidad" else None,
        friccion=valor if p.get("metodo") == "friccion" else None,
        relacion=float(p.get("relacion", 1.5) or 1.5),
        alto_m=float(alto_mm) / 1000 if alto_mm else None,
    )
    return {
        "caudal_m3h": r.caudal_m3h,
        "caudal_cfm": r.caudal_m3h / CFM_A_M3H,
        "diametro_mm": r.diametro_m * 1000,
        "diametro_comercial_mm": r.diametro_comercial_mm,
        "ancho_mm": r.ancho_m * 1000,
        "alto_mm": r.alto_m * 1000,
        "rectangular_comercial_mm": list(r.rectangular_comercial_mm),
        "velocidad_ms": r.velocidad_ms,
        "friccion_pa_m": r.friccion_pa_m,
        "avisos": advertencias(r, p.get("tipo", "principal")),
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
