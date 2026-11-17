# Guide GLPI : modéliser la CMDB du SIH (au moins 25 éléments de configuration)

Les 35 éléments de configuration (CI) sont décrits dans `../data/cmdb_ci.csv` (colonne `classe_glpi`).

## Étapes
1. Lancer `docker compose up -d` dans ce dossier, puis terminer l'installation web (voir commentaire du compose).
2. Créer l'entité « Clinique Les Oliviers » et les lieux : Salle serveurs, Bâtiment A, Externe.
3. Créer les CI selon leur classe :
   - Serveurs, hôtes, serveur de sauvegarde : *Parc > Ordinateurs* (type « Serveur »).
   - Baie SAN, cœur de réseau, pare-feu, lien opérateur : *Parc > Matériels réseau* ou *Baies*.
   - Applications (DPI, PACS, SIL, pharmacie, ERP, téléphonie, AD, bloc) : *Parc > Appliances* (ou Logiciels).
   - Bases de données : *Parc > Bases de données* (instances).
   - Onduleur, groupe électrogène, salle serveurs : *Parc > Matériels passifs* ou *Baies*.
   - Fournisseurs : *Gestion > Fournisseurs*.
4. Renseigner dans chaque fiche : nom, lieu, commentaire (RTO / RPO techniques) et fournisseur.
5. Créer les liens de dépendance : *Analyse d'impact* (onglet « Analyse d'impact » de chaque CI),
   en reprenant la colonne `depends_on` du CSV, puis relier chaque activité du BIA aux CI listés dans `ci_supports`
   (les activités peuvent être créées comme *Appliances* de type « Activité métier » ou *Services*).
6. Exporter : *liste des CI > Exporter* (CSV) pour chaque classe ; regrouper les exports dans `../preuves/export_cmdb/`.
7. Faire des captures d'écran : tableau de bord, liste des CI (au moins 25), une analyse d'impact (ex. A02 Réanimation).

## Preuves à fournir (sujet, 2.2.4)
- Export de la CMDB (étape 6) ; script commenté et jeu d'essai (ce dossier) ; graphe généré (`resultats/graphe_dependances.png`).
- Les menus exacts peuvent varier selon la version de GLPI : noter la version utilisée dans le journal.

## Import automatique des CI par l'API (alternative à la saisie manuelle)
Script : `glpi_import.py` (Python 3.5+, sans bibliothèque externe). Il crée 35 CI et 14 activités dans GLPI avec RTO/RPO et dépendances dans le champ Commentaires.
1. GLPI : Configuration > Générale > onglet API : activer l'API REST et la connexion par jeton externe. Dans « Clients de l'API », ouvrir le client « full access from localhost » et élargir la plage IPv4 (0.0.0.0 à 255.255.255.255) car Docker masque l'adresse locale (environnement de test uniquement).
2. Mes paramètres : copier la « Clé d'accès distant (API) » (jeton utilisateur).
3. Essai : `python3 glpi_import.py --user-token JETON --limit 3`, puis complet : `python3 glpi_import.py --user-token JETON`.
4. Le script mémorise les éléments créés (`glpi_state.json`) : on peut le relancer sans créer de doublons.
Limite : les relations de l'Analyse d'impact ne sont pas créables par l'API ; elles se saisissent dans l'interface (au moins pour l'activité A02).
Test : `glpi/test_mock/run_test.py` vérifie le script contre un faux serveur GLPI (49 éléments créés, reprise sans doublon, échec isolé). Le script n'a pas été testé contre un vrai GLPI.
