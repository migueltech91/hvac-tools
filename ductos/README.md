# Dimensionamiento de ductos de aire

Calcula el tamaño de un ducto (circular y rectangular equivalente) para un
caudal de aire, con medidas comerciales sugeridas y avisos de diseño.

## Métodos

- **Por velocidad**: se fija la velocidad del aire (m/s) → `A = Q / V`.
- **Por fricción constante** (*equal friction*): se fija la pérdida por
  fricción (Pa/m) y se busca el diámetro que la produce.

Fórmulas (ASHRAE Fundamentals, cap. 21):

- Pérdida por fricción: Darcy-Weisbach, `Δp/L = f/D · ρV²/2`.
- Factor de fricción: ecuación de Colebrook (acero galvanizado, ε = 0,09 mm).
- Rectangular equivalente: Huebscher, `De = 1,30·(a·b)^0,625 / (a+b)^0,25`.
- Aire estándar: 1,204 kg/m³, 20 °C.

Las medidas comerciales se redondean hacia arriba en pasos de 50 mm.

## Uso

Por velocidad:

```bash
python ductos/ductos.py --caudal 1000 --velocidad 5
```

```
Caudal               1,000 m³/h (589 CFM)
Diámetro calculado   266 mm  -> comercial 300 mm
Rectangular          299 x 200 mm  -> comercial 300 x 200 mm
Velocidad            5.00 m/s
Pérdida por fricción 1.132 Pa/m
```

Por fricción, caudal en CFM y relación de aspecto 2:1:

```bash
python ductos/ductos.py --caudal 600 --unidad CFM --friccion 0.8 --relacion 2
```

```
Caudal               1,019 m³/h (600 CFM)
Diámetro calculado   288 mm  -> comercial 300 mm
Rectangular          377 x 189 mm  -> comercial 400 x 200 mm
Velocidad            4.36 m/s
Pérdida por fricción 0.800 Pa/m
AVISO: Velocidad 4.4 m/s menor que la recomendada (5.0 m/s) para tramo principal: ducto sobredimensionado.
```

Con alto fijo (por ejemplo, un cielo raso que solo deja 150 mm):

```bash
python ductos/ductos.py --caudal 1000 --velocidad 5 --alto 150
# Rectangular  421 x 150 mm  -> comercial 450 x 150 mm
```

| Opción | Descripción | Por defecto |
|---|---|---|
| `--caudal` | Caudal de aire (obligatorio) | — |
| `--unidad` | `m3/h` o `CFM` | `m3/h` |
| `--velocidad` | Velocidad en m/s (o usar `--friccion`) | — |
| `--friccion` | Pérdida por fricción en Pa/m | — |
| `--relacion` | Relación ancho/alto del ducto rectangular | 1.5 |
| `--alto` | Alto fijo en mm (alternativa a `--relacion`) | — |
| `--tipo` | `residencial`, `principal`, `ramal`, `retorno` (para los avisos) | `principal` |

Velocidades recomendadas usadas para los avisos (m/s): residencial 2,5–5 ·
principal 5–8 · ramal 3–5 · retorno 2,5–5.

## Como librería

```python
from ductos.ductos import dimensionar, advertencias

r = dimensionar(1500, friccion=0.8, relacion=2)
print(r.diametro_comercial_mm, r.rectangular_comercial_mm, advertencias(r, "ramal"))
```

## Tests

```bash
python -m unittest ductos.test_ductos -v
```
