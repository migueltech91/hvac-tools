# HVAC Tools · Herramientas de climatización en Python

[![Tests](https://github.com/migueltech91/hvac-tools/actions/workflows/tests.yml/badge.svg)](https://github.com/migueltech91/hvac-tools/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green)

Colección de **programas de cálculo para HVAC** (calefacción, ventilación y aire
acondicionado) desarrollados en Python. Es mi portafolio para mostrar cómo
convierto fórmulas de ingeniería en software claro, probado y fácil de usar.

### ▶ [Probar la demo en vivo](https://migueltech91.github.io/hvac-tools/)

Las cinco calculadoras funcionan en el navegador, sin instalar nada: la página
ejecuta este mismo código Python con [Pyodide](https://pyodide.org)
(Python compilado a WebAssembly).

> ¿Necesitas una calculadora, un script de automatización o una herramienta a
> medida para tu empresa de climatización, refrigeración o mantenimiento?
> Escríbeme por **Workana** y lo adaptamos a tu flujo de trabajo.

## Programas incluidos

| Programa | ¿Qué resuelve? | Ejemplo |
|---|---|---|
| [Carga térmica](carga_termica/) | Cuántos BTU/h necesita un ambiente y qué equipo comprar | Dormitorio de 12 m² → split de 9 000 BTU/h |
| [Conversor de unidades](conversor_unidades/) | BTU/h ↔ kW ↔ TR, CFM ↔ m³/h, Pa ↔ inH₂O, °C ↔ °F… | 12 000 BTU/h = 1 TR = 3,52 kW |
| [Psicrometría](psicrometria/) | Propiedades del aire húmedo: rocío, bulbo húmedo, entalpía | 25 °C y 50 % HR → rocío 13,9 °C |
| [Ductos](ductos/) | Dimensiona ductos nuevos y verifica existentes (medidas en cm o mm): velocidad, fricción y riesgo de ruido | 3 000 m³/h en 20 × 30 cm → 13,9 m/s, ruidoso: usar 35 × 30 cm |
| [Consumo energético](consumo_energetico/) | kWh y costo mensual de un equipo; ahorro y retorno al cambiarlo | SEER 13 vs SEER 22 → retorno en años |

Cada carpeta tiene su propio README con la explicación del método, ejemplos de
uso y salida real del programa.

## Características

- **Sin dependencias externas**: solo la biblioteca estándar de Python.
- **Fórmulas de referencia**: ASHRAE Fundamentals (psicrometría, fricción en
  ductos, diámetro equivalente de Huebscher) y factores prácticos del rubro.
- **Probado**: 61 tests automáticos que corren en cada cambio
  (GitHub Actions, Windows y Linux).
- **Demo web**: interfaz en HTML/CSS/JS que llama al mismo código Python
  desde el navegador ([`web/`](web/), publicada con GitHub Pages).
- **Doble uso**: cada programa funciona desde la terminal y también como
  módulo importable para integrarlo en otros sistemas (web, Excel, APIs).
- **Validación de datos**: mensajes de error claros ante valores imposibles.

## Cómo usarlo

Requisitos: [Python 3.10 o superior](https://www.python.org/downloads/).

```bash
git clone https://github.com/migueltech91/hvac-tools.git
cd hvac-tools

# Carga térmica de una oficina de 20 m²
python carga_termica/carga_termica.py --area 20 --personas 2 --ventanas 3 --equipos 400

# Convertir 18 000 BTU/h a todas las unidades de potencia
python conversor_unidades/conversor_unidades.py 18000 BTU/h

# Propiedades del aire a 30 °C y 60 % de humedad en una ciudad a 1 500 m
python psicrometria/psicrometria.py --tbs 30 --hr 60 --altitud 1500

# Ducto para 1 200 CFM con pérdida de 1 Pa/m
python ductos/ductos.py --caudal 1200 --unidad CFM --friccion 1

# ¿Sirve un ducto de 20 x 30 cm para 3 000 m³/h?
python ductos/ductos.py --caudal 3000 --medida 20 30

# Costo mensual de un split de 12 000 BTU/h SEER 16, 8 h al día
python consumo_energetico/consumo_energetico.py calcular --capacidad 12000 --eficiencia 16 --horas 8 --tarifa 0.15
```

Todos los programas aceptan `--help` para ver sus opciones.

### Usarlo como librería

```python
from psicrometria.psicrometria import estado_desde_hr
from conversor_unidades.conversor_unidades import convertir

aire = estado_desde_hr(tbs=25, hr_pct=50)
print(f"Punto de rocío: {aire.rocio_c:.1f} °C")      # 13.9 °C
print(convertir(5, "TR", "kW"))                      # 17.58...
```

## Ejecutar los tests

```bash
python -m unittest discover -v
```

## Estructura

```
hvac-tools/
├── carga_termica/        # Carga térmica y selección de equipo
├── conversor_unidades/   # Conversión de unidades HVAC
├── psicrometria/         # Propiedades del aire húmedo
├── ductos/               # Dimensionamiento de ductos
├── consumo_energetico/   # Consumo, costo y retorno de inversión
├── web/                  # Demo web (Pyodide) + capa de integración api.py
├── index.html            # Página de la demo (GitHub Pages)
└── .github/workflows/    # Integración continua (tests automáticos)
```

## Cómo trabajo

Desarrollo con apoyo de herramientas de inteligencia artificial para programar
más rápido. Yo me encargo de lo que la IA no puede hacer: definir los métodos
de cálculo, validar los resultados con mi experiencia en el rubro HVAC y
corregir los errores técnicos antes de entregar.

En este repositorio, por ejemplo, la verificación de ductos existentes
(detectar que un ducto de 20 × 30 cm es demasiado pequeño para 3 000 m³/h y
generará ruido en difusores y rejillas) surgió de mi revisión técnica del
producto.

## Aviso

Estas herramientas sirven para estimaciones, presupuestos y aprendizaje. Para
proyectos formales, los resultados deben ser revisados por un profesional
habilitado y complementarse con un cálculo detallado según la normativa local.

## Licencia

[MIT](LICENSE) © 2026 migueltech91
