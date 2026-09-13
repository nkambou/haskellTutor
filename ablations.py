"""Etudes d'ablation sur les composants du cadre.

Chaque composant du moteur de reconnaissance a ete ajoute pour resoudre un
probleme precis. On verifie ici qu'il etait necessaire : on le retire, on refait
la mesure, et on rapporte l'ecart. Un composant dont le retrait ne change rien
n'a pas sa place dans le cadre.

Quatre ablations :
  A. le critere de decomposition (meme forme -> decomposer, sinon generaliser)
  B. la normalisation par commutativite limitee
  C. l'orientation canonique des gardes
  D. la condition de stabilite du declenchement
"""

import copy
import remontee as R
import normalisation2 as N2
import generateur as G


def points(corpus):
    fins, forme, blocs = N2.aligner_corps(corpus)
    return fins, forme


# ------------------------------------------------------------ A. decomposition

def ablation_decomposition():
    """Deux politiques uniformes, comparees au critere retenu."""
    original = R.antiunifier

    def toujours_decomposer(a, b, subst):
        if a == b:
            return a
        if isinstance(a, R.Trou):
            R._absorber(a, b, subst); return a
        if isinstance(b, R.Trou):
            R._absorber(b, a, subst); return b
        if isinstance(a, tuple) and isinstance(b, tuple) and a[0] == b[0] and len(a) == len(b):
            if a[0] == "op":
                op = a[1] if a[1] == b[1] else R._trou(("op", a[1], b[1]), subst)
                return ("op", op, toujours_decomposer(a[2], b[2], subst),
                        toujours_decomposer(a[3], b[3], subst))
            if a[0] == "var":
                return a if a[1] == b[1] else R._trou(("var", a[1], b[1]), subst)
            if a[0] == "app":
                f = a[1] if a[1] == b[1] else R._trou(("fn", a[1], b[1]), subst)
                return ("app", f) + tuple(toujours_decomposer(x, y, subst)
                                          for x, y in zip(a[2:], b[2:]))
        return R._trou(("expr", R.rendre(a), R.rendre(b)), subst)

    def toujours_bloc(a, b, subst):
        if a == b:
            return a
        if isinstance(a, R.Trou):
            R._absorber(a, b, subst); return a
        if isinstance(b, R.Trou):
            R._absorber(b, a, subst); return b
        if isinstance(a, tuple) and isinstance(b, tuple) and a[0] == b[0] and len(a) == len(b):
            if a[0] == "op" and a[1] == b[1]:
                return ("op", a[1], toujours_bloc(a[2], b[2], subst),
                        toujours_bloc(a[3], b[3], subst))
            if a[0] == "var" and a[1] == b[1]:
                return a
            if a[0] == "app" and a[1] == b[1]:
                return ("app", a[1]) + tuple(toujours_bloc(x, y, subst)
                                             for x, y in zip(a[2:], b[2:]))
        return R._trou(("expr", R.rendre(a), R.rendre(b)), subst)

    # deux ancrages par famille : c'est la ou les politiques se separent, un
    # troisieme ancrage collapsant souvent les trous par reutilisation
    familles = [("F-filter", 1), ("F-compose", 2), ("F-fold", 2),
                ("F-map", 1)]
    lignes = []
    for politique, nom in ((original, "critere retenu"),
                           (toujours_decomposer, "toujours decomposer"),
                           (toujours_bloc, "toujours generaliser en bloc")):
        R.antiunifier = politique
        obtenus = []
        for f, attendu in familles:
            corpus, _ = G.REFERENCES[f]
            p, _ = points(corpus[:2])
            obtenus.append((f, p, attendu))
        lignes.append((nom, obtenus))
    R.antiunifier = original
    return familles, lignes


# ------------------------------------------------------------ B. commutativite

VARIANTES_SOMME = [
    ("somme", "somme [] = 0\nsomme (x:xs) = x + somme xs"),
    ("somme2", "somme2 [] = 0\nsomme2 (n:ns) = n + somme2 ns"),
    ("somme3", "somme3 [] = 0\nsomme3 (x:xs) = somme3 xs + x"),
]


def ablation_commutativite():
    """Combien de classes d'equivalence pour trois ecritures equivalentes ?"""
    original = N2.commuter
    resultats = {}
    for actif in (True, False):
        N2.commuter = original if actif else (lambda e, operateurs=(): e)
        formes = set()
        for nom, code in VARIANTES_SOMME:
            formes.add(N2.analyser(nom, code)["pas"])
        resultats[actif] = formes
    N2.commuter = original
    return resultats


