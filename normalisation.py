"""Normalisation des soumissions d'apprenants avant alignement.

Le moteur de remontee suppose des definitions comparables. Les apprenants, eux,
ecrivent des gardes, des if, des where, des case, des accumulateurs, et donnent
a leurs variables les noms qu'ils veulent. Ce module ramene ces ecritures a une
forme canonique, ou dit pourquoi il n'y parvient pas.

Formes reconnues
  structurel-droit   f [] = z ; f (x:xs) = <expr contenant f xs>      -> foldr
  structurel-garde   idem avec gardes ou if-then-else                 -> foldr / filter
  accumulateur       f xs = go z xs where go acc [] = acc ; ...       -> foldl
  non-structurel     tout le reste                                    -> non aligne
"""

import re

# ------------------------------------------------------------ 1. pretraitement

def decouper(source):
    """Supprime signatures et commentaires, recolle gardes et where sur leur equation."""
    brut = []
    for ligne in source.splitlines():
        ligne = ligne.split("--")[0].rstrip()
        if not ligne.strip() or re.match(r"^\s*\w[\w']*\s*::", ligne):
            continue
        brut.append(ligne)
    eqs, courante = [], None
    for ligne in brut:
        indente = ligne[:1] in (" ", "\t")
        nu = ligne.strip()
        if indente and courante is not None:
            courante += " " + nu
        else:
            if courante is not None:
                eqs.append(courante)
            courante = nu
    if courante is not None:
        eqs.append(courante)
    return eqs

def separer_where(eq):
    """Renvoie (equation, [equations locales])."""
    m = re.search(r"\bwhere\b", eq)
    if not m:
        return eq.strip(), []
    corps = eq[m.end():].strip()
    locales = [p.strip() for p in re.split(r";", corps) if p.strip()]
    return eq[:m.start()].strip(), locales

def gardes(eq):
    """Transforme les gardes en une liste [(condition, expression)] ; otherwise -> None."""
    if "|" not in eq:
        return None
    tete, reste = eq.split("|", 1)
    branches = []
    coupe = re.compile(r"(?<![=<>/!])=(?!=)")
    for morceau in reste.split("|"):
        m = coupe.search(morceau)
        cond, expr = morceau[:m.start()], morceau[m.end():]
        cond = cond.strip()
        branches.append((None if cond == "otherwise" else cond, expr.strip()))
    return tete.strip(), branches

# ------------------------------------------------------------ 2. classification

CLAUSE = re.compile(r"^(\w[\w']*)\s*(.*?)\s*=\s*(.+)$")

def analyser(nom, source, commutatif=("+", "*")):
    """Renvoie un dictionnaire decrivant la forme canonique, ou l'echec."""
    eqs = decouper(source)
    principales, locales = [], []
    for eq in eqs:
        e, loc = separer_where(eq)
        principales.append(e)
        locales.extend(loc)

    # cas accumulateur : une seule equation principale qui delegue a une locale
    if len(principales) == 1 and locales:
        m = CLAUSE.match(principales[0])
        if m and re.search(r"\b(\w[\w']*)\s+\S+\s+\S+", m.group(3)):
            aux = re.match(r"(\w[\w']*)\s+(\S+)", m.group(3))
            if aux and any(l.startswith(aux.group(1)) for l in locales):
                return {"nom": nom, "forme": "accumulateur",
                        "auxiliaire": aux.group(1), "depart": aux.group(2),
                        "canon": None,
                        "note": "pli a gauche : l'operation est appliquee avant l'appel "
                                "recursif, pas apres. Ne s'aligne pas avec les plis a droite."}

    base, pas, cond = None, None, None
    for eq in principales:
        g = gardes(eq)
        if g:
            tete, branches = g
            m = CLAUSE.match(tete + " = 0")   # pour recuperer nom et motif
            motif = tete[len(nom):].strip()
            if motif in ("[]",):
                base = branches[0][1]
                continue
            garde, alors = branches[0]
            sinon = branches[1][1] if len(branches) > 1 else None
            cond = (garde, alors, sinon)
            pas = None
            motif_rec = motif
            continue
        m = CLAUSE.match(eq)
        if not m:
            continue
        _, motif, corps = m.groups()
        if motif.strip() == "[]":
            base = corps.strip()
        else:
            pas, motif_rec = corps.strip(), motif.strip()

    if base is None or (pas is None and cond is None):
        return {"nom": nom, "forme": "non-structurel", "canon": None,
                "note": "ni cas de base ni cas recursif identifiables sur une liste."}

    mm = re.match(r"\(?\s*(\w[\w']*)\s*:\s*(\w[\w']*)\s*\)?", motif_rec)
    if not mm:
        return {"nom": nom, "forme": "non-structurel", "canon": None,
                "note": "le motif du cas recursif n'est pas de la forme (tete:queue)."}
    tete, queue = mm.groups()

    def canoniser(expr):
        if expr is None:
            return None
        e = " " + expr.strip() + " "
        e = re.sub(r"\bif\b(.*?)\bthen\b(.*?)\belse\b(.*)", r"COND (\1) (\2) (\3)", e)
        e = re.sub(r"\b%s\s+%s\b" % (nom, queue), " REC ", e)
        e = re.sub(r"\b%s\b" % tete, " ELEM ", e)
        e = re.sub(r"\b%s\b" % queue, " REST ", e)
        e = re.sub(r"\s+", " ", e).strip()
        for op in commutatif:
            m = re.match(r"^REC \%s (.+)$" % op if op != "+" else r"^REC \+ (.+)$", e)
            if m:
                e = "%s %s REC" % (m.group(1), op)
        return e

    if cond is not None:
        garde, alors, sinon = cond
        canon = _serrer("COND (%s) (%s) (%s)" % (canoniser(garde), canoniser(alors), canoniser(sinon)))
        forme = "structurel-garde"
    else:
        canon = _serrer(canoniser(pas))
        forme = "structurel-droit"

    return {"nom": nom, "forme": forme, "base": base.strip(), "canon": canon, "note": ""}

