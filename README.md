# LT – Livrable technique (P1.2 BIA, Clinique Les Oliviers – organisme fictif)

## Contenu
- `bia_tool.py` : outil de calcul (contrôles, priorités, alertes, graphe)
- `data/matrice_bia.csv` et `data/cmdb_ci.csv` : données (14 activités, 35 CI)
- `jeu_essai/` : jeu d'essai avec 5 incohérences et 2 alertes volontaires, et résultats attendus
- `tests/test_bia_tool.py` : 20 tests automatiques
- `resultats/` : priorités, alertes, incohérences, rapport, graphe PNG et GEXF, journal de tests, mesures de temps
- `glpi/` : docker-compose (non testé) et guide de modélisation de la CMDB
- `JOURNAL_LABORATOIRE.md`, `preuves/` : journal et dossiers de preuves à compléter

## Utilisation
    pip install -r requirements.txt
    python bia_tool.py --matrice data/matrice_bia.csv --cmdb data/cmdb_ci.csv --out resultats
    python -m unittest discover -s tests -v

Code de retour : 0 sans incohérence, 1 sinon.

## Règles de calcul
- Contrôle RTO < DMIA (strict) ; DMIA ≤ palier d'impact inacceptable (niveau 4) ; références CMDB valides ; pas de cycle.
- Alerte si le RTO technique d'un CI dont dépend une activité dépasse le RTO métier (RPO idem pour applications et bases).
- RTO d'une chaîne approché par le maximum de ses composants (hypothèse H13).
- Priorité : tri par DMIA, RTO, impact à 1 h décroissant ; classes P1 (≤ 1 h), P2 (≤ 4 h), P3 (≤ 72 h), P4.
