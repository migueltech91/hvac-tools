import math
import unittest

from ductos.ductos import (
    advertencias,
    diametro_equivalente,
    dimensionar,
    factor_friccion,
    perdida_por_friccion,
    rectangular_por_alto,
    rectangular_por_relacion,
    redondear_comercial,
)


class TestDuctos(unittest.TestCase):
    def test_metodo_velocidad(self):
        r = dimensionar(1000, velocidad=5)
        self.assertAlmostEqual(r.diametro_m, 0.2660, places=4)
        self.assertAlmostEqual(r.velocidad_ms, 5.0, places=6)
        self.assertEqual(r.diametro_comercial_mm, 300)

    def test_metodo_friccion_consistente(self):
        r = dimensionar(1000, friccion=1.0)
        self.assertAlmostEqual(r.friccion_pa_m, 1.0, places=4)
        # Orden de magnitud del ábaco ASHRAE (~280 L/s a 1 Pa/m ≈ 280 mm).
        self.assertTrue(0.25 < r.diametro_m < 0.31, r.diametro_m)

    def test_factor_friccion(self):
        self.assertAlmostEqual(factor_friccion(1000, 0.2), 0.064)
        f = factor_friccion(1e5, 0.3)
        self.assertTrue(0.017 < f < 0.022, f)

    def test_friccion_disminuye_con_diametro(self):
        q = 0.3
        self.assertGreater(perdida_por_friccion(q, 0.25), perdida_por_friccion(q, 0.35))

    def test_equivalencia_rectangular(self):
        ancho, alto = rectangular_por_relacion(0.3, 2)
        self.assertAlmostEqual(ancho / alto, 2)
        self.assertAlmostEqual(diametro_equivalente(ancho, alto), 0.3, places=6)
        # Un ducto cuadrado equivale a un diámetro ~1.09 veces el lado.
        self.assertAlmostEqual(diametro_equivalente(0.3, 0.3) / 0.3, 1.093, places=3)

    def test_alto_fijo(self):
        ancho = rectangular_por_alto(0.3, 0.2)
        self.assertAlmostEqual(diametro_equivalente(ancho, 0.2), 0.3, places=6)
        r = dimensionar(1000, velocidad=5, alto_m=0.2)
        self.assertAlmostEqual(r.alto_m, 0.2)

    def test_redondeo_comercial(self):
        self.assertEqual(redondear_comercial(0.266), 300)
        self.assertEqual(redondear_comercial(0.300), 300)
        self.assertEqual(redondear_comercial(0.301), 350)

    def test_advertencias(self):
        rapido = dimensionar(3000, velocidad=10)
        self.assertTrue(any("ruido" in a for a in advertencias(rapido, "principal")))
        lento = dimensionar(500, velocidad=2)
        self.assertTrue(any("sobredimensionado" in a for a in advertencias(lento, "ramal")))
        normal = dimensionar(1000, velocidad=6)
        self.assertEqual(advertencias(normal, "principal"), [])
        # En el límite exacto del rango no debe haber aviso.
        self.assertEqual(advertencias(dimensionar(1000, velocidad=5), "principal"), [])

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            dimensionar(1000)
        with self.assertRaises(ValueError):
            dimensionar(1000, velocidad=5, friccion=1)
        with self.assertRaises(ValueError):
            dimensionar(-5, velocidad=5)
        with self.assertRaises(ValueError):
            rectangular_por_relacion(0.3, 0.5)

    def test_area_coherente(self):
        r = dimensionar(3600, velocidad=4)
        self.assertAlmostEqual(math.pi * r.diametro_m**2 / 4, 0.25, places=6)


if __name__ == "__main__":
    unittest.main()
