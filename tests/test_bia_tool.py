# -*- coding: utf-8 -*-
"""Tests automatiques de bia_tool.py. Lancer : python -m unittest discover -s tests -v"""
import os, sys, tempfile, time, unittest
import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
import bia_tool as b  # noqa: E402

DATA = os.path.join(RACINE, "data")
ESSAI = os.path.join(RACINE, "jeu_essai")


def lancer(matrice, cmdb, graphe=False):
    sortie = tempfile.mkdtemp()
    return b.executer(matrice, cmdb, sortie, avec_graphe=graphe)


class TestDonneesPrincipales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = lancer(os.path.join(DATA, "matrice_bia.csv"), os.path.join(DATA, "cmdb_ci.csv"))

    def test_aucune_incoherence(self):
        self.assertEqual(self.res["erreurs"], [])

    def test_quatorze_activites_et_35_ci(self):
        self.assertEqual(len(self.res["matrice"]), 14)
        self.assertGreaterEqual(len(self.res["cmdb"]), 25)  # exigence du sujet : au moins 25 CI

    def test_rto_strictement_inferieur_au_dmia(self):
        m = self.res["matrice"]
        self.assertTrue((m["rto_min"] < m["dmia_min"]).all())

    def test_rangs_uniques_et_ordre_par_dmia(self):
        p = self.res["priorites"]
        self.assertEqual(sorted(p["rang"]), list(range(1, 15)))
        self.assertTrue(p["dmia_min"].is_monotonic_increasing)

    def test_reanimation_est_la_premiere_priorite(self):
        self.assertEqual(self.res["priorites"].iloc[0]["id"], "A02")

    def test_classes(self):
        classes = self.res["priorites"].set_index("id")["classe"].to_dict()
        self.assertEqual((classes["A01"], classes["A06"], classes["A07"], classes["A09"]), ("P1", "P2", "P3", "P4"))

    def test_graphe_sans_cycle(self):
        import networkx as nx
        self.assertTrue(nx.is_directed_acyclic_graph(self.res["graphe"]))

    def test_alerte_dpi_pour_la_reanimation(self):
        a = self.res["alertes"]
        ligne = a[(a["id_activite"] == "A02") & (a["ci"] == "APP-DPI") & (a["nature"] == "RTO")]
        self.assertEqual(len(ligne), 1)
        self.assertEqual(float(ligne.iloc[0]["valeur_technique_min"]), 30.0)


class TestJeuDEssai(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = lancer(os.path.join(ESSAI, "matrice_bia_test.csv"), os.path.join(ESSAI, "cmdb_test.csv"))

    def controles(self, activite):
        return {e["controle"] for e in self.res["erreurs"] if e["activite"] == activite}

    def test_rto_superieur_au_dmia_detecte(self):
        self.assertIn("RTO < DMIA", self.controles("T02"))

    def test_rto_egal_au_dmia_detecte(self):
        self.assertIn("RTO < DMIA", self.controles("T03"))

    def test_dmia_au_dela_du_palier_detecte(self):
        self.assertIn("DMIA <= palier d'impact", self.controles("T04"))

    def test_ci_inconnu_detecte(self):
        self.assertIn("Référence CMDB", self.controles("T05"))

    def test_valeur_manquante_detectee(self):
        self.assertIn("Valeur manquante", self.controles("T06"))

    def test_activite_saine_sans_erreur(self):
        self.assertEqual(self.controles("T01"), set())

    def test_alerte_rto_technique_detectee(self):
        a = self.res["alertes"]
        self.assertEqual(len(a[(a["id_activite"] == "T07") & (a["nature"] == "RTO") & (a["ci"] == "APP-Y")]), 1)

    def test_alerte_rpo_technique_detectee(self):
        a = self.res["alertes"]
        self.assertEqual(len(a[(a["id_activite"] == "T08") & (a["nature"] == "RPO")]), 1)

    def test_exactement_cinq_incoherences(self):
        self.assertEqual(len(self.res["erreurs"]), 5)

    def test_code_retour_nonzero(self):
        sortie = tempfile.mkdtemp()
        code = b.main(["--matrice", os.path.join(ESSAI, "matrice_bia_test.csv"),
                       "--cmdb", os.path.join(ESSAI, "cmdb_test.csv"), "--out", sortie, "--sans-graphe"])
        self.assertEqual(code, 1)


class TestCycle(unittest.TestCase):
    def test_cycle_detecte(self):
        d = tempfile.mkdtemp()
        m = os.path.join(d, "m.csv"); c = os.path.join(d, "c.csv")
        pd.DataFrame([{"id": "X1", "service": "s", "activite": "a", "dmia_min": 60, "rto_min": 30, "rpo_min": 10,
                       "mbco": "-", "ci_supports": "C1", "mode_degrade": "oui", "imp_1h": 4, "imp_4h": 5,
                       "imp_24h": 5, "imp_72h": 5, "imp_1w": 5}]).to_csv(m, index=False)
        pd.DataFrame([{"id": "C1", "nom": "c1", "type": "Serveur", "rto_tech_min": 10, "rpo_tech_min": "", "depends_on": "C2"},
                      {"id": "C2", "nom": "c2", "type": "Serveur", "rto_tech_min": 10, "rpo_tech_min": "", "depends_on": "C1"}]
                     ).to_csv(c, index=False)
        res = lancer(m, c)
        self.assertIn("Cycle de dépendances", {e["controle"] for e in res["erreurs"]})


class TestPerformance(unittest.TestCase):
    def test_temps_d_execution_sans_graphe(self):
        t = time.perf_counter()
        lancer(os.path.join(DATA, "matrice_bia.csv"), os.path.join(DATA, "cmdb_ci.csv"))
        self.assertLess(time.perf_counter() - t, 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
