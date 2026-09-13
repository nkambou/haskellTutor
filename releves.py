"""Des journaux de cohorte a la rubrique « ce que le tuteur observe ».

Ce module ne fabrique aucune donnee. Il lit un journal de soumissions reelles
produit par HaskellTutor, compte les erreurs par chapitre, les classe, et engendre
le squelette de la rubrique avec les frequences observees et l'emplacement du
message GHC a coller.

Format du journal : un objet JSON par ligne (JSONL).

  {"horodatage": "2026-02-11T10:22:31",
   "cohorte": "INF3105-A26-G20",
   "apprenant": "a41c",            identifiant pseudonymise
   "chapitre": 4,
   "concept": "pli-droit",
   "exercice": "4.3",
   "verdict": "erreur",            reussite | erreur | correct_non_aligne
   "categorie": "missing-base-case",
   "message_ghc": "...",           texte brut, vide si le code compile
   "silencieuse": false}           vrai si le code compile et calcule faux

La categorie est choisie dans le catalogue ci-dessous. Une soumission dont la
categorie est absente du catalogue est comptee sous « non classee » : c'est le
signal qu'une erreur nouvelle est apparue et que le catalogue doit s'etendre.
"""

import json, sys, collections

# --------------------------------------------------------------- catalogue

CATALOGUE = {
    1: [("parentheses-appel",        "Les parenthèses d'appel"),
        ("priorite-application",     "La priorité de l'application"),
        ("int-double-mix",       "Le mélange Int et Double"),
        ("majuscule-initiale",       "Le nom qui commence par une majuscule")],
    2: [("motif-oublie",             "Le motif oublié"),
        ("ordre-des-cas",            "L'ordre des cas"),
        ("confusion-cons-append",    "La confusion entre : et ++"),
        ("head-tail-reflexe",        "head et tail employés par réflexe")],
    3: [("missing-base-case",       "L'oubli du cas de base"),
        ("wrong-recursive-call",    "L'appel récursif sur la mauvaise valeur"),
        ("base-produit-zero",        "Le cas de base de produit"),
        ("accumulateur-importe",     "L'accumulateur importé d'un autre langage")],
    4: [("missing-base-case",       "L'oubli du cas de base"),
        ("ordre-arguments-pli",      "L'inversion des arguments de la fonction repliée"),
        ("neutre-vs-liste-vide",     "La confusion entre l'élément neutre et la liste vide"),
        ("operation-un-argument",    "L'oubli du deuxième argument de l'opération"),
        ("map-au-lieu-de-filter",    "L'emploi de map là où filter est requis")],
    5: [("eta-mauvais-argument",     "La suppression d'un argument qui n'est pas en dernière position"),
        ("fausse-section-moins",     "La fausse section (- 1)"),
        ("priorite-composition",     "La priorité de la composition"),
        ("composer-arguments-manquants", "Composer avec une fonction à qui il manque un argument")],
    6: [("champs-motif",             "Le mauvais nombre de champs dans un motif"),
        ("deriving-show-oublie",     "Le deriving Show oublié"),
        ("parametre-type-oublie",    "Le paramètre de type oublié"),
        ("constructeur-comme-type",  "Le constructeur employé comme type"),
        ("cas-oublie",               "Le cas oublié")],
    7: [("contrainte-oubliee",       "La contrainte oubliée dans la signature"),
        ("instance-manquante",       "L'instance manquante sur un type à soi"),
        ("mauvaise-sorte",           "L'instance déclarée sur un type de mauvaise sorte"),
        ("type-ambigu",              "Le type ambigu"),
        ("instance-fautive",         "L'instance qui compile et ment")],
    8: [("calcul-sans-ouvrir",       "Calculer avec un Maybe sans l'ouvrir"),
        ("contenu-vs-enveloppe",     "Employer le contenu à la place de l'enveloppe"),
        ("length-sur-maybe",         "length sur un Maybe"),
        ("action-vs-valeur",         "Mélanger une action et une valeur"),
        ("do-finit-liaison",         "Le bloc do qui finit par une liaison")],
    9: [("foldl-sans-apostrophe",    "foldl sans apostrophe sur une longue liste"),
        ("pli-gauche-infini",        "Un pli à gauche sur une liste infinie"),
        ("croire-calcule",           "Croire qu'une expression a été calculée"),
        ("mesurer-sans-mesurer",     "Mesurer sans mesurer")],
}