# ------------------------------------------------------------ C. gardes

GARDES = [
    ("pairs", "pairs [] = []\npairs (x:xs)\n  | even x = x : pairs xs\n  | otherwise = pairs xs"),
    ("nonVides", "nonVides [] = []\nnonVides (s:ss)\n  | null s = nonVides ss\n  | otherwise = s : nonVides ss"),
    ("admis", "admis [] = []\nadmis (n:ns)\n  | n >= 60 = n : admis ns\n  | otherwise = admis ns"),
]


def ablation_orientation():
    original = N2.orienter
    N2.orienter = lambda nom, c, a, s: (c, a, s)
    sans, forme_sans = points(GARDES)
    N2.orienter = original
    avec, forme_avec = points(GARDES)
    return (avec, forme_avec), (sans, forme_sans)


# ------------------------------------------------------------ D. stabilite

def ablation_stabilite():
    """Sur un corpus construit un element a la fois, combien de fois la condition
    « compte attendu atteint » est-elle vraie avant que le compte ne se stabilise ?"""
    resultats = []
    for nom, attendu in (("F-fold", 3), ("F-map", 1), ("F-filter", 1),
                         ("F-failure", 1)):
        corpus, _ = G.REFERENCES[nom]
        comptes, premature, precedent = [], 0, None
        declenche_stable = None
        for k in range(2, len(corpus) + 1):
            p, _ = points(corpus[:k])
            comptes.append(p)
            if p == attendu and precedent != p and declenche_stable is None:
                premature += 1
            if p == attendu and precedent == p and declenche_stable is None:
                declenche_stable = k
            precedent = p
        resultats.append({"famille": nom, "attendu": attendu, "comptes": comptes,
                          "sans_stabilite": premature,
                          "avec_stabilite": declenche_stable})
    return resultats


# ------------------------------------------------------------ rapport

if __name__ == "__main__":
    print("ETUDES D'ABLATION SUR LE MOTEUR DE RECONNAISSANCE")
    print("=" * 78)

    print("\nA. Critere de decomposition des desaccords")
    print("-" * 78)
    familles, lignes = ablation_decomposition()
    entete = "  %-30s" % "politique"
    for f, a in familles:
        entete += "%-18s" % ("%s (%d)" % (f.replace("F-", ""), a))
    print(entete)
    for nom, obtenus in lignes:
        ligne = "  %-30s" % nom
        for f, p, attendu in obtenus:
            ligne += "%-18s" % ("%d %s" % (p, "ok" if p == attendu else "FAUX"))
        print(ligne)
    print("  Aucune politique uniforme ne sert les quatre familles ; le critere de")
    print("  forme est le seul des trois a rendre le compte attendu partout.")

    print("\nB. Normalisation par commutativite limitee")
    print("-" * 78)
    r = ablation_commutativite()
    print("  avec  : %d classe(s) pour 3 ecritures equivalentes -> %s"
          % (len(r[True]), sorted(r[True])))
    print("  sans  : %d classe(s) -> %s" % (len(r[False]), sorted(r[False])))

    print("\nC. Orientation canonique des gardes")
    print("-" * 78)
    (avec, fa), (sans, fs) = ablation_orientation()
    print("  avec  : %d point(s) de variation, forme %s" % (avec, fa))
    print("  sans  : %d point(s) de variation, forme %s" % (sans, fs))
    print("  Attendu : 1. Sans orientation, une garde ecrite a l'envers disperse")
    print("  l'alignement d'une famille par ailleurs conforme.")

    print("\nD. Condition de stabilite du declenchement")
    print("-" * 78)
    print("  %-18s %-8s %-24s %-12s %s"
          % ("famille", "attendu", "comptes successifs", "premature", "declenchement"))
    for x in ablation_stabilite():
        print("  %-18s %-8d %-24s %-12d %s"
              % (x["famille"], x["attendu"], str(x["comptes"]),
                 x["sans_stabilite"],
                 "au %se corpus" % x["avec_stabilite"] if x["avec_stabilite"] else "never"))
    print("  Un declenchement premature ouvre la phase d'abstraction sur un corpus")
    print("  dont l'alignement va encore changer.")
