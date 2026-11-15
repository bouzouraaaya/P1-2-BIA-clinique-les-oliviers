#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bia_tool.py - Outil de calcul du BIA (projet P1.2, Clinique Les Oliviers, organisme fictif)

Ce que fait l'outil (ISO 22301 clauses 8.2.1 et 8.2.2) :
  1. lit la matrice BIA (CSV) et l'export de la CMDB (CSV) ;
  2. contrôle la cohérence des paramètres : RTO < DMIA, DMIA <= palier d'impact
     inacceptable, références CMDB valides, absence de cycle de dépendances ;
  3. signale les dépendances dont le RTO technique dépasse le RTO métier
     (et celles dont le RPO technique dépasse le RPO métier) ;
  4. calcule les priorités de reprise (rang et classe P1 à P4) ;
  5. génère le graphe des dépendances activité -> application -> infrastructure.

Principe directeur : le besoin du patient fixe le RTO métier, puis le SI doit s'y
conformer. L'outil ne modifie donc jamais le RTO métier : il signale les écarts.

Usage :
  python bia_tool.py --matrice data/matrice_bia.csv --cmdb data/cmdb_ci.csv --out resultats
Code de retour : 0 si aucune incohérence de paramètres, 1 sinon (les alertes de
dépendances sont des constats, pas des erreurs).
"""
import argparse
import os
import sys

import networkx as nx
import pandas as pd

# --- Paramètres de la méthode (voir hypothèses H01 et H13) --------------------
SEUIL_IMPACT = 4  # niveau d'impact jugé inacceptable (échelle de 1 à 5)
PALIERS = [("imp_1h", 1), ("imp_4h", 4), ("imp_24h", 24), ("imp_72h", 72), ("imp_1w", 168)]
COLONNES_MATRICE = ["id", "service", "activite", "dmia_min", "rto_min", "rpo_min", "mbco",
                    "ci_supports", "mode_degrade"] + [p for p, _ in PALIERS]
COLONNES_CMDB = ["id", "nom", "type", "rto_tech_min", "rpo_tech_min", "depends_on"]
TYPES_AVEC_DONNEES = {"Application", "Base de données"}  # concernés par le RPO
SEVERITE = {"non": "CRITIQUE", "partiel": "MAJEUR", "oui": "MODERE"}


def fmt_duree(minutes):
    """Affiche une durée en minutes sous une forme lisible."""
    m = pd.to_numeric(minutes, errors="coerce")
    if pd.isna(m):
        return "n/d"
    m = float(m)
    if m < 60:
        return f"{m:g} min"
    if m < 1440:
        return f"{m / 60:g} h"
    return f"{m / 1440:g} j"


def _liste(valeur):
    """Transforme 'A;B;C' en ['A', 'B', 'C'] (vide si NaN)."""
    if pd.isna(valeur) or str(valeur).strip() == "":
        return []
    return [v.strip() for v in str(valeur).split(";") if v.strip()]


# --- 1. Lecture et contrôle de structure --------------------------------------
def charger(chemin_matrice, chemin_cmdb):
    """Lit les deux CSV et vérifie la présence des colonnes obligatoires."""
    matrice = pd.read_csv(chemin_matrice)
    cmdb = pd.read_csv(chemin_cmdb)
    manquantes = [c for c in COLONNES_MATRICE if c not in matrice.columns]
    manquantes += [c for c in COLONNES_CMDB if c not in cmdb.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {manquantes}")
    return matrice, cmdb


# --- 2. Contrôles de cohérence des paramètres ---------------------------------
def controler_matrice(matrice):
    """Retourne la liste des incohérences de la matrice (liste de dictionnaires)."""
    erreurs = []
    for _, r in matrice.iterrows():
        a = r["id"]
        # valeurs manquantes ou non numériques
        for col in ["dmia_min", "rto_min", "rpo_min"]:
            if pd.isna(pd.to_numeric(r[col], errors="coerce")):
                erreurs.append({"activite": a, "controle": "Valeur manquante",
                                "detail": f"{col} absent ou non numérique"})
        if pd.isna(pd.to_numeric(r["dmia_min"], errors="coerce")) or \
           pd.isna(pd.to_numeric(r["rto_min"], errors="coerce")):
            continue
        dmia, rto = float(r["dmia_min"]), float(r["rto_min"])
        # règle 1 : RTO strictement inférieur au DMIA
        if not rto < dmia:
            erreurs.append({"activite": a, "controle": "RTO < DMIA",
                            "detail": f"RTO {fmt_duree(rto)} >= DMIA {fmt_duree(dmia)}"})
        # règle 2 : DMIA au plus égal au palier d'impact inacceptable
        palier = palier_impact(r)
        if palier is not None and dmia / 60 > palier:
            erreurs.append({"activite": a, "controle": "DMIA <= palier d'impact",
                            "detail": f"DMIA {fmt_duree(dmia)} dépasse le palier d'impact inacceptable ({palier} h)"})
        # règle 3 : mode dégradé valide
        if r["mode_degrade"] not in SEVERITE:
            erreurs.append({"activite": a, "controle": "Mode dégradé",
                            "detail": f"valeur '{r['mode_degrade']}' (attendu : oui, partiel, non)"})
    return erreurs


def palier_impact(ligne):
    """Premier intervalle (en heures) où l'impact atteint le seuil, ou None."""
    for colonne, heures in PALIERS:
        if float(ligne[colonne]) >= SEUIL_IMPACT:
            return heures
    return None


