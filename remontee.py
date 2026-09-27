"""Noyau de la remontee : reconnaitre un schema dans le code de l'apprenant.

Entree  : les definitions recursives que l'apprenant a ecrites au fil des exercices.
Sortie  : l'alignement de ces definitions et leur plus petite generalisation commune,
          c'est-a-dire ce qui reste quand on raye ce qui differe.
"""

import re, itertools

# ---------------------------------------------------------------- 1. lecture

EQ = re.compile(r"^(\w+)\s*(.*?)\s*=\s*(.+)$")

def lire(source):
    """Extrait les equations d'une definition Haskell a deux cas (base, recursif)."""
    eqs = []
    for ligne in source.strip().splitlines():
        ligne = ligne.split("--")[0].strip()
        if not ligne or "::" in ligne:
            continue
        m = EQ.match(ligne)
        if m:
            eqs.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    return eqs

# ---------------------------------------------------------------- 2. syntax

# Litteraux de chaine et de caractere, et operateurs entre accents graves, forment
# chacun un seul jeton. Tout autre caractere visible devient un jeton a lui seul :
# aucun caractere n'est ignore en silence, sans quoi deux formes differentes
# pourraient s'aligner comme si elles etaient identiques, ou l'inverse.
TOK = re.compile(r'"(?:[^"\\]|\\.)*"'
                 r"|'(?:[^'\\]|\\.)'"
                 r"|`[A-Za-z_][A-Za-z0-9_']*`"
                 r"|\(|\)|\[\]|&&|\|\||==|/=|<=|>=|\+\+"
                 r"|[A-Za-z_][A-Za-z0-9_']*|\d+|[+*/:<>-]"
                 r"|\S")
INFIXES = ["&&", "||", "==", "/=", "<=", ">=", "++", ":", "+", "-", "*", "/", "<", ">"]

def tokens(s):
    return TOK.findall(s)

def parse(ts):
    """Analyse une expression infixe simple ; renvoie un arbre (op, gauche, droite)
    ou une feuille."""
    def atome(i):
        if ts[i] == "(":
            noeud, j = expr(i + 1)
            return noeud, j + 1
        if ts[i] == "[":
            # liste en extension : [a] ou [a, b] devient (LIST a b)
            elements, j = [], i + 1
            while j < len(ts) and ts[j] != "]":
                e, j = expr(j)
                elements.append(e)
                if j < len(ts) and ts[j] == ",":
                    j += 1
            return ("app", "LIST") + tuple(elements) if elements else ("var", "[]"), j + 1
        t = ts[i]
        i += 1
        args = []
        while i < len(ts) and ts[i] not in INFIXES + [")", "]", ","]:
            a, i = atome(i)
            args.append(a)
        return (("app", t) + tuple(args) if args else ("var", t)), i

    def expr(i):
        gauche, i = atome(i)
        while i < len(ts) and ts[i] in INFIXES:
            op = ts[i]
            droite, i = atome(i + 1)
            gauche = ("op", op, gauche, droite)
        return gauche, i

    arbre, _ = expr(0)
    return arbre

# ------------------------------------------------- 3. normalisation du schema

def normaliser(nom, motif, corps):
    """Remplace l'appel recursif par le marqueur REC et les variables liees par
    ELEM et REST, pour que deux definitions differentes deviennent comparables."""
    m = re.match(r"\((\w+):(\w+)\)", motif)
    tete, queue = (m.group(1), m.group(2)) if m else ("_", "_")
    corps = re.sub(r"\b%s\s+%s\b" % (nom, queue), "REC", corps)
    if tete != "_":
        corps = re.sub(r"\b%s\b" % tete, "ELEM", corps)
    return parse(tokens(corps))

# ------------------------------------------------- 4. anti-unification

class Trou:
    """Un point de variation : ce que la craie a raye au tableau."""
    n = 0
    def __init__(self):
        Trou.n += 1
        self.i = Trou.n
    def __repr__(self):
        return "?%d" % self.i

