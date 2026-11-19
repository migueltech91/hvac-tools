# Estimador de consumo energético de equipos de A/C

Calcula cuánto consume y cuánto cuesta por mes y por año un equipo de aire
acondicionado, y compara dos equipos para saber en cuánto tiempo se recupera
el sobrecosto del equipo más eficiente (inverter, SEER alto, etc.).

## Método

- Potencia eléctrica: `kW = capacidad (BTU/h) / EER / 1000`.
- Eficiencias aceptadas: **SEER**, **EER**, **COP** (× 3,412 → EER) y
  **kW/TR** (12 / kW/TR → EER).
- Consumo: `kWh = kW × horas/día × factor de uso × días × meses`.
- Retorno simple: `sobrecosto / ahorro anual`.

El *factor de uso* es la fracción del tiempo encendido en que trabaja el
compresor (1,0 = estimación conservadora).

## Uso

Consumo de un equipo:

```bash
python consumo_energetico/consumo_energetico.py calcular \
    --capacidad 12000 --eficiencia 13 --tipo SEER --horas 8 --tarifa 0.15
```

```
Potencia eléctrica   0.92 kW
Consumo diario       7.4 kWh
Consumo mensual      222 kWh  ->  $33.23
Consumo anual        2,658 kWh  ->  $398.77
```

Comparación de dos equipos (tipo de eficiencia, valor y precio de cada uno):

```bash
python consumo_energetico/consumo_energetico.py comparar \
    --capacidad 18000 --horas 10 --tarifa 0.18 \
    --equipo-a SEER 13 450 --equipo-b SEER 22 750
```

```
Equipo A
Potencia eléctrica   1.38 kW
Consumo diario       13.8 kWh
Consumo mensual      415 kWh  ->  $74.77
Consumo anual        4,985 kWh  ->  $897.23

Equipo B
Potencia eléctrica   0.82 kW
Consumo diario       8.2 kWh
Consumo mensual      245 kWh  ->  $44.18
Consumo anual        2,945 kWh  ->  $530.18

El equipo B ahorra $367.05 al año.
Sobrecosto de $300.00 recuperado en 0.8 años (10 meses).
```

| Opción | Descripción | Por defecto |
|---|---|---|
| `--capacidad` | Capacidad del equipo en BTU/h (obligatoria) | — |
| `--eficiencia` / `--tipo` | Valor y tipo: `SEER`, `EER`, `COP`, `kW/TR` | tipo `SEER` |
| `--horas` | Horas de uso por día | 8 |
| `--dias` | Días de uso por mes | 30 |
| `--meses` | Meses de uso por año | 12 |
| `--tarifa` | Costo por kWh | 0.15 |
| `--factor-uso` | Fracción de trabajo del compresor (0–1) | 1.0 |
| `--moneda` | Símbolo de moneda | `$` |

## Como librería

```python
from consumo_energetico.consumo_energetico import calcular_consumo, comparar_equipos

c = calcular_consumo(24000, 3.2, "COP", horas_dia=12, tarifa_kwh=0.20)
r = comparar_equipos(12000, 11, 380, 20, 620, tipo_a="EER", horas_dia=8)
print(c.costo_mes, r.retorno_anios)
```

## Tests

```bash
python -m unittest consumo_energetico.test_consumo_energetico -v
```