# --- 3. Graphe des dépendances ------------------------------------------------
def construire_graphe(matrice, cmdb):
    """Construit le graphe orienté activité -> CI -> CI. Retourne (graphe, erreurs)."""
    erreurs, g = [], nx.DiGraph()
    ci_ids = set(cmdb["id"])
    for _, c in cmdb.iterrows():
        g.add_node(c["id"], kind="ci", type=c["type"], nom=c["nom"])
    for _, r in matrice.iterrows():
        g.add_node(r["id"], kind="activite", type="Activité", nom=r["activite"], service=r["service"])
        for ci in _liste(r["ci_supports"]):
            if ci not in ci_ids:
                erreurs.append({"activite": r["id"], "controle": "Référence CMDB",
                                "detail": f"CI inconnu '{ci}' dans ci_supports"})
            else:
                g.add_edge(r["id"], ci)
    for _, c in cmdb.iterrows():
        for dep in _liste(c["depends_on"]):
            if dep not in ci_ids:
                erreurs.append({"activite": c["id"], "controle": "Référence CMDB",
                                "detail": f"dépendance inconnue '{dep}' pour le CI {c['id']}"})
            else:
                g.add_edge(c["id"], dep)
    if not nx.is_directed_acyclic_graph(g):
        cycle = nx.find_cycle(g)
        erreurs.append({"activite": "-", "controle": "Cycle de dépendances",
                        "detail": " -> ".join(a for a, _ in cycle)})
    return g, erreurs


# --- 4. Alertes RTO / RPO techniques ------------------------------------------
def calculer_alertes(matrice, cmdb, g):
    """Liste les dépendances dont le RTO (ou RPO) technique dépasse le besoin métier."""
    ci = cmdb.set_index("id")
    lignes = []
    for _, r in matrice.iterrows():
        if r["id"] not in g:
            continue
        distances = nx.single_source_shortest_path_length(g, r["id"])
        for dep, niveau in sorted(distances.items(), key=lambda x: (x[1], x[0])):
            if dep == r["id"]:
                continue
            c = ci.loc[dep]
            rto_t = pd.to_numeric(c["rto_tech_min"], errors="coerce")
            rpo_t = pd.to_numeric(c["rpo_tech_min"], errors="coerce")
            base = {"id_activite": r["id"], "activite": r["activite"], "ci": dep, "nom_ci": c["nom"],
                    "type_ci": c["type"], "niveau_dependance": niveau,
                    "mode_degrade": r["mode_degrade"], "severite": SEVERITE.get(r["mode_degrade"], "A PRECISER")}
            if pd.notna(rto_t) and rto_t > float(r["rto_min"]):
                lignes.append({**base, "nature": "RTO", "valeur_metier_min": float(r["rto_min"]),
                               "valeur_technique_min": float(rto_t),
                               "ecart_min": float(rto_t) - float(r["rto_min"])})
            if c["type"] in TYPES_AVEC_DONNEES and pd.notna(rpo_t) and rpo_t > float(r["rpo_min"]):
                lignes.append({**base, "nature": "RPO", "valeur_metier_min": float(r["rpo_min"]),
                               "valeur_technique_min": float(rpo_t),
                               "ecart_min": float(rpo_t) - float(r["rpo_min"])})
    colonnes = ["id_activite", "activite", "nature", "ci", "nom_ci", "type_ci", "niveau_dependance",
                "valeur_metier_min", "valeur_technique_min", "ecart_min", "mode_degrade", "severite"]
    return pd.DataFrame(lignes, columns=colonnes)


# --- 5. Priorités de reprise --------------------------------------------------
def classe_priorite(dmia_min):
    """P1 : DMIA <= 1 h ; P2 : <= 4 h ; P3 : <= 72 h ; P4 : au-delà."""
    if dmia_min <= 60:
        return "P1"
    if dmia_min <= 240:
        return "P2"
    if dmia_min <= 4320:
        return "P3"
    return "P4"


