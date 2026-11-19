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

## B. Entrées réalisées sur la machine virtuelle (GLPI)
| N° | Date | Action | Commande / menu | Résultat / mesure |
|---|---|---|---|---|
| 6 | 16/11/2026 | Machine virtuelle Ubuntu (VMware, 2 Go de mémoire) : mises à jour automatiques bloquées par un verrou apt | `ps`, `kill`, `systemctl disable --now apt-daily.timer apt-daily-upgrade.timer` | Verrou libéré, minuteurs désactivés |
| 7 | 16/11/2026 | Installation de Docker | `sudo apt install -y docker.io docker-compose` | Docker 18.09.7 et docker-compose 1.8.0 (le paquet docker-compose-v2 n'existe pas sur cette version) |
| 8 | 16/11/2026 | Fichier compose adapté et lancement | `docker-compose up -d` (version "2", MariaDB 10.5) | Deux conteneurs Up |
| 9 | 16/11/2026 | Échec du téléchargement automatique de GLPI | `docker-compose logs` : `wget: missing URL` | GLPI 10.0.16 téléchargé avec `wget` (58 Mo), extrait dans `data/glpi` |
| 10 | 17/11/2026 | Installation web de GLPI, suppression de `install.php`, changement des mots de passe par défaut | Assistant d'installation | Version confirmée : GLPI 10.0.16 |
| 11 | 18/11/2026 | API REST activée, client « full access from localhost » élargi (0.0.0.0 à 255.255.255.255, test uniquement), jeton généré | Configuration > Générale > API | API accessible |
| 12 | 18/11/2026 | Import des CI par script | `python3 glpi_import.py` (essai à blanc, 3 éléments, puis complet) | 49 éléments créés, 0 échec |
| 13 | 18/11/2026 | Vérification des listes et captures d'écran | Parc et Gestion | 12 ordinateurs, 4 matériels réseau, 3 passifs, 22 applicatifs, 4 instances, 4 fournisseurs |
| 14 | 19/11/2026 | Export de la CMDB | `python3 glpi_export.py` | 49 éléments exportés, 6 CSV dans `preuves/export_cmdb/` |