SILENCIEUSES = {"base-produit-zero", "eta-mauvais-argument", "instance-fautive",
                "length-sur-maybe", "foldl-sans-apostrophe", "priorite-application"}


# --------------------------------------------------------------- lecture

def lire_journal(chemin):
    lignes = []
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if ligne:
                lignes.append(json.loads(ligne))
    return lignes


def agreger(journal, chapitre):
    """Compte les erreurs du chapitre, par categorie, et le nombre d'apprenants touches."""
    connues = dict(CATALOGUE.get(chapitre, []))
    soumissions = [e for e in journal if e.get("chapitre") == chapitre]
    erreurs = [e for e in soumissions if e.get("verdict") != "reussite"]
    par_cat = collections.Counter()
    apprenants = collections.defaultdict(set)
    messages = {}
    for e in erreurs:
        c = e.get("categorie", "unclassified")
        if c not in connues and c != "unclassified":
            c = "unclassified:" + c
        par_cat[c] += 1
        apprenants[c].add(e.get("apprenant"))
        if e.get("message_ghc") and c not in messages:
            messages[c] = e["message_ghc"]
    return {
        "chapitre": chapitre,
        "soumissions": len(soumissions),
        "erreurs": len(erreurs),
        "apprenants": len({e.get("apprenant") for e in soumissions}),
        "par_categorie": par_cat,
        "touches": {c: len(a) for c, a in apprenants.items()},
        "messages": messages,
        "libelles": connues,
    }


# --------------------------------------------------------------- sortie

def rubrique(ag):
    """Engendre le squelette de la rubrique, dans l'ordre des frequences observees."""
    n_app = ag["apprenants"] or 1
    lignes = ["## %d.x Ce que le tuteur observe" % ag["chapitre"], ""]
    lignes.append("*Relevé sur %d soumissions de %d apprenants ; %d erreurs.*"
                  % (ag["soumissions"], ag["apprenants"], ag["erreurs"]))
    lignes.append("")
    for cat, n in ag["par_categorie"].most_common():
        libelle = ag["libelles"].get(cat, "À NOMMER — catégorie nouvelle : " + cat)
        part = 100.0 * ag["touches"].get(cat, 0) / n_app
        lignes.append("**%s.** %d occurrences, %.0f %% des apprenants."
                      % (libelle, n, part))
        if cat in SILENCIEUSES:
            lignes.append("")
            lignes.append("> Erreur silencieuse : le code compile. À signaler comme telle.")
        msg = ag["messages"].get(cat)
        lignes.append("")
        lignes.append("```")
        lignes.append(msg.strip() if msg else "[message GHC à coller depuis le journal]")
        lignes.append("```")
        lignes.append("")
        lignes.append("[commentaire à rédiger : ce que l'étudiant a supposé, et la règle à retenir]")
        lignes.append("")
    non_classees = [c for c in ag["par_categorie"] if c.startswith("unclassified")]
    if non_classees:
        lignes.append("*%d catégorie(s) non classée(s) : le catalogue doit s'étendre.*"
                      % len(non_classees))
    return "\n".join(lignes)


def tableau(journal):
    """Vue d'ensemble par chapitre, pour la console enseignante."""
    out = ["chapitre  soumissions  erreurs  taux   erreur dominante"]
    out.append("-" * 74)
    for ch in sorted(CATALOGUE):
        ag = agreger(journal, ch)
        if not ag["soumissions"]:
            continue
        dom, n = (ag["par_categorie"].most_common(1) or [("—", 0)])[0]
        taux = 100.0 * ag["erreurs"] / ag["soumissions"]
        out.append("   %-7d %-12d %-8d %-6.0f %s (%d)"
                   % (ch, ag["soumissions"], ag["erreurs"], taux,
                      ag["libelles"].get(dom, dom), n))
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("usage : python3 releves.py journal.jsonl [chapitre]")
        sys.exit(0)
    journal = lire_journal(sys.argv[1])
    if len(sys.argv) > 2:
        print(rubrique(agreger(journal, int(sys.argv[2]))))
    else:
        print(tableau(journal))
