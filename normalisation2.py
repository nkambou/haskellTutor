"""Normalisation v2 : au-dela des listes.

La version 1 ne savait traiter qu'une recursion sur une liste, avec les patterns
[] et (x:xs). Elle laissait six familles du referentiel non validables. Cette
version generalise sur trois axes.

1. Constructeurs quelconques. Les patterns sont lus tels qu'ils sont ecrits, le
   constructeur est identifie, ses champs sont numerotes, et un champ sur lequel
   porte un appel recursif devient RECi. Feuille / Noeud, Nothing / Just,
   [] / (x:xs) sont traites par le meme code.

2. Definitions sans motif. f x = G (H x) n'a pas de constructeur ; l'argument
   devient ARG et le corps est normalise tel quel.

3. Signatures. Certaines familles s'alignent sur les types et non sur les corps
   (une meme operation sur plusieurs types, une meme enveloppe a gauche et a
   droite). Le meme anti-unificateur y sert, applique a l'arbre du type.

Limite connue et non levee : l'anti-unification reste du premier ordre. Elle ne
peut pas reconnaitre que [a] et Arbre a sont la meme enveloppe appliquee a deux
types differents. La famille F-fmap est donc validee a deux points de variation
et non a un ; l'invariant « le meme trou a gauche et a droite » reste a
verifier a la main.
"""

import re
import remontee as R

# ------------------------------------------------------------ 1. decoupage

def decouper(source):
    """Recolle gardes et where sur leur equation, supprime signatures et commentaires."""
    brut = []
    for ligne in source.splitlines():
        ligne = ligne.split("--")[0].rstrip()
        if not ligne.strip() or re.match(r"^\s*\w[\w']*\s*::", ligne):
            continue
        brut.append(ligne)
    eqs, courante = [], None
    for ligne in brut:
        if ligne[:1] in (" ", "\t") and courante is not None:
            courante += " " + ligne.strip()
        else:
            if courante is not None:
                eqs.append(courante)
            courante = ligne.strip()
    if courante is not None:
        eqs.append(courante)
    return eqs

COUPE = re.compile(r"(?<![=<>/!])=(?!=)")

def separer(nom, eq):
    """Renvoie (motif brut, corps) pour une equation de la fonction nom."""
    m = COUPE.search(eq)
    if not m:
        return None
    gauche, corps = eq[:m.start()].strip(), eq[m.end():].strip()
    if not gauche.startswith(nom):
        return None
    return gauche[len(nom):].strip(), corps

# ------------------------------------------------------------ 2. patterns

MOTIF_CONS = re.compile(r"^\(\s*(\w[\w']*)\s*:\s*(\w[\w']*)\s*\)$")
MOTIF_CTOR = re.compile(r"^\(?\s*([A-Z]\w*)((?:\s+[\w'_]+)*)\s*\)?$")

def lire_motif(motif):
    """Renvoie (constructeur, [champs]) ou (None, [variables]) si le motif n'en est pas un."""
    motif = motif.strip()
    if motif == "[]":
        return "NIL", []
    m = MOTIF_CONS.match(motif)
    if m:
        return "CONS", [m.group(1), m.group(2)]
    m = MOTIF_CTOR.match(motif)
    if m and motif[:1].isupper() or (m and motif.startswith("(")):
        champs = m.group(2).split() if m.group(2) else []
        return m.group(1), champs
    return None, motif.split()

# ------------------------------------------------------------ 3. corps

LAMBDA = re.compile(r"\\\s*[\w'_ ]+->")

def normaliser_corps(nom, corps, champs):
    """Remplace l'appel recursif par RECi, les champs par Ci, les lambdas par LAM."""
    e = " " + corps.strip() + " "
    e = LAMBDA.sub(" LAM ", e)
    e = re.sub(r"\bif\b(.*?)\bthen\b(.*?)\belse\b(.*)", r"COND (\1) (\2) (\3)", e)
    e = re.sub(r"\bcase\b(.*?)\bof\b(.*)", r"CASE (\1) (\2)", e)
    for i, champ in enumerate(champs, start=1):
        e = re.sub(r"\b%s\s+%s\b" % (re.escape(nom), re.escape(champ)), " REC%d " % i, e)
    for i, champ in enumerate(champs, start=1):
        e = re.sub(r"\b%s\b" % re.escape(champ), " C%d " % i, e)
    e = re.sub(r"\s+", " ", e)
    return commuter(serrer(e))