def meme_forme(a, b):
    """Deux termes ont la meme forme s'ils ont la meme structure d'arbre, quels que
    soient les symboles portes par les noeuds. C'est le critere qui decide si un
    desaccord se decompose ou se generalise d'un bloc."""
    if isinstance(a, Trou) or isinstance(b, Trou):
        return True
    if isinstance(a, tuple) and isinstance(b, tuple):
        if a[0] != b[0] or len(a) != len(b):
            return False
        if a[0] == "var":
            return True
        debut = 2 if a[0] in ("op", "app") else 1
        return all(meme_forme(x, y) for x, y in zip(a[debut:], b[debut:]))
    return a == b


def antiunifier(a, b, subst):
    """Plus petite generalisation commune de deux arbres.
    Deux noeuds de meme forme sont conserves ; tout desaccord devient un trou,
    et un meme desaccord rencontre deux fois donne le meme trou."""
    if a == b:
        return a
    if isinstance(a, Trou):            # trou deja ouvert : on y verse la valeur nouvelle
        _absorber(a, b, subst)
        return a
    if isinstance(b, Trou):
        _absorber(b, a, subst)
        return b
    if isinstance(a, tuple) and isinstance(b, tuple) and a[0] == b[0] and len(a) == len(b):
        if a[0] == "op":
            if isinstance(a[1], Trou):
                _absorber(a[1], b[1], subst); op = a[1]
            else:
                op = a[1] if a[1] == b[1] else _trou(("op", a[1], b[1]), subst)
            return ("op", op,
                    antiunifier(a[2], b[2], subst),
                    antiunifier(a[3], b[3], subst))
        if a[0] == "var":
            return a if a[1] == b[1] else _trou(("var", a[1], b[1]), subst)
        if a[0] == "app":
            if isinstance(a[1], Trou):
                _absorber(a[1], b[1], subst)
                return ("app", a[1]) + tuple(antiunifier(x, y, subst)
                                             for x, y in zip(a[2:], b[2:]))
            if a[1] != b[1]:
                if not meme_forme(a, b):
                    # structures differentes : le desaccord porte sur le sous-terme
                    # entier, pas sur la fonction et ses arguments separement
                    return _trou(("expr", rendre(a), rendre(b)), subst)
                # meme structure, tetes differentes : la tete devient le point de
                # variation et les arguments s'alignent
                f = _trou(("fn", a[1], b[1]), subst)
                return ("app", f) + tuple(antiunifier(x, y, subst)
                                          for x, y in zip(a[2:], b[2:]))
            return ("app", a[1]) + tuple(antiunifier(x, y, subst) for x, y in zip(a[2:], b[2:]))
    return _trou(("expr", rendre(a), rendre(b)), subst)

def _absorber(t, valeur, subst):
    genre, valeurs = subst[t]
    v = valeur if isinstance(valeur, str) else rendre(valeur)
    if v not in valeurs:
        valeurs.append(v)

def _trou(cle, subst):
    """Un trou par couple de sous-termes en desaccord ; on accumule les valeurs vues."""
    genre = cle[0]
    for t, (g, valeurs) in subst.items():
        if g == genre and cle[1] in valeurs:
            for v in cle[2:]:
                if v not in valeurs:
                    valeurs.append(v)
            return t
    t = Trou()
    subst[t] = (genre, list(cle[1:]))
    return t

def rendre(a):
    if isinstance(a, Trou):
        return repr(a)
    if a[0] == "var":
        return a[1]
    if a[0] == "op":
        op = repr(a[1]) if isinstance(a[1], Trou) else a[1]
        return "(%s %s %s)" % (rendre(a[2]), op, rendre(a[3]))
    return "(%s %s)" % (a[1], " ".join(rendre(x) for x in a[2:]))

# ------------------------------------------------- 5. schemas de reference

