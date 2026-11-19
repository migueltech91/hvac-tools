# Calculadora psicrométrica

Calcula las propiedades del aire húmedo, igual que leer una carta
psicrométrica pero con precisión numérica y para cualquier altitud.

**Entradas**: temperatura de bulbo seco + humedad relativa **o** bulbo húmedo.
Opcionalmente, presión atmosférica o altitud.

**Salidas**: humedad relativa, bulbo húmedo, punto de rocío, humedad absoluta
(relación de humedad), entalpía, volumen específico y densidad.

## Método

Ecuaciones del *ASHRAE Handbook – Fundamentals*, capítulo 1:

- Presión de saturación del vapor: Hyland-Wexler (sobre agua y sobre hielo).
- Relación de humedad: `W = 0,621945 · pv / (p − pv)`.
- Entalpía: `h = 1,006·t + W·(2501 + 1,86·t)` kJ/kg de aire seco.
- Bulbo húmedo y punto de rocío: se resuelven numéricamente (bisección).
- Presión según altitud: atmósfera estándar.

## Uso

```bash
python psicrometria/psicrometria.py --tbs 25 --hr 50
```

```
Bulbo seco          25.00 °C
Humedad relativa    50.0 %
Bulbo húmedo        17.89 °C
Punto de rocío      13.86 °C
Humedad absoluta    9.88 g/kg aire seco
Entalpía            50.32 kJ/kg aire seco
Volumen específico  0.8580 m³/kg aire seco
Densidad            1.1770 kg/m³
Presión             101.325 kPa
```

Con bulbo húmedo y altitud (por ejemplo, una ciudad a 1 500 m):

```bash
python psicrometria/psicrometria.py --tbs 30 --tbh 22 --altitud 1500
```

```
Bulbo seco          30.00 °C
Humedad relativa    52.1 %
Bulbo húmedo        22.00 °C
Punto de rocío      19.09 °C
Humedad absoluta    16.69 g/kg aire seco
Entalpía            72.87 kJ/kg aire seco
Volumen específico  1.0567 m³/kg aire seco
Densidad            0.9621 kg/m³
Presión             84.556 kPa
```

| Opción | Descripción |
|---|---|
| `--tbs` | Bulbo seco en °C (obligatoria) |
| `--hr` | Humedad relativa en % (o usar `--tbh`) |
| `--tbh` | Bulbo húmedo en °C (o usar `--hr`) |
| `--presion` | Presión atmosférica en kPa (por defecto 101.325) |
| `--altitud` | Altitud en m (alternativa a `--presion`) |

## Como librería

```python
from psicrometria.psicrometria import estado_desde_hr, presion_por_altitud

aire = estado_desde_hr(24, 55, presion_por_altitud(2240))
print(aire.rocio_c, aire.entalpia_kj_kg)
```

Aplicaciones típicas: verificar riesgo de condensación en ductos y
superficies frías, calcular calor sensible y latente en serpentines, y
analizar procesos de mezcla, enfriamiento o deshumidificación.

## Tests

```bash
python -m unittest psicrometria.test_psicrometria -v
```

Los tests comparan con valores de tablas ASHRAE y verifican la consistencia
entre los distintos métodos de entrada.
