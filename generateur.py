"""Generateur d'activites et politique de session de HaskellTutor 3.

Lit le referentiel, engendre les activites d'une famille, admet ou ecarte les
soumissions, decide a chaque pas ce que l'apprenant fait ensuite, et declenche
la remontee quand l'alignement de son propre corpus le permet.

Depend de normalisation.py (forme canonique) et de remontee.py (anti-unification).
"""

import json, random, sys
sys.path.insert(0, ".")
import normalisation as N
import remontee as R

# ============================================================ 1. donnees

def charger(chemin="referentiel.json"):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)

def concept(ref, cid):
    for p in ref["paliers"]:
        for c in p["concepts"]:
            if c["id"] == cid:
                return c, p
    raise KeyError(cid)


# ============================================================ 2. enonces

GABARITS = {
    "F-fold": [
        ("somme", "[Int] -> Int", "0", "+",
         "Une liste de relevés de température. Écrivez `somme` qui en donne le total."),
        ("produit", "[Int] -> Int", "1", "*",
         "Un facteur d'échelle par étage. Écrivez `produit` qui donne le facteur global."),
        ("longueur", "[a] -> Int", "0", "ignore",
         "Un inventaire dont les éléments importent peu. Écrivez `longueur` qui les compte."),
        ("aplatir", "[[String]] -> [String]", "[]", "++",
         "Des paragraphes découpés en listes de mots. Écrivez `aplatir` qui les remet bout à bout."),
        ("toutVrai", "[Bool] -> Bool", "True", "&&",
         "Les résultats de plusieurs vérifications. Écrivez `toutVrai` qui dit si toutes ont réussi."),
    ],
    "F-map": [
        ("doubler", "[Int] -> [Int]", "[]", "2 *",
         "Des quantités à convertir. Écrivez `doubler`."),
        ("initiales", "[String] -> [Char]", "[]", "head",
         "Une liste de prénoms. Écrivez `initiales` qui donne la première lettre de chacun."),
        ("notes", "[(String,Int)] -> [Int]", "[]", "snd",
         "Un relevé nom-note. Écrivez `notes` qui ne garde que les notes."),
        ("majuscules", "[Char] -> [Char]", "[]", "toUpper",
         "Un texte en minuscules. Écrivez `majuscules`."),
    ],
    "F-filter": [
        ("pairs", "[Int] -> [Int]", "[]", "even",
         "Des numéros de place. Écrivez `pairs` qui ne garde que les pairs."),
        ("nonVides", "[String] -> [String]", "[]", "not . null",
         "Des champs de formulaire. Écrivez `nonVides` qui écarte les champs laissés vides."),
        ("admis", "[(String,Int)] -> [(String,Int)]", "[]", "snd >= 60",
         "Un relevé nom-note. Écrivez `admis` qui ne garde que les reçus."),
    ],
}

def engendrer(famille, deja_servis, exclus=()):
    """Choisit un ancrage non encore servi. La famille F-fold impose de servir
    au moins un ancrage dont l'operation ignore l'element avant la remontee."""
    libres = [g for g in GABARITS[famille] if g[0] not in deja_servis and g[0] not in exclus]
    if not libres:
        return None
    if famille == "F-fold":
        deja_ignore = any(g[3] == "ignore" for g in GABARITS[famille] if g[0] in deja_servis)
        restants_apres = len(libres) - 1
        if not deja_ignore and restants_apres <= 1:
            for g in libres:
                if g[3] == "ignore":
                    return g            # obligation du referentiel
    return libres[0]


# ============================================================ 3. admission

FORMES_ATTENDUES = {
    "F-fold": ("structurel-droit",),
    "F-map": ("structurel-droit",),
    "F-filter": ("structurel-garde", "structurel-droit"),
}

def admettre(nom, source, famille, tests_reussis):
    """Regle d'admission au corpus d'alignement."""
    if not tests_reussis:
        return {"admis": False, "motif": "tests non reussis", "analyse": None}
    a = N.analyser(nom, source)
    if a["forme"] not in FORMES_ATTENDUES[famille]:
        return {"admis": False,
                "motif": "correcte mais non alignable (%s)" % a["forme"],
                "analyse": a}
    return {"admis": True, "motif": "", "analyse": a}


# ============================================================ 4. alignement

def etat_alignement(corpus):
    """corpus : liste de (nom, source). Normalise chaque soumission, puis anti-unifie
    les formes canoniques. Renvoie (nb de points de variation, forme generale)."""
    formes, bases = [], []
    for nom, src in corpus:
        a = N.analyser(nom, src)
        if a["canon"] is None:
            continue
        formes.append(R.parse(R.tokens(a["canon"])))
        bases.append(a["base"])
    if len(formes) < 2:
        return 0, None
    R.Trou.n = 0
    subst = {}
    g = formes[0]
    for f in formes[1:]:
        g = R.antiunifier(g, f, subst)
    nb = len(subst) + (1 if len(set(bases)) > 1 else 0)
    return nb, R.rendre(g)


