# Dimensionamiento y verificación de ductos de aire

Dos herramientas en una:

1. **Dimensionar** un ducto nuevo para un caudal de aire: tamaño circular y
   rectangular equivalente, con medidas comerciales sugeridas.
2. **Verificar** un ducto existente o propuesto: a partir de sus medidas
   calcula la velocidad real del aire y la pérdida por fricción. Si el ducto es
   demasiado pequeño, avisa del ruido en difusores y rejillas y sugiere el
   tamaño mínimo recomendado.

Las medidas del ducto se ingresan y se muestran en **centímetros** (por
defecto) o en milímetros (`--unidad-medida mm`).

## Métodos

- **Por velocidad**: se fija la velocidad del aire (m/s), `A = Q / V`.
- **Por fricción constante** (*equal friction*): se fija la pérdida por
  fricción (Pa/m) y se busca el diámetro que la produce.
- **Verificación**: velocidad real `V = Q / (ancho × alto)` y fricción con el
  diámetro equivalente. El tamaño sugerido conserva el alto del ducto
  (normalmente limitado por el cielo raso) y agranda el ancho hasta quedar
  dentro de la velocidad máxima del tramo.

Fórmulas (ASHRAE Fundamentals, cap. 21):

- Pérdida por fricción: Darcy-Weisbach, `Δp/L = f/D · ρV²/2`.
- Factor de fricción: ecuación de Colebrook (acero galvanizado, ε = 0,09 mm).
- Rectangular equivalente: Huebscher, `De = 1,30·(a·b)^0,625 / (a+b)^0,25`.
- Aire estándar: 1,204 kg/m³, 20 °C.

Las medidas comerciales se redondean hacia arriba en pasos de 5 cm (50 mm).

## Verificar un ducto existente

Ejemplo de revisión técnica: ¿sirve un ducto de **20 × 30 cm** para
**3 000 m³/h**?

```bash
python ductos/ductos.py --caudal 3000 --medida 20 30
```

```
Caudal               3,000 m³/h (1,766 CFM)
Ducto                20 x 30 cm (Ø equivalente 26.6 cm)
Área libre           0.0600 m²
Velocidad del aire   13.89 m/s  (recomendado 5-8 m/s, tramo principal)
Pérdida por fricción 8.801 Pa/m
AVISO: Velocidad 13.9 m/s muy por encima del máximo recomendado (8 m/s) para tramo principal: ducto demasiado pequeño, generará ruido en difusores y rejillas.
AVISO: Pérdida por fricción alta (8.8 Pa/m > 2 Pa/m): el ventilador necesitará más presión.
Tamaño mínimo recomendado: 35 x 30 cm -> 7.9 m/s
```

No sirve: el aire va a casi 14 m/s. Con el mismo alto de 30 cm, el ducto debe
tener al menos 35 cm de ancho.

Un ducto adecuado:

```bash
python ductos/ductos.py --caudal 1000 --medida 30 20 --tipo ramal
```

```
Caudal               1,000 m³/h (589 CFM)
Ducto                30 x 20 cm (Ø equivalente 26.6 cm)
Área libre           0.0600 m²
Velocidad del aire   4.63 m/s  (recomendado 3-5 m/s, tramo ramal)
Pérdida por fricción 1.123 Pa/m
Resultado: ducto adecuado para este caudal.
```

Ducto circular en milímetros:

```bash
python ductos/ductos.py --caudal 800 --diametro 200 --unidad-medida mm --tipo ramal
# Velocidad del aire 7.07 m/s ... Tamaño mínimo recomendado: Ø 250 mm -> 4.5 m/s
```

## Dimensionar un ducto nuevo

Por velocidad:

```bash
python ductos/ductos.py --caudal 1000 --velocidad 5
```

```
Caudal               1,000 m³/h (589 CFM)
Diámetro calculado   26.6 cm  -> comercial 30 cm
Rectangular          29.9 x 20 cm  -> comercial 30 x 20 cm
Velocidad            5.00 m/s
Pérdida por fricción 1.132 Pa/m
```

Por fricción, caudal en CFM y relación de aspecto 2:1:

```bash
python ductos/ductos.py --caudal 600 --unidad CFM --friccion 0.8 --relacion 2
```

```
Caudal               1,019 m³/h (600 CFM)
Diámetro calculado   28.8 cm  -> comercial 30 cm
Rectangular          37.7 x 18.9 cm  -> comercial 40 x 20 cm
Velocidad            4.36 m/s
Pérdida por fricción 0.800 Pa/m
AVISO: Velocidad 4.4 m/s menor que la recomendada (5 m/s) para tramo principal: ducto sobredimensionado.
```

Con alto fijo (por ejemplo, un cielo raso que solo deja 15 cm):

```bash
python ductos/ductos.py --caudal 1000 --velocidad 5 --alto 15
# Rectangular  42.1 x 15 cm  -> comercial 45 x 15 cm
```

## Opciones

| Opción | Descripción | Por defecto |
|---|---|---|
| `--caudal` | Caudal de aire (obligatorio) | — |
| `--unidad` | Unidad del caudal: `m3/h` o `CFM` | `m3/h` |
| `--unidad-medida` | Unidad de las medidas del ducto: `cm` o `mm` | `cm` |
| `--velocidad` | Dimensionar con esta velocidad en m/s | — |
| `--friccion` | Dimensionar con esta pérdida por fricción en Pa/m | — |
| `--medida ANCHO ALTO` | Verificar un ducto rectangular existente | — |
| `--diametro` | Verificar un ducto circular existente | — |
| `--relacion` | Relación ancho/alto al dimensionar | 1.5 |
| `--alto` | Alto fijo al dimensionar (alternativa a `--relacion`) | — |
| `--tipo` | `residencial`, `principal`, `ramal`, `retorno` | `principal` |

Se usa una sola de `--velocidad`, `--friccion`, `--medida` o `--diametro`.

Velocidades recomendadas para bajo ruido (m/s): residencial 2,5–5 ·
principal 5–8 · ramal 3–5 · retorno 2,5–5. Por encima del máximo, el ducto
genera ruido en difusores y rejillas; por debajo del mínimo, está
sobredimensionado (más material y espacio del necesario).

## Como librería

```python
from ductos.ductos import a_metros, advertencias, dimensionar, tamano_recomendado, verificar

# Verificar 3000 m³/h en un ducto de 20 x 30 cm
v = verificar(3000, ancho_m=a_metros(20, "cm"), alto_m=a_metros(30, "cm"))
print(round(v.velocidad_ms, 1), advertencias(v, "principal"), tamano_recomendado(v, "principal"))

# Dimensionar un ramal por fricción
r = dimensionar(1500, friccion=0.8, relacion=2)
print(r.diametro_comercial_mm, r.rectangular_comercial_mm)
```

## Tests

```bash
python -m unittest ductos.test_ductos -v
```