SCHEMAS = {
    "pli":       {"variations": 2, "rec_dans_op": True,  "nom_reel": "foldr"},
    "transform": {"variations": 1, "constructeur": ":",  "nom_reel": "map"},
    "selection": {"variations": 1, "gardes": True,       "nom_reel": "filter"},
}

def classer(bases, corps_normalises, nb_trous):
    """Decide de quel schema releve un groupe de definitions alignees."""
    if all(rendre(c).startswith("((") is False for c in corps_normalises):
        pass
    if len(set(bases)) > 1 and nb_trous >= 2:
        return "pli"
    if len(set(bases)) == 1 and nb_trous == 1:
        return "transform"
    return "indetermine"

# ------------------------------------------------- 6. mise en oeuvre

def aligner(definitions):
    """definitions : liste de (nom, source). Renvoie l'alignement et la generalisation."""
    lignes, arbres, bases = [], [], []
    for nom, src in definitions:
        eqs = lire(src)
        base = [c for (n, m, c) in eqs if m.strip() == "[]"][0]
        rec = [(m, c) for (n, m, c) in eqs if m.strip() != "[]"][0]
        arbre = normaliser(nom, rec[0], rec[1])
        lignes.append((nom, base, rec[1]))
        arbres.append(arbre)
        bases.append(base)

    Trou.n = 0
    subst = {}
    g = arbres[0]
    for a in arbres[1:]:
        g = antiunifier(g, a, subst)
    return lignes, bases, g, subst


def rapport(titre, corpus, exercices):
    lignes, bases, g, subst = aligner(corpus)
    print("=" * 74)
    print(titre)
    print("Corpus de l'apprenant : %d definitions produites aux exercices %s\n" % (len(corpus), exercices))
    print("%-12s %-8s %s" % ("fonction", "cas []", "cas recursif (normalise)"))
    for (nom, base, rec) in lignes:
        print("%-12s %-8s %s" % (nom, base, rec))
    print("\nCe qui reste apres alignement :")
    print("   cas de base   : %s" % ("?0   valeurs observees " + str(sorted(set(bases)))
                                     if len(set(bases)) > 1 else bases[0] + "   (identique partout)"))
    print("   cas recursif  : " + rendre(g))
    for t, (genre, vals) in subst.items():
        print("   %s  (%s)  valeurs observees %s" % (t, genre, vals))
    nb = len(subst) + (1 if len(set(bases)) > 1 else 0)
    print("\nPoints de variation : %d" % nb)
    tete = rendre(g)
    if isinstance(g, tuple) and g[0] == "op" and g[1] == ":" and len(set(bases)) == 1:
        verdict = "transformation  ->  map"
    elif isinstance(g, tuple) and g[0] == "op" and isinstance(g[1], Trou) and "REC" in tete:
        verdict = "pli  ->  foldr"
    else:
        verdict = "indetermine"
    print("Schema reconnu     : %s" % verdict)
    print("Declenchement      : %s\n" % ("remontee proposee au groupe" if len(corpus) >= 3 else "corpus insuffisant"))

if __name__ == "__main__":
    corpus = [
        ("somme", "somme [] = 0\nsomme (x:xs) = x + somme xs"),
        ("produit", "produit [] = 1\nproduit (x:xs) = x * produit xs"),
        ("longueur", "longueur [] = 0\nlongueur (x:xs) = 1 + longueur xs"),
        ("concatener", "concatener [] = []\nconcatener (xs:xss) = xs ++ concatener xss"),
    ]
    rapport("FAMILLE 2 — quatre definitions du chapitre 3", corpus, "3.4, 3.5, 3.7 et 3.9")

    corpus2 = [
        ("doubler", "doubler [] = []\ndoubler (x:xs) = 2 * x : doubler xs"),
        ("carres", "carres [] = []\ncarres (x:xs) = x * x : carres xs"),
        ("initiales", "initiales [] = []\ninitiales (n:ns) = head n : initiales ns"),
    ]
    Trou.n = 0
    rapport("FAMILLE 1 — trois definitions du chapitre 4", corpus2, "4.1, 4.2 et 4.3")
