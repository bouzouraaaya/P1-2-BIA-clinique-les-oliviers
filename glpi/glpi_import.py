#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cree dans GLPI (API REST) les 35 CI et les 14 activites du projet P1.2 (donnees fictives).
Compatible Python 3.5+, sans bibliotheque externe. Voir le guide pour activer l'API de GLPI."""
import argparse, json, os, sys, urllib.request, urllib.error

CIS = """APP-DPI|Application|Dossier Patient Informatisé|30|15|SRV-DPI;DB-DPI;APP-AD;FOU-SIH|H08
APP-PACS|Application|PACS (imagerie)|120|120|SRV-PACS;FOU-SIH|H11
APP-SIL|Application|SIL (laboratoire)|120|60|SRV-SIL;DB-SIL|H09
APP-PHA|Application|Logiciel pharmacie|120|60|SRV-PHA;DB-PHA|H09
APP-ERP|Application|ERP de gestion|1440|1440|SRV-ERP;DB-ERP|H10
APP-TEL|Application|Téléphonie IP (IPPBX)|30||SRV-IPBX|H06
APP-AD|Application|Annuaire et authentification|30||SRV-AD|H07
APP-BLOC|Application|Planification du bloc opératoire|120|60|SRV-BLOC;APP-DPI|H11
SRV-DPI|Serveur|Serveur applicatif DPI|30||HYP-01;NET-CORE|H07
SRV-PACS|Serveur|Serveur PACS|60||HYP-01;SAN-01;NET-CORE|H07
SRV-SIL|Serveur|Serveur SIL|60||HYP-02;NET-CORE|H07
SRV-PHA|Serveur|Serveur pharmacie|60||HYP-02;NET-CORE|H07
SRV-ERP|Serveur|Serveur ERP|240||HYP-02;NET-CORE|H07
SRV-IPBX|Serveur|Serveur IPBX|30||NET-CORE;NET-WAN|H06
SRV-AD|Serveur|Contrôleur de domaine|30||HYP-01|H07
SRV-BLOC|Serveur|Serveur planification bloc|60||HYP-02;NET-CORE|H07
SRV-DB01|Serveur|Serveur de bases de données|30||HYP-02;SAN-01|H07
DB-DPI|Base de données|Base de données DPI|30|15|SRV-DB01|H08
DB-SIL|Base de données|Base de données SIL|60|60|SRV-DB01|H09
DB-PHA|Base de données|Base de données pharmacie|60|60|SRV-DB01|H09
DB-ERP|Base de données|Base de données ERP|240|1440|SRV-DB01|H10
HYP-01|Infrastructure|Hôte de virtualisation 1|30||SAL-DC;SAN-01;NET-CORE|H07
HYP-02|Infrastructure|Hôte de virtualisation 2|30||SAL-DC;SAN-01;NET-CORE|H07
SAN-01|Infrastructure|Baie de stockage SAN|60||SAL-DC|H07
BKP-01|Infrastructure|Serveur de sauvegarde|120||SAN-01;SAL-DC|H09
NET-CORE|Réseau|Cœur de réseau|15||SAL-DC|H07
NET-FW|Réseau|Pare-feu|30||NET-CORE|H07
NET-WAN|Réseau|Liaison opérateur télécom|240||NET-FW;FOU-TEL|H12
SAL-DC|Infrastructure|Salle serveurs|15||UPS-01;GE-01|H06
UPS-01|Alimentation|Onduleur|0|||H06
GE-01|Alimentation|Groupe électrogène|30|||H06
FOU-SIH|Fournisseur|Éditeur du SIH|240|||H12
FOU-O2|Fournisseur|Fournisseur d'oxygène médical|120|||H12
FOU-TEL|Fournisseur|Opérateur télécom|240|||H12
FOU-BIO|Fournisseur|Société de maintenance biomédicale|240|||H12"""
ACTS = """A01|Urgences|Accueil et prise en charge des urgences vitales|APP-DPI;APP-TEL;APP-PACS;APP-SIL;FOU-O2;FOU-BIO
A02|Réanimation|Réanimation et soins continus|APP-DPI;APP-TEL;FOU-O2;FOU-BIO
A03|Bloc opératoire|Interventions chirurgicales (6 salles)|APP-BLOC;APP-DPI;APP-PACS;FOU-O2;FOU-BIO
A04|Imagerie|Imagerie médicale (radiologie, scanner, IRM)|APP-PACS;FOU-SIH;FOU-BIO
A05|Laboratoire|Analyses biologiques|APP-SIL;FOU-BIO
A06|Pharmacie|Dispensation des médicaments et dispositifs médicaux|APP-PHA;APP-DPI;FOU-O2
A07|Hospitalisation|Soins en unités d'hospitalisation|APP-DPI;APP-TEL
A08|Administration|Admission et gestion administrative des patients|APP-DPI;APP-AD
A09|Facturation|Facturation et recouvrement|APP-ERP
A10|Administration|Gestion des ressources humaines et de la paie|APP-ERP
A11|Logistique|Approvisionnement, achats et gestion des stocks|APP-ERP;FOU-O2
A12|Technique|Maintenance biomédicale et technique|APP-ERP;FOU-BIO
A13|Support|Téléphonie et communication d'urgence interne|APP-TEL;FOU-TEL
A14|DSI|Exploitation et support du système d'information|APP-AD;BKP-01"""