def commuter(e, operateurs=("+", "*")):
    """Commutativite limitee : x + f xs et f xs + x decrivent le meme pas. Appliquee
    a ++ ou a : elle produirait de fausses egalites, elle est donc restreinte."""
    for op in operateurs:
        m = re.match(r"^REC(\d*) \%s (.+)$" % op, e)
        if m:
            return "%s %s REC%s" % (m.group(2), op, m.group(1))
    return e

def serrer(e):
    e = re.sub(r"\s*,\s*", ", ", e)
    e = re.sub(r"\(\s+", "(", e)
    e = re.sub(r"\s+\)", ")", e)
    return re.sub(r"\s+", " ", e).strip()

# ------------------------------------------------------------ 4. analyse

def separer_gardes(nom, eq):
    """Une equation a gardes devient (motif, COND (cond) (alors) (sinon))."""
    if "|" not in eq:
        return None
    tete, reste = eq.split("|", 1)
    if not tete.strip().startswith(nom):
        return None
    motif = tete.strip()[len(nom):].strip()
    branches = []
    for morceau in reste.split("|"):
        m = COUPE.search(morceau)
        if not m:
            continue
        cond = morceau[:m.start()].strip()
        branches.append((None if cond == "otherwise" else cond, morceau[m.end():].strip()))
    if not branches:
        return None
    cond, alors = branches[0]
    sinon = branches[1][1] if len(branches) > 1 else "NOTHING"
    cond, alors, sinon = orienter(nom, cond, alors, sinon)
    return motif, "COND (%s) (%s) (%s)" % (cond, alors, sinon)


def orienter(nom, cond, alors, sinon):
    """Une garde et sa negation avec les branches echangees decrivent la meme selection.
    On oriente toujours dans le meme sens : la branche qui conserve l'element vient
    en premier. C'est une variante d'ecriture, pas une difference de sens."""
    def seulement_recursif(e):
        reste = re.sub(r"\b%s\b\s+\w+" % re.escape(nom), "", e).strip()
        return reste == "" and nom in e
    if seulement_recursif(alors) and not seulement_recursif(sinon):
        return "NOT (%s)" % cond, sinon, alors
    return cond, alors, sinon


def analyser(nom, source):
    """Renvoie {'forme': ..., 'equations': {constructeur: corps normalise}, 'base': ...}."""
    equations, sans_motif = {}, []
    for eq in decouper(source):
        sep = separer_gardes(nom, eq) or separer(nom, eq)
        if not sep:
            continue
        motif, corps = sep
        ctor, champs = lire_motif(motif)
        if ctor is None:
            champs = champs or ["ARG"]
            sans_motif.append(normaliser_corps(nom, corps, champs))
        else:
            equations[ctor] = normaliser_corps(nom, corps, champs)

    if equations:
        recursifs = [c for c, e in equations.items() if "REC" in e]
        vides = [c for c in equations if c in ("NIL", "Nothing", "Feuille")
                 or not equations[c].count("C")]
        bases = recursifs and [c for c in equations if c not in recursifs] or vides
        pas = (equations[recursifs[0]] if recursifs
               else next((e for c, e in equations.items() if c not in bases), None))
        return {"forme": "constructors",
                "equations": equations,
                "base": equations[bases[0]] if bases else None,
                "pas": pas}
    if sans_motif:
        return {"forme": "no-pattern", "equations": {}, "base": None, "pas": sans_motif[0]}
    return {"forme": "unanalysable", "equations": {}, "base": None, "pas": None}

# ------------------------------------------------------------ 5. signatures

ARROW = re.compile(r"->")

if "ARROW" not in R.INFIXES:
    R.INFIXES.append("ARROW")

def arbre_de_signature(sig):
    """Analyse un type en arbre, en traitant [a] comme (LIST a) et -> comme un infixe."""
    s = sig.split("=>")[-1]
    s = re.sub(r"\[\s*(\w+)\s*\]", r"(LIST \1)", s)
    s = s.replace("->", " ARROW ")
    return R.parse(R.tokens(s))

# ------------------------------------------------------------ 6. alignement

def compter_trous(a, vus=None):
    """Compte les trous presents dans l'arbre generalise, et non ceux qui ont ete
    ouverts puis absorbes en cours d'alignement."""
    if vus is None:
        vus = set()
    if isinstance(a, R.Trou):
        vus.add(a.i)
    elif isinstance(a, tuple):
        for x in a[1:]:
            compter_trous(x, vus)
    return vus


