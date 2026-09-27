"""Induction des obligations d'une famille, par ablation.

Une famille d'activites porte des « obligations » : des ancrages sans lesquels la
generalisation visee n'est pas atteignable. Dans HaskellTutor elles ont ete trouvees
a la main, en concevant les familles. Ce module les trouve mecaniquement.

Le principe est une analyse d'ablation sur le corpus de reference. On aligne la
famille complete et on note le nombre de points de variation. Puis, pour chaque
ancrage, on le retire, on realigne le reste, et on compare. Un ancrage dont le
retrait modifie le compte est porteur : il est le seul a exhiber une des variations
que la famille doit faire voir. Un ancrage dont le retrait ne change rien est
interchangeable, ce qui est une information utile en sens inverse : la famille peut
s'en passer, ou en accepter d'autres du meme type.

Le cout est lineaire en le nombre d'ancrages et chaque alignement est immediat.
"""

import normalisation2 as N2
import remontee as R


def aligner_fournisseur(corpus, analyse):
    """Meme alignement que le noyau, a partir des formes rendues par un fournisseur
    de langage : l'inducteur ne depend alors plus de l'analyseur Haskell."""
    formes, bases = [], []
    for nom, code in corpus:
        a = analyse(nom, code)
        if a.get("pas") is None:
            continue
        formes.append(R.parse(R.tokens(a["pas"])))
        bases.append(a["base"])
    if len(formes) < 2:
        return 0, None, 0
    R.Trou.n = 0
    subst, g = {}, formes[0]
    for f in formes[1:]:
        g = R.antiunifier(g, f, subst)
    vus = set()

    def compter(x):
        if isinstance(x, R.Trou):
            vus.add(x.i)
        elif isinstance(x, tuple):
            for y in x[1:]:
                compter(y)
    compter(g)
    varie = len({b for b in bases if b is not None}) > 1
    return len(vus) + (1 if varie else 0), R.rendre(g), (1 if varie else 0) + (1 if vus else 0)


def points(corpus, granularite="fins", analyse=None):
    fins, forme, blocs = (aligner_fournisseur(corpus, analyse) if analyse
                          else N2.aligner_corps(corpus))
    return (blocs if granularite == "blocs" else fins), forme


def induire(corpus, granularite="fins", analyse=None):
    """Renvoie, pour chaque ancrage, l'effet de son retrait sur l'alignement."""
    complet, forme = points(corpus, granularite, analyse)
    resultats = []
    for i, (nom, code) in enumerate(corpus):
        reste = corpus[:i] + corpus[i + 1:]
        if len(reste) < 2:
            continue
        p, f = points(reste, granularite, analyse)
        resultats.append({
            "ancrage": nom,
            "sans_lui": p,
            "ecart": p - complet,
            "porteur": p != complet,
            "forme_sans_lui": f,
        })
    return {"complet": complet, "forme": forme, "ancrages": resultats,
            "obligatoires": [r["ancrage"] for r in resultats if r["porteur"]],
            "interchangeables": [r["ancrage"] for r in resultats if not r["porteur"]]}


def rapport(nom_famille, corpus, attendu=None, granularite="fins", analyse=None):
    r = induire(corpus, granularite, analyse)
    lignes = ["%s — %d ancrages, alignement a %d point(s)%s"
              % (nom_famille, len(corpus), r["complet"],
                 "" if attendu is None else " (attendu %d)" % attendu),
              "  forme complete : %s" % r["forme"], ""]
    lignes.append("  %-14s %-10s %-8s %-16s %s"
                  % ("ancrage", "sans lui", "ecart", "verdict", "forme sans lui"))
    for a in r["ancrages"]:
        lignes.append("  %-14s %-10d %-+8d %-16s %s"
                      % (a["ancrage"], a["sans_lui"], a["ecart"],
                         "PORTEUR" if a["porteur"] else "interchangeable",
                         a["forme_sans_lui"]))
    lignes.append("")
    if r["obligatoires"]:
        lignes.append("  obligation induite : servir %s"
                      % " et ".join(r["obligatoires"]))
    else:
        lignes.append("  aucune obligation : tous les ancrages sont interchangeables ; "
                      "la famille peut etre servie par n'importe quel sous-ensemble "
                      "de taille suffisante")
    return "\n".join(lignes)


# Famille map de l'instanciation Python, pour l'etape 4 de la section 6 :
#     python3 obligations.py --python
PY_MAP = [(n, "def %s(xs):\n    if not xs:\n        return []\n    return %s\n" % (n, pas))
          for n, pas in (("doubler", "[2 * xs[0]] + doubler(xs[1:])"),
                         ("majuscules", "[xs[0].upper()] + majuscules(xs[1:])"),
                         ("initiales", "[xs[0][0]] + initiales(xs[1:])"),
                         ("carres", "[xs[0] * xs[0]] + carres(xs[1:])"),
                         ("notes", "[xs[0][1]] + notes(xs[1:])"))]


if __name__ == "__main__" and "--python" in __import__("sys").argv:
    import os, sys
    ici = os.path.dirname(os.path.abspath(__file__))
    sys.path[:0] = [os.path.join(ici, "pytutor"), ici]
    import langue_python as LP
    print("INDUCTION DES OBLIGATIONS, FOURNISSEUR PYTHON")
    print("=" * 78)
    print()
    print(rapport("F-transformation (Python)", PY_MAP, 1, "fins", LP.analyser))
    raise SystemExit(0)

if __name__ == "__main__":
    import generateur as G

    print("INDUCTION DES OBLIGATIONS PAR ABLATION")
    print("=" * 78)
    print()
    cas = [("F-fold", "fins", 3), ("F-map", "fins", 1),
           ("F-filter", "fins", 1), ("F-tree", "blocs", 2), ("F-tree", "fins", None),
           ("F-failure", "fins", 1)]
    for nom, gran, attendu in cas:
        corpus, _ = G.REFERENCES[nom]
        print(rapport(nom, corpus, attendu, gran))
        print()