def valider_famille(famille, attendu):
    """Une famille est bien formee si l'alignement de ses propres solutions de
    reference rend exactement le nombre de points de variation vise. Ce controle
    se fait au chargement, sans qu'aucun apprenant l'ait subie."""
    corpus = [(g[0], SOLUTIONS[g[0]]) for g in GABARITS[famille] if g[0] in SOLUTIONS]
    nb, forme = etat_alignement(corpus)
    return {"famille": famille, "ancrages": len(corpus), "points": nb,
            "attendu": attendu, "conforme": nb == attendu, "forme": forme}


# ============================================================ 5. politique

class Apprenant:
    def __init__(self, nom):
        self.nom = nom
        self.etats = {}          # concept -> "instances" | "generalised" | "acquired"
        self.corpus = {}         # concept -> [(nom, source)]
        self.ecartes = {}        # concept -> [(nom, motif)]
        self.servis = {}         # concept -> set(noms d'ancrages)
        self.reemplois = {}      # concept -> int
        self.stabilite = {}      # concept -> nb de points de variation au pas precedent

    def init(self, cid):
        self.etats.setdefault(cid, "instances")
        self.corpus.setdefault(cid, [])
        self.ecartes.setdefault(cid, [])
        self.servis.setdefault(cid, set())
        self.reemplois.setdefault(cid, 0)

def decider(ref, ap, cid):
    """Quatre decisions possibles, plus le guidage."""
    c, palier = concept(ref, cid)
    r = ref["reglages"]
    ap.init(cid)
    n = len(ap.corpus[cid])
    attendu = c["generalisation"]["points_de_variation_attendus"] if c["generalisation"] else None

    if ap.etats[cid] == "generalised":
        if ap.reemplois[cid] >= r["reemploi_requis"]:
            return ("next_tier", "%d reemplois spontanes obtenus" % ap.reemplois[cid])
        return ("reuse", "reemploi %d sur %d" % (ap.reemplois[cid], r["reemploi_requis"]))

    if n < r["instances_min"]:
        return ("instance", "corpus insuffisant (%d < %d)" % (n, r["instances_min"]))

    nb, forme = etat_alignement(ap.corpus[cid])
    stable = ap.stabilite.get(cid) == nb
    ap.stabilite[cid] = nb

    if nb == attendu and stable:
        return ("abstraction", "alignement stable a %d points de variation" % nb)
    if n >= r["instances_max"]:
        return ("guidance", "plafond de %d instances atteint, alignement a %d point(s)"
                % (r["instances_max"], nb))
    if nb != attendu:
        return ("instance", "alignement a %d point(s), le referentiel en attend %d" % (nb, attendu))
    return ("instance", "alignement a %d points mais instable" % nb)


# ============================================================ 6. simulation

SOLUTIONS = {
    "somme":      "somme [] = 0\nsomme (x:xs) = x + somme xs",
    "produit":    "produit [] = 1\nproduit (x:xs) = x * produit xs",
    "longueur":   "longueur [] = 0\nlongueur (x:xs) = 1 + longueur xs",
    "aplatir":    "aplatir [] = []\naplatir (p:ps) = p ++ aplatir ps",
    "toutVrai":   "toutVrai [] = True\ntoutVrai (b:bs) = b && toutVrai bs",
    "unionTriee": "unionTriee [] = []\nunionTriee (l:ls) = fusion l (unionTriee ls)",
}

SOLUTIONS.update({
    "doubler":    "doubler [] = []\ndoubler (x:xs) = 2 * x : doubler xs",
    "initiales":  "initiales [] = []\ninitiales (n:ns) = head n : initiales ns",
    "notes":      "notes [] = []\nnotes (p:ps) = snd p : notes ps",
    "majuscules": "majuscules [] = []\nmajuscules (c:cs) = toUpper c : majuscules cs",
})

SOLUTIONS.update({
    "pairs":    "pairs [] = []\npairs (x:xs)\n  | even x = x : pairs xs\n  | otherwise = pairs xs",
    "nonVides": "nonVides [] = []\nnonVides (s:ss)\n  | not (null s) = s : nonVides ss\n  | otherwise = nonVides ss",
    "admis":    "admis [] = []\nadmis (p:ps)\n  | snd p >= 60 = p : admis ps\n  | otherwise = admis ps",
})

