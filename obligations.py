"""Induction des obligations d'une famille, par ablation.

Une famille d'activites porte des « obligations » : des ancrages sans lesquels la
generalisation visee n'est pas atteignable. Dans HaskellTutor elles ont ete trouvees
a la main, en redigeant les chapitres. Ce module les trouve mecaniquement.

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


def points(corpus, granularite="fins"):
    fins, forme, blocs = N2.aligner_corps(corpus)
    return (blocs if granularite == "blocs" else fins), forme


def induire(corpus, granularite="fins"):
    """Renvoie, pour chaque ancrage, l'effet de son retrait sur l'alignement."""
    complet, forme = points(corpus, granularite)
    resultats = []
    for i, (nom, code) in enumerate(corpus):
        reste = corpus[:i] + corpus[i + 1:]
        if len(reste) < 2:
            continue
        p, f = points(reste, granularite)
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


def rapport(nom_famille, corpus, attendu=None, granularite="fins"):
    r = induire(corpus, granularite)
    lignes = ["%s — %d ancrages, alignement a %d point(s)%s"
              % (nom_famille, len(corpus), r["complet"],
                 "" if attendu is None else " (attendu %d)" % attendu),
              "  forme complete : %s" % r["forme"], ""]
    lignes.append("  %-14s %-10s %-8s %s" % ("ancrage", "sans lui", "ecart", "verdict"))
    for a in r["ancrages"]:
        lignes.append("  %-14s %-10d %-+8d %s"
                      % (a["ancrage"], a["sans_lui"], a["ecart"],
                         "PORTEUR" if a["porteur"] else "interchangeable"))
    lignes.append("")
    if r["obligatoires"]:
        lignes.append("  obligation induite : servir %s"
                      % " et ".join(r["obligatoires"]))
    else:
        lignes.append("  aucune obligation : tous les ancrages sont interchangeables ; "
                      "la famille peut etre servie par n'importe quel sous-ensemble "
                      "de taille suffisante")
    return "\n".join(lignes)


if __name__ == "__main__":
    import generateur as G

    print("INDUCTION DES OBLIGATIONS PAR ABLATION")
    print("=" * 78)
    print()
    cas = [("F-fold", "fins", 3), ("F-map", "fins", 1),
           ("F-filter", "fins", 1), ("F-tree", "blocs", 2),
           ("F-failure", "fins", 1)]
    for nom, gran, attendu in cas:
        corpus, _ = G.REFERENCES[nom]
        print(rapport(nom, corpus, attendu, gran))
        print()