def calculer_priorites(matrice, alertes):
    """Tri par DMIA, puis RTO, puis impact à 1 h décroissant, puis identifiant."""
    df = matrice.copy()
    df["dmia_min"] = pd.to_numeric(df["dmia_min"], errors="coerce")
    df["rto_min"] = pd.to_numeric(df["rto_min"], errors="coerce")
    df = df.dropna(subset=["dmia_min", "rto_min"])
    df = df.sort_values(["dmia_min", "rto_min", "imp_1h", "id"], ascending=[True, True, False, True])
    df = df.reset_index(drop=True)
    df["rang"] = df.index + 1
    df["classe"] = df["dmia_min"].apply(classe_priorite)
    nb = alertes.groupby("id_activite").size() if len(alertes) else pd.Series(dtype=int)
    df["nb_alertes"] = df["id"].map(nb).fillna(0).astype(int)
    return df[["rang", "id", "service", "activite", "classe", "dmia_min", "rto_min", "rpo_min",
               "mbco", "mode_degrade", "nb_alertes"]]


# --- 6. Graphe (image) --------------------------------------------------------
COULEURS = {"Activité": "#1f4e79", "Application": "#2e86c1", "Serveur": "#5dade2",
            "Base de données": "#48c9b0", "Infrastructure": "#f5b041", "Réseau": "#af7ac5",
            "Alimentation": "#ec7063", "Fournisseur": "#a6acaf"}