# solutions de reference des familles ajoutees, pour le controle au chargement
SOLUTIONS.update({
    "estVide":   "estVide [] = True\nestVide (_:_) = False",
    "premier":   "premier [] = 0\npremier (x:_) = x",
    "reste":     "reste [] = []\nreste (_:xs) = xs",
    "majuscules2": "majuscules [] = []\nmajuscules (c:cs) = toUpper c : majuscules cs",
    "compteA":   "compteA [] = 0\ncompteA (c:cs)\n  | c == 'a' = 1 + compteA cs\n  | otherwise = compteA cs",
    "positifs":  "positifs [] = []\npositifs (x:xs)\n  | x > 0 = x : positifs xs\n  | otherwise = positifs xs",
})

GABARITS.update({
    "bare-recursion": [
        ("somme", "[Int] -> Int", "0", "+", "Total des releves."),
        ("longueur", "[a] -> Int", "0", "ignore", "Nombre d'elements."),
        ("majuscules2", "String -> String", "[]", "toUpper", "Texte en majuscules."),
    ],
    "F-filter-bis": [
        ("compteA", "String -> Int", "0", "garde", "Compter les a."),
        ("positifs", "[Int] -> [Int]", "[]", "garde", "Garder les positifs."),
    ],
})
FORMES_ATTENDUES.update({
    "bare-recursion": ("structurel-droit",),
    "F-filter-bis": ("structurel-garde", "structurel-droit"),
})

# ---- solutions de reference des seize familles, pour le controle au chargement
REFERENCES = {
 "F-map": ([("doubler", SOLUTIONS["doubler"]), ("initiales", SOLUTIONS["initiales"]),
                       ("notes", SOLUTIONS["notes"]), ("majuscules", SOLUTIONS["majuscules"])], []),
 "F-filter": ([("pairs", SOLUTIONS["pairs"]), ("nonVides", SOLUTIONS["nonVides"]),
                  ("admis", SOLUTIONS["admis"])], []),
 "F-fold": ([("somme", SOLUTIONS["somme"]), ("produit", SOLUTIONS["produit"]),
            ("longueur", SOLUTIONS["longueur"]), ("aplatir", SOLUTIONS["aplatir"]),
            ("toutVrai", SOLUTIONS["toutVrai"])], []),
 "F-tree": ([
   ("sommeA", "sommeA Feuille = 0\nsommeA (Noeud g x d) = sommeA g + x + sommeA d"),
   ("tailleA", "tailleA Feuille = 0\ntailleA (Noeud g x d) = tailleA g + 1 + tailleA d"),
   ("listerA", "listerA Feuille = []\nlisterA (Noeud g x d) = listerA g ++ [x] ++ listerA d"),
   ("hauteurA", "hauteurA Feuille = 0\nhauteurA (Noeud g x d) = 1 + max (hauteurA g) (hauteurA d)")], []),
 "F-failure": ([
   ("premierS", "premierS [] = Nothing\npremierS (x:xs) = Just x"),
   ("maximumS", "maximumS [] = Nothing\nmaximumS (x:xs) = Just (foldr1 max (x:xs))"),
   ("moyenneS", "moyenneS [] = Nothing\nmoyenneS (x:xs) = Just (moy (x:xs))")], []),
 "F-compose": ([
   ("nbMots", "nbMots s = length (words s)"),
   ("majInitiale", "majInitiale s = toUpper (head s)"),
   ("nonVide", "nonVide s = not (null s)")], []),
 "F-partial": ([
   ("doublerTous", "doublerTous xs = map LAM xs"),
   ("garderPairs", "garderPairs xs = filter even xs"),
   ("initiales", "initiales ns = map head ns")], []),
 "F-chain": ([
   ("a", "a n = case f n of Nothing -> Nothing ; Just s -> g s"),
   ("b", "b n = case h n of Nothing -> Nothing ; Just s -> k s"),
   ("c", "c n = case m n of Nothing -> Nothing ; Just s -> p s")], []),
 "F-instances": ([], ["Forme -> String", "Jour -> String", "Reponse -> String"]),
 "F-fmap": ([], ["(a -> b) -> [a] -> [b]", "(a -> b) -> Arbre a -> Arbre b",
                 "(a -> b) -> Boite a -> Boite b"]),
}

ACCUMULATEUR = {
    "somme": "somme xs = go 0 xs\n  where go acc [] = acc\n        go acc (y:ys) = go (acc + y) ys",
}