TYPE_MAP = {"Application": "Appliance", "Serveur": "Computer", "Base de données": "DatabaseInstance",
            "Réseau": "NetworkEquipment", "Alimentation": "PassiveDCEquipment",
            "Infrastructure": "Computer", "Fournisseur": "Supplier"}
OVERRIDE = {"SAN-01": "NetworkEquipment", "SAL-DC": "PassiveDCEquipment"}


class Glpi(object):
    def __init__(self, url, user_token, app_token=None):
        self.base = url.rstrip("/") + "/apirest.php"
        self.user_token, self.app_token, self.session = user_token, app_token, None

    def call(self, method, path, body=None, auth=False):
        headers = {"Content-Type": "application/json"}
        if self.app_token:
            headers["App-Token"] = self.app_token
        if auth:
            headers["Authorization"] = "user_token " + self.user_token
        elif self.session:
            headers["Session-Token"] = self.session
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError("HTTP %d : %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))

    def open(self):
        self.session = self.call("GET", "/initSession", auth=True)["session_token"]

    def close(self):
        try:
            self.call("GET", "/killSession")
        except Exception:
            pass


def elements():
    for ligne in CIS.strip().splitlines():
        i, typ, nom, rto, rpo, dep, hyp = ligne.split("|")
        itemtype = OVERRIDE.get(i, TYPE_MAP.get(typ, "Computer"))
        com = "Type : %s. RTO technique : %s min." % (typ, rto)
        if rpo not in ("", "None"):
            com += " RPO technique : %s min." % rpo
        com += " Dépend de : %s. Hypothèse : %s. (Données fictives, projet P1.2)" % (dep.replace(";", ", ") or "aucun", hyp)
        yield i, itemtype, i + " - " + nom, com
    for ligne in ACTS.strip().splitlines():
        i, svc, nom, cis = ligne.split("|")
        yield "ACT-" + i, "Appliance", "ACT-" + i + " - " + nom, \
            "Activité métier du BIA (service : %s). S'appuie sur : %s. (Données fictives, projet P1.2)" % (svc, cis.replace(";", ", "))


def main():
    p = argparse.ArgumentParser(description="Import des CI et activites dans GLPI")
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--user-token", help="cle d'acces distant (API) du profil GLPI")
    p.add_argument("--app-token", default=None)
    p.add_argument("--state", default="glpi_state.json", help="fichier qui memorise les elements deja crees")
    p.add_argument("--limit", type=int, default=0, help="ne traiter que les N premiers elements (essai)")
    p.add_argument("--dry-run", action="store_true", help="afficher sans rien envoyer")
    a = p.parse_args()
    liste = list(elements())
    if a.limit:
        liste = liste[:a.limit]
    etat = json.load(open(a.state)) if os.path.exists(a.state) else {}
    if a.dry_run:
        for i, t, n, c in liste:
            print("[essai] %-18s %-9s %s" % (t, i, c[:60]))
        print("%d elements (aucun envoi)" % len(liste))
        return 0
    if not a.user_token:
        sys.exit("Indiquez --user-token (voir le guide)")
    g = Glpi(a.url, a.user_token, a.app_token)
    try:
        g.open()
    except Exception as e:
        sys.exit("Connexion refusée : %s\nVérifiez l'API, le jeton et les clients autorisés (guide)." % e)
    crees = ignores = 0
    echecs = []
    for i, t, n, c in liste:
        if i in etat:
            ignores += 1
            continue
        try:
            rep = g.call("POST", "/" + t, {"input": {"name": n, "comment": c}})
            etat[i] = {"itemtype": t, "id": rep["id"]}
            json.dump(etat, open(a.state, "w"), indent=1)
            crees += 1
            print("cree    %-18s %-9s id=%s" % (t, i, rep["id"]))
        except Exception as e:
            echecs.append(i)
            print("ECHEC   %-18s %-9s %s" % (t, i, e))
    g.close()
    print("Résumé : %d créés, %d déjà présents, %d échecs %s" % (crees, ignores, len(echecs), echecs or ""))
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