def dessiner_graphe(g, matrice, cmdb, chemin_png):
    """Dessine le graphe en couches ; contour rouge = RTO technique > besoin métier le plus strict."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ci = cmdb.set_index("id")
    rto_metier = matrice.set_index("id")["rto_min"].astype(float).to_dict()
    for i, generation in enumerate(nx.topological_generations(g)):
        for n in generation:
            g.nodes[n]["layer"] = i
    # contour rouge : CI en écart avec la plus stricte des activités qui en dépendent
    ecart = set()
    for n in g.nodes:
        if g.nodes[n]["kind"] != "ci":
            continue
        rto_t = pd.to_numeric(ci.loc[n, "rto_tech_min"], errors="coerce")
        acts = [a for a in nx.ancestors(g, n) if g.nodes[a]["kind"] == "activite"]
        if pd.notna(rto_t) and acts and rto_t > min(rto_metier[a] for a in acts):
            ecart.add(n)
    ordre = sorted(g.nodes, key=lambda n: (g.nodes[n]["layer"], g.nodes[n]["type"], n))
    h = nx.DiGraph()
    h.add_nodes_from((n, g.nodes[n]) for n in ordre)
    h.add_edges_from(g.edges)
    # positions : une colonne par couche, noeuds espacés régulièrement dans l'ordre trié
    couches = {}
    for n in ordre:
        couches.setdefault(h.nodes[n]["layer"], []).append(n)
    pos = {}
    for x, noeuds in couches.items():
        for k, n in enumerate(noeuds):
            pos[n] = (x, -(k - (len(noeuds) - 1) / 2))
    fig, ax = plt.subplots(figsize=(26, 13))
    nx.draw_networkx_edges(h, pos, ax=ax, edge_color="#7f8c8d", alpha=0.35, arrows=True,
                           arrowsize=9, node_size=1900, connectionstyle="arc3,rad=0.04")
    couleurs = [COULEURS.get(h.nodes[n]["type"], "#cccccc") for n in h.nodes]
    contours = ["#c0392b" if n in ecart else "#2c3e50" for n in h.nodes]
    largeurs = [3.5 if n in ecart else 0.8 for n in h.nodes]
    nx.draw_networkx_nodes(h, pos, ax=ax, node_color=couleurs, edgecolors=contours,
                           linewidths=largeurs, node_size=1900)
    etiquettes = {n: (f"{n}\n{h.nodes[n]['service']}" if h.nodes[n]["kind"] == "activite" else n) for n in h.nodes}
    nx.draw_networkx_labels(h, pos, labels=etiquettes, font_size=7, ax=ax)
    legende = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=12, label=t)
               for t, c in COULEURS.items()]
    legende.append(plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="white",
                              markeredgecolor="#c0392b", markeredgewidth=3, markersize=12,
                              label="RTO technique > RTO métier le plus strict"))
    ax.legend(handles=legende, loc="lower center", ncol=5, fontsize=10, frameon=False)
    ax.set_title("Graphe des dépendances : activité → application → serveur / base → infrastructure "
                 "(Clinique Les Oliviers, données fictives)", fontsize=14)
    ax.axis("off")
    fig.savefig(chemin_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return sorted(ecart)


# --- 7. Programme principal ---------------------------------------------------
def executer(chemin_matrice, chemin_cmdb, dossier_sortie, avec_graphe=True):
    """Enchaîne tous les traitements et retourne un dictionnaire de résultats."""
    os.makedirs(dossier_sortie, exist_ok=True)
    matrice, cmdb = charger(chemin_matrice, chemin_cmdb)
    erreurs = controler_matrice(matrice)
    g, err_graphe = construire_graphe(matrice, cmdb)
    erreurs += err_graphe
    alertes = calculer_alertes(matrice, cmdb, g)
    priorites = calculer_priorites(matrice, alertes)
    priorites.to_csv(os.path.join(dossier_sortie, "priorites_reprise.csv"), index=False, encoding="utf-8")
    alertes.to_csv(os.path.join(dossier_sortie, "alertes_dependances.csv"), index=False, encoding="utf-8")
    pd.DataFrame(erreurs, columns=["activite", "controle", "detail"]).to_csv(
        os.path.join(dossier_sortie, "incoherences.csv"), index=False, encoding="utf-8")
    rouges = []
    if avec_graphe and not err_graphe:
        rouges = dessiner_graphe(g, matrice, cmdb, os.path.join(dossier_sortie, "graphe_dependances.png"))
    nx.write_gexf(g, os.path.join(dossier_sortie, "graphe_dependances.gexf")) if not err_graphe else None
    return {"matrice": matrice, "cmdb": cmdb, "erreurs": erreurs, "alertes": alertes,
            "priorites": priorites, "graphe": g, "ci_en_ecart": rouges}


def rapport_texte(res):
    """Construit le rapport de contrôle affiché et enregistré."""
    L = ["=" * 78, "RAPPORT DE CONTRÔLE DU BIA", "=" * 78]
    L.append(f"Activités : {len(res['matrice'])} | Éléments de configuration : {len(res['cmdb'])}")
    L.append("\n1) COHÉRENCE DES PARAMÈTRES")
    if res["erreurs"]:
        for e in res["erreurs"]:
            L.append(f"  [INCOHÉRENT] {e['activite']:<10} {e['controle']:<26} {e['detail']}")
    else:
        L.append("  Aucune incohérence : RTO < DMIA, DMIA <= palier d'impact, références CMDB valides.")
    L.append("\n2) ÉCARTS ENTRE BESOIN MÉTIER ET CAPACITÉ TECHNIQUE (par activité)")
    al = res["alertes"]
    for _, r in res["priorites"].iterrows():
        sous = al[al["id_activite"] == r["id"]]
        rto = sous[sous["nature"] == "RTO"]
        rpo = sous[sous["nature"] == "RPO"]
        if sous.empty:
            L.append(f"  {r['id']} {r['activite'][:44]:<44} RTO métier {fmt_duree(r['rto_min']):>7} : aucun écart")
            continue
        rto_si = rto[rto["type_ci"] != "Fournisseur"]
        nb_four = int((rto["type_ci"] == "Fournisseur").sum())
        pire = rto_si.sort_values("valeur_technique_min", ascending=False).head(1)
        txt = (f"RTO métier {fmt_duree(r['rto_min']):>7} : {len(rto_si)} écart(s) RTO SI, "
               f"{nb_four} fournisseur(s), {len(rpo)} écart(s) RPO")
        if len(pire):
            p = pire.iloc[0]
            txt += f" ; pire SI : {p['ci']} ({fmt_duree(p['valeur_technique_min'])})"
        L.append(f"  {r['id']} {r['activite'][:44]:<44} {txt} [{sous['severite'].iloc[0]}]")
    L.append("\n3) PRIORITÉS DE REPRISE")
    for _, r in res["priorites"].iterrows():
        L.append(f"  {int(r['rang']):>2}. {r['id']} {r['classe']}  DMIA {fmt_duree(r['dmia_min']):>7}  "
                 f"RTO {fmt_duree(r['rto_min']):>7}  RPO {fmt_duree(r['rpo_min']):>7}  {r['activite']}")
    if res["ci_en_ecart"]:
        L.append(f"\n4) CI AU CONTOUR ROUGE DU GRAPHE ({len(res['ci_en_ecart'])}) : " + ", ".join(res["ci_en_ecart"]))
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description="Outil de calcul du BIA (projet P1.2)")
    p.add_argument("--matrice", default="data/matrice_bia.csv")
    p.add_argument("--cmdb", default="data/cmdb_ci.csv")
    p.add_argument("--out", default="resultats")
    p.add_argument("--sans-graphe", action="store_true")
    a = p.parse_args(argv)
    res = executer(a.matrice, a.cmdb, a.out, avec_graphe=not a.sans_graphe)
    texte = rapport_texte(res)
    print(texte)
    with open(os.path.join(a.out, "rapport_controle.txt"), "w", encoding="utf-8") as f:
        f.write(texte + "\n")
    return 1 if res["erreurs"] else 0


if __name__ == "__main__":
    sys.exit(main())
