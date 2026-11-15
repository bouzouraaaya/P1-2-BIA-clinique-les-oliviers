# Journal de laboratoire – P1.2 BIA (données fictives, machines virtuelles uniquement)

Règle du sujet : toute configuration, commande et mesure est consignée. Aucune manipulation sur un système de production ou un réseau tiers.

## A. Entrées réalisées lors de la préparation de l'outil Python (à refaire et confirmer sur votre poste)
| N° | Action | Commande | Résultat observé |
|---|---|---|---|
| 1 | Exécution sur les données principales | `python bia_tool.py --out resultats` | 0 incohérence ; 14 activités ; 35 CI ; 65 alertes RTO et 12 alertes RPO ; code retour 0 |
| 2 | Exécution sur le jeu d'essai | `python bia_tool.py --matrice jeu_essai/matrice_bia_test.csv --cmdb jeu_essai/cmdb_test.csv --out jeu_essai/resultats_attendus` | 5 incohérences détectées (T02 à T06) ; alertes RTO (T07) et RPO (T08) ; code retour 1 |
| 3 | Tests automatiques | `python -m unittest discover -s tests -v` | 20 tests réussis (journal : `resultats/journal_tests.txt`) |
| 4 | Mesure du temps | 3 exécutions de chaque mode | Avec graphe : 1,28 s en moyenne ; sans graphe : 0,45 s (`resultats/mesure_temps.txt`) |
| 5 | Cohérence Excel / Python | Comparaison des rangs et classes | Identiques pour les 14 activités |

## B. Entrées à compléter par vous (GLPI)
| N° | Date | Action | Commande / menu | Résultat / mesure | Capture |
|---|---|---|---|---|---|
| 6 | | Création de la VM Linux (distribution, RAM, disque) | | | |
| 7 | | Installation de Docker | | | |
| 8 | | `docker compose up -d` | | Version de GLPI : | |
| 9 | | Installation web, changement des mots de passe | | | |
| 10 | | Création des CI (nombre) | | | |
| 11 | | Création des liens de dépendance (nombre) | | | |
| 12 | | Export de la CMDB | | | |
| 13 | | Exécution de l'outil sur l'export CMDB | | | |