def simuler(ref, cid, profil="direct", trace=True, exclus=()):
    ap = Apprenant("Amina")
    ap.init(cid)
    c, _ = concept(ref, cid)
    famille = c["famille"]
    pas = 0
    journal = []
    while pas < 12:
        pas += 1
        decision, motif = decider(ref, ap, cid)
        journal.append(("decision", decision, motif))
        if decision in ("abstraction", "guidance", "next_tier"):
            break
        if decision == "reuse":
            ap.reemplois[cid] += 1
            journal.append(("reuse", "item de reemploi reussi avec le schema", ""))
            continue
        g = engendrer(famille, ap.servis[cid], exclus)
        if g is None:
            journal.append(("epuise", "plus d'ancrage disponible", ""))
            break
        nom, typ, neutre, op, enonce = g
        ap.servis[cid].add(nom)
        src = ACCUMULATEUR[nom] if (profil == "accumulateur" and nom in ACCUMULATEUR) else SOLUTIONS[nom]
        v = admettre(nom, src, famille, tests_reussis=True)
        journal.append(("activite", nom, "%s | neutre %s | operation %s" % (typ, neutre, op)))
        if v["admis"]:
            ap.corpus[cid].append((nom, src))
            journal.append(("admission", "admise au corpus", v["analyse"]["canon"]))
        else:
            ap.ecartes[cid].append((nom, v["motif"]))
            journal.append(("admission", "ecartee", v["motif"]))
    return ap, journal


def afficher(ref, cid, profil, titre, exclus=()):
    ap, journal = simuler(ref, cid, profil, exclus=exclus)
    print("=" * 82)
    print(titre)
    print("-" * 82)
    for genre, a, b in journal:
        if genre == "decision":
            print("  decision   : %-16s (%s)" % (a, b))
        elif genre == "activite":
            print("  activite   : %-16s %s" % (a, b))
        elif genre == "admission":
            print("               %-16s %s" % (a, b))
        else:
            print("  %-10s : %s %s" % (genre, a, b))
    nb, forme = etat_alignement(ap.corpus[cid])
    print("-" * 82)
    print("  corpus      : %s" % ", ".join(n for n, _ in ap.corpus[cid]))
    print("  ecartees    : %s" % (", ".join("%s (%s)" % e for e in ap.ecartes[cid]) or "none"))
    print("  alignement  : %d point(s) de variation, forme %s" % (nb, forme))
    print()


if __name__ == "__main__":
    ref = charger()

    print("CONTROLE DES FAMILLES AU CHARGEMENT")
    print("-" * 82)
    for cid in ("pli-droit", "transformation", "selection"):
        c, _ = concept(ref, cid)
        v = valider_famille(c["famille"], c["generalisation"]["points_de_variation_attendus"])
        print("  %-18s %d ancrages, alignement %d point(s), attendu %d  ->  %s"
              % (v["famille"], v["ancrages"], v["points"], v["attendu"],
                 "conforme" if v["conforme"] else "FAMILLE MAL FORMEE, non servie"))

    print()
    print("ETAT DES SEIZE FAMILLES DU REFERENTIEL")
    print("-" * 82)
    import normalisation2 as N2
    for nom, spec in ref["familles"].items():
        v = spec.get("validation", {})
        mode = v.get("mode", "none")
        n = len(spec["ancrages"])
        oblig = "oui" if "obligation" in spec else "non"
        if mode == "none":
            etat = "sans remontee, rien a aligner"
        elif mode == "invariant":
            corpus, _ = REFERENCES[nom]
            ok, det = N2.verifier_invariant_final(corpus)
            etat = "invariant %s (%s)" % (
                "verifie" if ok else "NOT VERIFIE",
                ", ".join("%s:%d%s" % (n, o, "" if f else " pas final") for n, o, f in det))
        elif mode == "confrontation":
            etat = "confrontation, aucune generalisation attendue"
        elif nom in REFERENCES:
            corpus, sigs = REFERENCES[nom]
            if mode == "signatures":
                obtenu, forme = N2.aligner_signatures(sigs)
            else:
                fins, forme, blocs = N2.aligner_corps(corpus)
                obtenu = blocs if v.get("granularite") == "blocs" else fins
            att = v.get("attendu")
            etat = "%s %d, attendu %d : %s" % (
                v.get("granularite", "fins"), obtenu, att,
                "conforme" if obtenu == att else "NOT CONFORME")
        else:
            etat = "solutions de reference absentes"
        print("  %-20s ch.%-2s %d ancrages  oblig.%-4s %-13s %s"
              % (nom, spec["chapitre"], n, oblig, mode, etat))
    print()

    afficher(ref, "pli-droit", "direct",
             "PARCOURS 1 — apprenante qui ecrit des recursions directes")
    afficher(ref, "pli-droit", "accumulateur",
             "PARCOURS 2 — la premiere soumission est un pli a gauche")
    afficher(ref, "transformation", "direct",
             "PARCOURS 3 — famille de transformation, une seule variation attendue")

    import copy
    ref4 = copy.deepcopy(ref)
    ref4["reglages"]["instances_max"] = 3
    afficher(ref4, "pli-droit", "direct",
             "PARCOURS 4 — l'ancrage qui ignore l'element n'a pas ete servi : plateau",
             exclus=("longueur",))