def _serrer(e):
    """Uniformise les espaces pour que deux ecritures d'une meme forme coincident."""
    if e is None:
        return None
    e = re.sub(r"\s*,\s*", ", ", e)
    e = re.sub(r"\(\s+", "(", e)
    e = re.sub(r"\s+\)", ")", e)
    return re.sub(r"\s+", " ", e).strip()

# ------------------------------------------------------------ 3. mise en oeuvre

VARIANTES_SOMME = [
    ("somme — recursion directe", """
somme :: [Int] -> Int
somme []     = 0
somme (x:xs) = x + somme xs
"""),
    ("somme — autres noms de variables", """
somme (n:ns) = n + somme ns
somme [] = 0
"""),
    ("somme — operandes inverses", """
somme [] = 0
somme (x:xs) = somme xs + x
"""),
    ("somme — accumulateur", """
somme xs = go 0 xs
  where go acc []     = acc
        go acc (y:ys) = go (acc + y) ys
"""),
]

VARIANTES_PAIRS = [
    ("pairs — gardes", """
pairs [] = []
pairs (x:xs)
  | even x    = x : pairs xs
  | otherwise = pairs xs
"""),
    ("pairs — if then else", """
pairs [] = []
pairs (x:xs) = if even x then x : pairs xs else pairs xs
"""),
    ("pairs — condition ecrite autrement", """
pairs [] = []
pairs (v:vs)
  | mod v 2 == 0 = v : pairs vs
  | otherwise    = pairs vs
"""),
]

def rapport(titre, variantes, nom):
    print("=" * 78)
    print(titre)
    print("-" * 78)
    formes = {}
    for etiquette, src in variantes:
        r = analyser(nom, src)
        cle = (r.get("base"), r.get("canon"))
        formes.setdefault(cle, []).append(etiquette)
        print("%-38s %-18s %s" % (etiquette, r["forme"],
                                  r["canon"] if r["canon"] else "—"))
        if r["note"]:
            print("%-38s %s" % ("", r["note"]))
    alignables = {k: v for k, v in formes.items() if k[1] is not None}
    print("-" * 78)
    print("Classes d'equivalence apres normalisation : %d" % len(alignables))
    for (base, canon), etiquettes in alignables.items():
        print("   base %-4s pas %-24s <- %d soumission(s)" % (base, canon, len(etiquettes)))
    horsjeu = [v for k, v in formes.items() if k[1] is None]
    if horsjeu:
        print("   %d soumission(s) hors alignement" % sum(len(x) for x in horsjeu))
    print()

if __name__ == "__main__":
    rapport("Quatre copies pour le meme exercice : somme", VARIANTES_SOMME, "somme")
    rapport("Trois copies pour le meme exercice : pairs", VARIANTES_PAIRS, "pairs")
