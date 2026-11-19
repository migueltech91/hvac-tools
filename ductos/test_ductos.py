import math
import unittest

from ductos.ductos import (
    a_metros,
    advertencias,
    diametro_equivalente,
    dimensionar,
    factor_friccion,
    formatear_medida,
    informe_verificacion,
    perdida_por_friccion,
    rectangular_por_alto,
    rectangular_por_relacion,
    redondear_comercial,
    tamano_recomendado,
    verificar,
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

    def test_verificar_ducto_pequeno_3000_m3h_20x30cm(self):
        # Caso de revisión técnica: 3000 m³/h en un ducto de 20 x 30 cm.
        v = verificar(3000, ancho_m=a_metros(20, "cm"), alto_m=a_metros(30, "cm"))
        self.assertAlmostEqual(v.area_m2, 0.06)
        self.assertAlmostEqual(v.velocidad_ms, 13.89, places=2)
        self.assertAlmostEqual(v.diametro_m, 0.2664, places=4)
        avisos = advertencias(v, "principal")
        self.assertTrue(any("ruido en difusores y rejillas" in a for a in avisos))
        self.assertTrue(any("fricción alta" in a for a in avisos))
        sugerido = tamano_recomendado(v, "principal")
        # Conserva el alto de 30 cm y agranda el ancho a 35 cm (7,9 m/s <= 8 m/s).
        self.assertEqual((sugerido["ancho_m"], sugerido["alto_m"]), (0.35, 0.30))
        self.assertLessEqual(sugerido["velocidad_ms"], 8.0)

    def test_verificar_ducto_adecuado(self):
        # 1000 m³/h en 30 x 20 cm: 4,6 m/s, dentro del rango de un ramal (3-5 m/s).
        v = verificar(1000, ancho_m=0.30, alto_m=0.20)
        self.assertAlmostEqual(v.velocidad_ms, 1000 / 3600 / 0.06)
        self.assertEqual(advertencias(v, "ramal"), [])
        self.assertIsNone(tamano_recomendado(v, "ramal"))
        self.assertIn("ducto adecuado", informe_verificacion(v, "ramal"))

    def test_verificar_circular(self):
        v = verificar(800, diametro_m=0.20)
        self.assertEqual(v.forma, "circular")
        self.assertAlmostEqual(v.velocidad_ms, 800 / 3600 / (math.pi * 0.01), places=6)
        sugerido = tamano_recomendado(v, "ramal")
        self.assertEqual(sugerido["forma"], "circular")
        self.assertLessEqual(sugerido["velocidad_ms"], 5.0)

    def test_verificar_validaciones(self):
        with self.assertRaises(ValueError):
            verificar(1000)
        with self.assertRaises(ValueError):
            verificar(1000, ancho_m=0.3)
        with self.assertRaises(ValueError):
            verificar(1000, ancho_m=0.3, alto_m=0.2, diametro_m=0.25)
        with self.assertRaises(ValueError):
            a_metros(10, "pulgadas")

    def test_medidas_en_cm_y_mm(self):
        self.assertAlmostEqual(a_metros(20, "cm"), 0.20)
        self.assertAlmostEqual(a_metros(200, "mm"), 0.20)
        self.assertEqual(formatear_medida(0.266, "cm"), "26.6")
        self.assertEqual(formatear_medida(0.30, "cm"), "30")
        self.assertEqual(formatear_medida(0.266, "mm"), "266")

    def test_area_coherente(self):
        r = dimensionar(3600, velocidad=4)
        self.assertAlmostEqual(math.pi * r.diametro_m**2 / 4, 0.25, places=6)


if __name__ == "__main__":
    unittest.main()
