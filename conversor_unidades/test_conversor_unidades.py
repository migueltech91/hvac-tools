import unittest

from conversor_unidades.conversor_unidades import (
    convertir,
    normalizar_unidad,
    tabla_equivalencias,
)


class TestConversor(unittest.TestCase):
    def test_tonelada_de_refrigeracion(self):
        self.assertAlmostEqual(convertir(12000, "BTU/h", "TR"), 1.0, places=4)
        self.assertAlmostEqual(convertir(1, "TR", "kW"), 3.5169, places=4)

    def test_caudal(self):
        self.assertAlmostEqual(convertir(1000, "CFM", "m3/h"), 1699.01, places=2)
        self.assertAlmostEqual(convertir(1, "m3/s", "L/s"), 1000.0)

    def test_presion(self):
        self.assertAlmostEqual(convertir(1, "inH2O", "Pa"), 249.089, places=3)
        self.assertAlmostEqual(convertir(1, "bar", "psi"), 14.5038, places=4)

    def test_temperatura(self):
        self.assertAlmostEqual(convertir(0, "C", "F"), 32.0)
        self.assertAlmostEqual(convertir(212, "F", "C"), 100.0)
        self.assertAlmostEqual(convertir(25, "C", "K"), 298.15)

    def test_ida_y_vuelta(self):
        valor = 18000
        self.assertAlmostEqual(convertir(convertir(valor, "BTU/h", "kW"), "kW", "BTU/h"), valor)

    def test_alias_y_mayusculas(self):
        self.assertEqual(normalizar_unidad("btuh"), "BTU/h")
        self.assertEqual(normalizar_unidad("cfm"), "CFM")
        self.assertEqual(normalizar_unidad("°C"), "C")
        self.assertEqual(normalizar_unidad("toneladas"), "TR")

    def test_magnitudes_incompatibles(self):
        with self.assertRaises(ValueError):
            convertir(1, "CFM", "kW")

    def test_unidad_desconocida(self):
        with self.assertRaises(ValueError):
            convertir(1, "furlong", "m3/h")

    def test_bajo_cero_absoluto(self):
        with self.assertRaises(ValueError):
            convertir(-300, "C", "K")

    def test_tabla_equivalencias(self):
        tabla = tabla_equivalencias(1, "TR")
        self.assertAlmostEqual(tabla["BTU/h"], 12000, places=1)
        self.assertIn("kcal/h", tabla)


if __name__ == "__main__":
    unittest.main()
