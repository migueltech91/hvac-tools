# Conversor de unidades HVAC

Convierte entre las unidades que se usan a diario en climatización y
refrigeración, tanto del sistema métrico como del sistema inglés.

| Magnitud | Unidades |
|---|---|
| Potencia térmica | W, kW, BTU/h, MBH, TR (tonelada de refrigeración), kcal/h, HP |
| Caudal de aire | m3/s, m3/h, L/s, CFM |
| Presión | Pa, kPa, bar, psi, inH2O, mmH2O, mmHg, inHg |
| Energía | J, kJ, Wh, kWh, BTU, kcal |
| Temperatura | C, F, K |

No distingue mayúsculas y acepta alias comunes: `btuh`, `ton`, `toneladas`,
`pcm`, `°C`, `inwc`, `mmca`…

## Uso

```bash
python conversor_unidades/conversor_unidades.py 12000 BTU/h TR
# 12,000 BTU/h = 1 TR

python conversor_unidades/conversor_unidades.py 1500 CFM m3/h
# 1,500 CFM = 2,548.5162 m3/h

python conversor_unidades/conversor_unidades.py 24 C F
# 24 C = 75.2 F
```

Si se omite la unidad de destino, muestra todas las equivalencias:

```
$ python conversor_unidades/conversor_unidades.py 18000 BTU/h
        5,275.2793  W
            5.2753  kW
            18,000  BTU/h
                18  MBH
               1.5  TR
        4,535.9237  kcal/h
            7.0743  HP
```

Para ver todas las unidades: `python conversor_unidades/conversor_unidades.py --listar`

## Como librería

```python
from conversor_unidades.conversor_unidades import convertir, tabla_equivalencias

convertir(1, "TR", "kW")          # 3.5168528
convertir(0.5, "inH2O", "Pa")     # 124.544455
tabla_equivalencias(1000, "CFM")  # {'m3/s': ..., 'm3/h': ..., 'L/s': ..., 'CFM': 1000.0}
```

Si se mezclan magnitudes (por ejemplo, CFM a kW) o se usa una unidad
desconocida, lanza `ValueError` con un mensaje claro.

## Tests

```bash
python -m unittest conversor_unidades.test_conversor_unidades -v
```
