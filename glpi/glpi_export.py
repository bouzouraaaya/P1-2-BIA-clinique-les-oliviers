#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exporte en CSV les elements GLPI du projet P1.2 (API REST). Python 3.5+, sans bibliotheque externe."""
import argparse, csv, json, os, sys, urllib.request, urllib.error

LISTES = [("ordinateurs", "Computer"), ("materiels_reseau", "NetworkEquipment"),
          ("equipements_passifs", "PassiveDCEquipment"), ("applicatifs", "Appliance"),
          ("instances_bases", "DatabaseInstance"), ("fournisseurs", "Supplier")]


def appel(base, chemin, token, session=None, app=None):
    h = {"Content-Type": "application/json"}
    if app:
        h["App-Token"] = app
    if session:
        h["Session-Token"] = session
    else:
        h["Authorization"] = "user_token " + token
    try:
        with urllib.request.urlopen(urllib.request.Request(base + chemin, headers=h), timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP %d : %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))


def main():
    p = argparse.ArgumentParser(description="Export CSV des listes GLPI")
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--user-token", required=True)
    p.add_argument("--app-token", default=None)
    p.add_argument("--out", default="preuves/export_cmdb")
    a = p.parse_args()
    base = a.url.rstrip("/") + "/apirest.php"
    try:
        sess = appel(base, "/initSession", a.user_token, None, a.app_token)["session_token"]
    except Exception as e:
        sys.exit("Connexion refusée : %s" % e)
    os.makedirs(a.out, exist_ok=True)
    total = 0
    for nom, typ in LISTES:
        lignes = appel(base, "/%s?range=0-199&expand_dropdowns=true" % typ, a.user_token, sess, a.app_token)
        champs = []
        for l in lignes:
            for k in l:
                if k not in champs:
                    champs.append(k)
        chemin = os.path.join(a.out, nom + ".csv")
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(champs)
            for l in lignes:
                w.writerow([str(l.get(c, "")) for c in champs])
        total += len(lignes)
        print("%-22s %3d lignes -> %s" % (typ, len(lignes), chemin))
    try:
        appel(base, "/killSession", a.user_token, sess, a.app_token)
    except Exception:
        pass
    print("Total : %d éléments exportés" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