def aligner_corps(corpus):
    """corpus : [(nom, source)]. Aligne les cas de base et les cas recursifs."""
    formes, bases = [], []
    for nom, src in corpus:
        a = analyser(nom, src)
        if a["pas"] is None:
            continue
        formes.append(R.parse(R.tokens(a["pas"])))
        bases.append(a["base"])
    if len(formes) < 2:
        return 0, None, 0
    R.Trou.n = 0
    subst = {}
    g = formes[0]
    for f in formes[1:]:
        g = R.antiunifier(g, f, subst)
    varie_base = len({b for b in bases if b is not None}) > 1
    fins = len(compter_trous(g))
    blocs = (1 if varie_base else 0) + (1 if fins else 0)
    return fins + (1 if varie_base else 0), R.rendre(g), blocs

def aligner_signatures(signatures):
    arbres = [arbre_de_signature(s) for s in signatures]
    if len(arbres) < 2:
        return 0, None
    R.Trou.n = 0
    subst = {}
    g = arbres[0]
    for a in arbres[1:]:
        g = R.antiunifier(g, a, subst)
    return len(compter_trous(g)), R.rendre(g)


def verifier_invariant_final(corpus, marqueur="C1"):
    """Pour la famille de l'application partielle : le dernier argument doit apparaitre
    une seule fois, en derniere position, dans chaque solution de reference."""
    details = []
    for nom, src in corpus:
        a = analyser(nom, src)
        corps = a["pas"] or ""
        occurrences = len(re.findall(r"\b%s\b" % marqueur, corps))
        final = corps.rstrip().endswith(marqueur)
        details.append((nom, occurrences, final))
    conforme = all(o == 1 and f for _, o, f in details)
    return conforme, details


if __name__ == "__main__":
    arbre = [
        ("sommeA", "sommeA Feuille = 0\nsommeA (Noeud g x d) = sommeA g + x + sommeA d"),
        ("tailleA", "tailleA Feuille = 0\ntailleA (Noeud g x d) = tailleA g + 1 + tailleA d"),
        ("listerA", "listerA Feuille = []\nlisterA (Noeud g x d) = listerA g ++ [x] ++ listerA d"),
        ("hauteurA", "hauteurA Feuille = 0\nhauteurA (Noeud g x d) = 1 + max (hauteurA g) (hauteurA d)"),
    ]
    echec = [
        ("premierS", "premierS [] = Nothing\npremierS (x:xs) = Just x"),
        ("maximumS", "maximumS [] = Nothing\nmaximumS (x:xs) = Just (foldr1 max (x:xs))"),
        ("moyenneS", "moyenneS [] = Nothing\nmoyenneS (x:xs) = Just (moy (x:xs))"),
    ]
    compo = [
        ("nbMots", "nbMots s = length (words s)"),
        ("majInitiale", "majInitiale s = toUpper (head s)"),
        ("sommeDesLongueurs", "sommeDesLongueurs xss = sum (mapl xss)"),
        ("nonVide", "nonVide s = not (null s)"),
    ]
    partielle = [
        ("doublerTous", "doublerTous xs = map LAM xs"),
        ("garderPairs", "garderPairs xs = filter even xs"),
        ("totaliser", "totaliser xs = foldr plus zero xs"),
        ("initiales", "initiales ns = map head ns"),
    ]
    print("%-16s %-6s %-6s %s" % ("famille", "fins", "blocs", "forme generale"))
    print("-" * 74)
    for titre, corpus in [("F-tree", arbre), ("F-failure", echec),
                          ("F-compose", compo), ("F-partial", partielle)]:
        n, f, blocs = aligner_corps(corpus)
        print("%-16s %-6d %-6d %s" % (titre, n, blocs, f))

    for titre, sigs in [
        ("F-instances", ["Forme -> String", "Jour -> String", "Reponse -> String"]),
        ("F-fmap", ["(a -> b) -> [a] -> [b]",
                    "(a -> b) -> Arbre a -> Arbre b",
                    "(a -> b) -> Boite a -> Boite b"])]:
        n, f = aligner_signatures(sigs)
        print("%-16s %-6d %-6s %s" % (titre, n, "-", f))
