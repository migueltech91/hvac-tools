import json
import unittest

from web.api import ejecutar


def llamar(nombre, **params):
    return json.loads(ejecutar(nombre, json.dumps(params)))


class TestApiWeb(unittest.TestCase):
    def test_unidades(self):
        r = llamar("unidades")
        self.assertTrue(r["ok"])
        self.assertIn("BTU/h", r["datos"]["potencia"])
        self.assertEqual(r["datos"]["temperatura"], ["C", "F", "K"])

    def test_carga(self):
        r = llamar("carga", area=12, personas=1)
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["datos"]["total_btu_h"], 7755.0)
        self.assertEqual(r["datos"]["equipo_btu_h"], 9000)

    def test_conversor(self):
        r = llamar("conversor", valor=12000, origen="BTU/h", destino="TR")
        self.assertAlmostEqual(r["datos"]["resultado"], 1.0, places=4)
        self.assertIn("kW", r["datos"]["tabla"])

    def test_psicrometria_hr_y_bulbo_humedo(self):
        hr = llamar("psicrometria", tbs=25, modo="hr", valor=50, altitud=0)["datos"]
        self.assertAlmostEqual(hr["rocio_c"], 13.86, places=1)
        tbh = llamar("psicrometria", tbs=25, modo="tbh", valor=hr["tbh_c"])["datos"]
        self.assertAlmostEqual(tbh["hr_pct"], 50, places=2)

    def test_ductos(self):
        r = llamar("ductos", caudal=1000, metodo="velocidad", valor=5)["datos"]
        self.assertEqual(r["diametro_comercial_mm"], 300)
        cfm = llamar("ductos", caudal=600, unidad="CFM", metodo="friccion", valor=0.8, relacion=2)
        self.assertAlmostEqual(cfm["datos"]["friccion_pa_m"], 0.8, places=3)

    def test_consumo_y_comparar(self):
        c = llamar("consumo", capacidad=12000, eficiencia=13, horas=8, tarifa=0.15)["datos"]
        self.assertAlmostEqual(c["costo_mes"], 33.23, places=2)
        k = llamar("comparar", capacidad=18000, eficiencia_a=13, precio_a=450,
                   eficiencia_b=22, precio_b=750, horas=10, tarifa=0.18)["datos"]
        self.assertGreater(k["ahorro_anual"], 0)

    def test_errores_legibles(self):
        r = llamar("psicrometria", tbs=20, modo="tbh", valor=25)
        self.assertFalse(r["ok"])
        self.assertIn("bulbo húmedo", r["error"])
        self.assertFalse(llamar("carga")["ok"])
        self.assertFalse(llamar("conversor", valor=1, origen="CFM", destino="kW")["ok"])


if __name__ == "__main__":
    unittest.main()
