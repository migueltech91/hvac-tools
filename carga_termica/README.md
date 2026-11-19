# Calculadora de carga térmica (BTU/h)

Estima la capacidad de aire acondicionado que necesita un ambiente
(dormitorio, oficina, local pequeño) y sugiere la capacidad comercial del
equipo: 9 000, 12 000, 18 000, 24 000 BTU/h, etc.

## Método

Método simplificado por factores, habitual para presupuestar equipos split:

| Componente | Cálculo |
|---|---|
| Envolvente (muros, techo, infiltración) | área (m²) × factor de clima × altura / 2,5 m |
| Ventanas | área de vidrio (m²) × factor de exposición solar |
| Personas | cantidad × factor de actividad (calor sensible + latente) |
| Equipos e iluminación | potencia (W) × 3,412 BTU/h |
| Seguridad | 10 % del subtotal (configurable) |

Factores utilizados:

- **Clima** (BTU/h por m²): templado 450 · cálido 550 · muy cálido 650
- **Exposición de ventanas** (BTU/h por m² de vidrio): sombra 80 · baja 160 · media 320 · alta 550
- **Actividad** (BTU/h por persona): sedentaria 450 · ligera 600 · intensa 1 000

> Es una estimación preliminar. Para proyectos formales corresponde un cálculo
> detallado (ASHRAE, Manual J / N).

## Uso

```bash
python carga_termica/carga_termica.py --area 20 --personas 2 --ventanas 3 \
    --exposicion media --equipos 400 --clima calido
```

Salida:

```
Desglose de carga térmica
----------------------------------
Envolvente          11,000 BTU/h
Ventanas               960 BTU/h
Personas               900 BTU/h
Equipos              1,365 BTU/h
Seguridad            1,422 BTU/h
----------------------------------
TOTAL               15,647 BTU/h
                      4.59 kW
                      1.30 TR

Equipo sugerido: 18,000 BTU/h (1.5 TR)
```

Opciones (`--help`):

| Opción | Descripción | Por defecto |
|---|---|---|
| `--area` | Área del piso en m² (obligatoria) | — |
| `--altura` | Altura del ambiente en m | 2.5 |
| `--clima` | `templado`, `calido`, `muy_calido` | `calido` |
| `--personas` | Número de ocupantes | 1 |
| `--actividad` | `sedentaria`, `ligera`, `intensa` | `sedentaria` |
| `--ventanas` | Área de vidrio en m² | 0 |
| `--exposicion` | `sombra`, `baja`, `media`, `alta` | `media` |
| `--equipos` | Potencia de equipos e iluminación en W | 0 |
| `--seguridad` | Factor de seguridad (0.10 = 10 %) | 0.10 |

## Como librería

```python
from carga_termica.carga_termica import Ambiente, calcular_carga

r = calcular_carga(Ambiente(area_m2=12, personas=1))
print(r.total_btu_h, r.equipo_sugerido_btu_h)   # 7755.0 9000
```

## Tests

```bash
python -m unittest carga_termica.test_carga_termica -v
```
