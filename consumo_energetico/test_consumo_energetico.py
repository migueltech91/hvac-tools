import unittest

from consumo_energetico.consumo_energetico import (
    calcular_consumo,
    comparar_equipos,
    eer_equivalente,
    informe_comparacion,
)


class TestConsumo(unittest.TestCase):
    def test_split_12000_seer_13(self):
        c = calcular_consumo(12000, 13, "SEER", horas_dia=8, tarifa_kwh=0.15)
        self.assertAlmostEqual(c.potencia_kw, 0.9231, places=4)
        self.assertAlmostEqual(c.kwh_dia, 7.3846, places=4)
        self.assertAlmostEqual(c.kwh_mes, 221.54, places=2)
        self.assertAlmostEqual(c.costo_mes, 33.23, places=2)
        self.assertAlmostEqual(c.costo_anual, c.costo_mes * 12)

    def test_equivalencias_eficiencia(self):
        self.assertAlmostEqual(eer_equivalente(3.0, "COP"), 10.2364, places=4)
        self.assertAlmostEqual(eer_equivalente(1.0, "kW/TR"), 12.0)
        self.assertEqual(eer_equivalente(11, "EER"), 11)

    def test_cop_y_kw_tr_dan_misma_potencia(self):
        # 1 TR con 1 kW/TR consume 1 kW.
        c = calcular_consumo(12000, 1.0, "kW/TR")
        self.assertAlmostEqual(c.potencia_kw, 1.0)

    def test_factor_uso(self):
        completo = calcular_consumo(12000, 13)
        mitad = calcular_consumo(12000, 13, factor_uso=0.5)
        self.assertAlmostEqual(mitad.kwh_mes, completo.kwh_mes / 2)

    def test_comparacion_y_retorno(self):
        r = comparar_equipos(18000, 13, 450, 22, 750, horas_dia=10, tarifa_kwh=0.18)
        self.assertGreater(r.ahorro_anual, 0)
        self.assertAlmostEqual(r.diferencia_precio, 300)
        self.assertAlmostEqual(r.retorno_anios, 300 / r.ahorro_anual)
        self.assertIn("recuperado", informe_comparacion(r))

    def test_equipo_eficiente_mas_barato(self):
        r = comparar_equipos(12000, 13, 600, 18, 500)
        self.assertEqual(r.retorno_anios, 0.0)

    def test_nunca_se_recupera(self):
        r = comparar_equipos(12000, 18, 400, 13, 600)
        self.assertIsNone(r.retorno_anios)

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            calcular_consumo(0, 13)
        with self.assertRaises(ValueError):
            calcular_consumo(12000, 13, horas_dia=25)
        with self.assertRaises(ValueError):
            calcular_consumo(12000, 13, "XYZ")
        with self.assertRaises(ValueError):
            calcular_consumo(12000, -1)


if __name__ == "__main__":
    unittest.main()
