import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from data_loader import (
    normalize_name_key, clean_text_encoding,
    load_batting, load_pitching, load_fielding, load_sprint,
    load_batting_expected, load_pitching_expected,
    load_batting_exitvelo, load_pitching_exitvelo,
    get_player_data, detect_role
)
from components import (
    build_radar, build_comparison_table, build_comparison_image,
    _winner, _fmt, _fetch_headshot_image
)

_REP = chr(0xFFFD)


class TestVision360(unittest.TestCase):

    def test_accented_and_mojibake_normalization(self):
        """Valida que nombres con acentos, eñes y mojibake coincidan al 100%."""
        test_cases = [
            ("Ronald Acuña Jr.", f"Acu{_REP}a Jr., Ronald"),
            ("Ronald Acuna", "Acuña, Ronald"),
            ("Jesús Luzardo", f"Luzardo, Jes{_REP}s"),
            ("Cristopher Sánchez", f"S{_REP}nchez, Cristopher"),
            ("Iván Herrera", f"Herrera, Iv{_REP}n"),
            ("Luis Arraez", "Arraez, Luis"),
            ("Andrés Giménez", f"Gim{_REP}nez, Andr{_REP}s"),
            ("José Altuve", f"Altuve, Jos{_REP}"),
            ("Lourdes Gurriel Jr.", "Gurriel Jr., Lourdes"),
            ("Yordan Alvarez", "Alvarez, Yordan"),
            ("Salvador Perez", "Perez, Salvador"),
            ("Ezequiel Tovar", "Tovar, Ezequiel"),
            ("Wilyer Abreu", "Abreu, Wilyer"),
            ("Teoscar Hernández", f"Hern{_REP}ndez, Teoscar"),
            ("Gleyber Torres", "Torres, Gleyber"),
        ]

        for clean_name, corrupt_name in test_cases:
            norm_clean = normalize_name_key(clean_name)
            norm_corrupt = normalize_name_key(corrupt_name)
            self.assertEqual(
                norm_clean, norm_corrupt,
                f"Mismatch: '{clean_name}' ({norm_clean}) != '{corrupt_name}' ({norm_corrupt})"
            )

    def test_dataset_loading_and_shape(self):
        """Valida que todos los datasets en data/ estén presentes y no vacíos."""
        bat_df = load_batting()
        pit_df = load_pitching()
        field_df = load_fielding()
        sprint_df = load_sprint()
        bat_exp = load_batting_expected()
        pit_exp = load_pitching_expected()

        self.assertFalse(bat_df.empty, "batting.csv no debe estar vacío")
        self.assertFalse(pit_df.empty, "pitching.csv no debe estar vacío")
        self.assertFalse(field_df.empty, "fielding.csv no debe estar vacío")
        self.assertFalse(sprint_df.empty, "sprint.csv no debe estar vacío")
        self.assertFalse(bat_exp.empty, "batting_expected.csv no debe estar vacío")
        self.assertFalse(pit_exp.empty, "pitching_expected.csv no debe estar vacío")

    def test_player_data_and_mlbid_resolution(self):
        """Valida que jugadores resuelvan su mlbID, headshot y métricas Statcast."""
        bat_df = load_batting()
        pit_df = load_pitching()
        field_df = load_fielding()
        sprint_df = load_sprint()
        bat_exp = load_batting_expected()
        pit_exp = load_pitching_expected()
        bat_ev = load_batting_exitvelo()
        pit_ev = load_pitching_exitvelo()

        p1 = "James Wood"
        d1 = get_player_data(p1, bat_df, pit_df, field_df, sprint_df, bat_exp, pit_exp, bat_ev, pit_ev)

        self.assertEqual(d1["role"], "batter")
        self.assertEqual(d1["mlbID"], 695578)
        self.assertIn("https://img.mlbstatic.com", str(d1["headshot_url"]))
        self.assertIsNotNone(d1["batting"].get("V_xBA"))
        self.assertIsNotNone(d1["batting"].get("V_xwOBA"))
        self.assertIsNotNone(d1["batting"].get("V_EV"))
        self.assertIsNotNone(d1["sprint"].get("sprint_speed"))

    def test_radar_labels(self):
        """Valida que los ejes del radar muestren etiquetas amigables."""
        bat_df = load_batting()
        pit_df = load_pitching()
        field_df = load_fielding()
        sprint_df = load_sprint()

        d1 = get_player_data("James Wood", bat_df, pit_df, field_df, sprint_df)
        d2 = get_player_data("Zach Neto", bat_df, pit_df, field_df, sprint_df)

        fig = build_radar(d1, d2, "James Wood", "Zach Neto", "batter")
        theta = fig.data[0].theta

        self.assertIn("xwOBA", theta)
        self.assertIn("Exit Velo", theta)
        self.assertNotIn("P_xwOBA", theta)
        self.assertNotIn("P_Barrel", theta)

    def test_winner_logic_and_ties(self):
        """Valida que _winner asigne ventajas y reporte 'Igual' en empates."""
        self.assertEqual(_winner(0.300, 0.300, True, "P1", "P2"), "Igual")
        self.assertEqual(_winner(0.350, 0.300, True, "P1", "P2"), "P1")
        self.assertEqual(_winner(0.300, 0.350, True, "P1", "P2"), "P2")
        self.assertEqual(_winner(3.10, 3.10, False, "P1", "P2"), "Igual")
        self.assertEqual(_winner(2.50, 3.80, False, "P1", "P2"), "P1")
        self.assertEqual(_winner(4.20, 3.10, False, "P1", "P2"), "P2")

    def test_comparison_table_360(self):
        """Valida que la tabla comparativa contenga las 6 dimensiones analíticas."""
        bat_df = load_batting()
        pit_df = load_pitching()
        field_df = load_fielding()
        sprint_df = load_sprint()
        bat_exp = load_batting_expected()
        pit_exp = load_pitching_expected()
        bat_ev = load_batting_exitvelo()
        pit_ev = load_pitching_exitvelo()

        d1 = get_player_data("James Wood", bat_df, pit_df, field_df, sprint_df, bat_exp, pit_exp, bat_ev, pit_ev)
        d2 = get_player_data("Zach Neto", bat_df, pit_df, field_df, sprint_df, bat_exp, pit_exp, bat_ev, pit_ev)

        comp_df = build_comparison_table(d1, d2, "James Wood", "Zach Neto", "batter")
        cats = comp_df["Categoría"].unique().tolist()

        self.assertIn("Tradicional (Rate)", cats)
        self.assertIn("Volumen", cats)
        self.assertIn("Statcast Esperado", cats)
        self.assertIn("Diferenciales", cats)
        self.assertIn("Defensa", cats)
        self.assertIn("Velocidad", cats)
        self.assertGreaterEqual(len(comp_df), 20)

    def test_png_matchup_generation_with_photos(self):
        """Valida que el PNG descargable se genere con fotos válidas."""
        bat_df = load_batting()
        pit_df = load_pitching()
        field_df = load_fielding()
        sprint_df = load_sprint()
        bat_exp = load_batting_expected()
        pit_exp = load_pitching_expected()
        bat_ev = load_batting_exitvelo()
        pit_ev = load_pitching_exitvelo()

        d1 = get_player_data("James Wood", bat_df, pit_df, field_df, sprint_df, bat_exp, pit_exp, bat_ev, pit_ev)
        d2 = get_player_data("Zach Neto", bat_df, pit_df, field_df, sprint_df, bat_exp, pit_exp, bat_ev, pit_ev)

        comp_df = build_comparison_table(d1, d2, "James Wood", "Zach Neto", "batter")
        img_bytes = build_comparison_image(d1, d2, "James Wood", "Zach Neto", "batter", comp_df)

        self.assertIsInstance(img_bytes, bytes)
        self.assertGreater(len(img_bytes), 20000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
