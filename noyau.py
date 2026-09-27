"""Noyau executable de HaskellTutor.

Reunit ce qui a ete construit separement : le referentiel, le generateur
d'activites, la normalisation, l'alignement, et la politique de session. Ajoute
ce qui manquait pour que le systeme tourne : la compilation reelle des
soumissions par GHC, la persistance de l'etat, et le journal des soumissions au
format attendu par releves.py.

Aucune dependance hors bibliotheque standard. GHC doit etre installe.
"""

import json, os, sys, subprocess, tempfile, datetime, hashlib, importlib

# Le repertoire de ce fichier est ajoute au chemin de recherche, de sorte que le
# serveur peut etre lance depuis n'importe quel repertoire courant.
ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)

# Le fournisseur de langage et le referentiel sont a cote de ce fichier.
TUTEUR = ICI

import normalisation2 as N2
import remontee as R

# Le fournisseur de langage. Une seule variable d'environnement change de tuteur.
_nom_langue = os.environ.get("TUTOR_LANGUAGE", "language_haskell")
try:
    LANGUE = importlib.import_module(_nom_langue)
except ModuleNotFoundError:
    dispo = sorted(f[:-3] for f in os.listdir(ICI) if f.startswith("language_")
                   and f.endswith(".py"))
    raise SystemExit(
        "\nLe fournisseur de langage \"%s\" est introuvable.\n"
        "  repertoire du tuteur : %s\n"
        "  fournisseurs la : %s\n\n"
        "Le fichier %s.py doit se trouver a cote de noyau.py. Si vous avez\n"
        "telecharge les fichiers un a un, verifiez qu'aucun ne manque : le tuteur\n"
        "a besoin de serveur.py, noyau.py, textes.py, remontee.py,\n"
        "normalisation.py, normalisation2.py, referentiel.json,\n"
        "etudiant.html, enseignant.html et language_haskell.py.\n"
        % (_nom_langue, ICI, ", ".join(dispo) or "aucun", _nom_langue))

VERSION = "3.8"

ICI = os.path.dirname(os.path.abspath(__file__))
REFERENTIEL = os.path.join(ICI, "referentiel.json")
# Un fichier d'etat et un journal par langage, pour que deux tuteurs puissent
# tourner cote a cote depuis le meme dossier. Haskell garde les noms d'origine.
_SUFFIXE = "" if LANGUE.name == "haskell" else "_" + LANGUE.name
ETAT = os.path.join(ICI, "etat%s.json" % _SUFFIXE)
JOURNAL = os.path.join(ICI, "journal%s.jsonl" % _SUFFIXE)

# ============================================================ activites

# Chaque ancrage : identifiant, enonce, signature, amorce, tests (expression, attendu).
ACTIVITES = {
 "F-map": [
  ("doubler", "Multipliez chaque element par deux.", "doubler :: [Int] -> [Int]",
   "doubler :: [Int] -> [Int]\ndoubler = undefined\n",
   [("doubler [1,2,3]", "[2,4,6]"), ("doubler []", "[]")]),
  ("initiales", "Donnez la premiere lettre de chaque chaine.", "initiales :: [String] -> [Char]",
   "initiales :: [String] -> [Char]\ninitiales = undefined\n",
   [("initiales [\"Ada\",\"Curie\"]", "\"AC\""), ("initiales []", "\"\"")]),
  ("notes", "Un releve nom-note. Ne gardez que les notes.",
   "notes :: [(String,Int)] -> [Int]",
   "notes :: [(String,Int)] -> [Int]\nnotes = undefined\n",
   [("notes [(\"a\",3),(\"b\",5)]", "[3,5]"), ("notes []", "[]")]),
  ("carres", "Remplacez chaque element par son carre.", "carres :: [Int] -> [Int]",
   "carres :: [Int] -> [Int]\ncarres = undefined\n",
   [("carres [1,2,3]", "[1,4,9]"), ("carres []", "[]")]),
 ],
 "F-fold": [
  ("somme", "Le total des releves de temperature.", "somme :: [Int] -> Int",
   "somme :: [Int] -> Int\nsomme = undefined\n",
   [("somme [3,4,5,6]", "18"), ("somme []", "0")]),
  ("produit", "Un facteur d'echelle par etage : donnez le facteur global.",
   "produit :: [Int] -> Int",
   "produit :: [Int] -> Int\nproduit = undefined\n",
   [("produit [1,2,3,4]", "24"), ("produit []", "1")]),
  ("longueur", "Un inventaire dont les elements importent peu : comptez-les.",
   "longueur :: [a] -> Int",
   "longueur :: [a] -> Int\nlongueur = undefined\n",
   [("longueur [1,2,3::Int]", "3"), ("longueur ([]::[Int])", "0"),
    ("longueur \"abcde\"", "5")]),
  ("aplatir", "Des paragraphes decoupes en listes de mots : remettez-les bout a bout.",
   "aplatir :: [[String]] -> [String]",
   "aplatir :: [[String]] -> [String]\naplatir = undefined\n",
   [("aplatir [[\"le\",\"chat\"],[\"dort\"]]", "[\"le\",\"chat\",\"dort\"]"),
    ("aplatir []", "[]")]),
  ("toutVrai", "Les resultats de plusieurs verifications : toutes ont-elles reussi ?",
   "toutVrai :: [Bool] -> Bool",
   "toutVrai :: [Bool] -> Bool\ntoutVrai = undefined\n",
   [("toutVrai [True,True]", "True"), ("toutVrai [True,False]", "False"),
    ("toutVrai []", "True")]),
 ],
 "F-filter": [
  ("pairs", "Des numeros de place : ne gardez que les pairs.", "pairs :: [Int] -> [Int]",
   "pairs :: [Int] -> [Int]\npairs = undefined\n",
   [("pairs [1,2,3,4]", "[2,4]"), ("pairs []", "[]")]),
  ("nonVides", "Des champs de formulaire : ecartez ceux laisses vides.",
   "nonVides :: [String] -> [String]",
   "nonVides :: [String] -> [String]\nnonVides = undefined\n",
   [("nonVides [\"a\",\"\",\"b\"]", "[\"a\",\"b\"]"), ("nonVides []", "[]")]),
  ("admis", "Un relevé nom-note : ne gardez que les reçus, ceux qui ont au moins 60.",
   "admis :: [(String,Int)] -> [(String,Int)]",
   "admis :: [(String,Int)] -> [(String,Int)]\nadmis = undefined\n",
   [('admis [("Ada",72),("Bob",55),("Cy",60)]', '[("Ada",72),("Cy",60)]'), ("admis []", "[]")]),
  ("voyelles", "Un texte : ne gardez que les voyelles.", "voyelles :: String -> String",
   "voyelles :: String -> String\nvoyelles = undefined\n",
   [("voyelles \"haskell\"", "\"ae\""), ("voyelles \"\"", "\"\"")]),
 ],
}

# Items de reemploi : un probleme ou la recursion explicite reste possible, et ou
# l'on verifie que l'apprenant emploie le schema sans y etre invite.
REEMPLOIS = {
 "F-map": [
  ("majuscules", "Mettez chaque chaine en majuscules. import Data.Char (toUpper) autorise.",
   "majuscules :: [String] -> [String]",
   "import Data.Char (toUpper)\n\nmajuscules :: [String] -> [String]\nmajuscules = undefined\n",
   [("majuscules [\"ada\",\"curie\"]", "[\"ADA\",\"CURIE\"]"), ("majuscules []", "[]")]),
  ("negatifs", "Changez le signe de chaque element.", "negatifs :: [Int] -> [Int]",
   "negatifs :: [Int] -> [Int]\nnegatifs = undefined\n",
   [("negatifs [1,-2,3]", "[-1,2,-3]"), ("negatifs []", "[]")]),
 ],
 "F-filter": [
  ("courts", "Ne gardez que les mots de moins de quatre lettres.",
   "courts :: [String] -> [String]",
   "courts :: [String] -> [String]\ncourts = undefined\n",
   [("courts [\"le\",\"chat\",\"a\"]", "[\"le\",\"a\"]"), ("courts []", "[]")]),
  ("positifs", "Ne gardez que les nombres strictement positifs.",
   "positifs :: [Int] -> [Int]",
   "positifs :: [Int] -> [Int]\npositifs = undefined\n",
   [("positifs [-2,3,0,5]", "[3,5]"), ("positifs []", "[]")]),
 ],
 "F-fold": [
  ("maximumL", "Le plus grand element d'une liste non vide.", "maximumL :: [Int] -> Int",
   "maximumL :: [Int] -> Int\nmaximumL = undefined\n",
   [("maximumL [3,9,2]", "9"), ("maximumL [7]", "7")]),
  ("concatMots", "Recollez des mots en une seule chaine.", "concatMots :: [String] -> String",
   "concatMots :: [String] -> String\nconcatMots = undefined\n",
   [("concatMots [\"le\",\"chat\"]", "\"lechat\""), ("concatMots []", "\"\"")]),
 ],
}

FORMES_ATTENDUES = {
 "F-map": ("constructors",),
 "F-fold": ("constructors",),
 "F-filter": ("constructors",),
}

# ============================================================ aide

# Trois niveaux, jamais davantage, et jamais la solution. Le premier reformule ce
# que le compilateur a dit ; le deuxieme oriente vers la forme attendue ; le
# troisieme montre la charpente sans la remplir. Aucun niveau ne nomme le schema :
# le nom est le resultat de la remontee, pas son amorce.

AIDES_ERREUR = {
 "missing-base-case": [
   "Le compilateur signale un motif non couvert. Quelle forme d'entree votre "
   "definition ne traite-t-elle pas ?",
   "Une liste est soit vide, soit un element suivi d'une liste. Vous avez ecrit "
   "une equation pour la seconde forme seulement.",
   "Il vous manque une equation dont le motif est [] . Sa valeur est celle qui ne "
   "change rien a l'operation que vous employez."],
 "incompatible-types": [
   "Lisez le message de bas en haut : la derniere ligne dit ou, l'avant-derniere "
   "dans quel argument de quelle fonction.",
   "Comparez le type attendu et le type trouve, puis demandez a GHCi le type de la "
   "fonction citee, avec :t .",
   "Le desaccord porte sur l'argument que le message nomme. Verifiez ce que votre "
   "expression rend a cet endroit precis."],
 "int-double-mix": [
   "Une division exige des nombres fractionnaires des deux cotes.",
   "length et les comptages rendent un Int. Une division sur un Int n'est pas la "
   "meme operation.",
   "Enveloppez chaque operande entier dans fromIntegral avant de diviser."],
 "wrong-result": [
   "Votre code compile : l'erreur n'est pas de forme mais de calcul.",
   "Comparez le resultat obtenu et le resultat attendu sur le premier test qui "
   "echoue, et demandez-vous quel cas produit cet ecart.",
   "Deroulez votre definition a la main sur l'entree du test qui echoue, en "
   "commencant par le cas de base."],
 "unknown-name": [
   "Un nom employe n'est pas defini.",
   "Verifiez l'orthographe et la casse : un nom de fonction commence par une "
   "minuscule.",
   "Si la fonction vient d'un module, il faut l'importer en tete de fichier."],
 "syntax": [
   "Le fichier ne s'analyse pas : le probleme est en amont du sens.",
   "Verifiez l'indentation et les parentheses de la ligne signalee.",
   "Une equation tient sur une ligne, ou ses suites sont indentees davantage que "
   "le nom de la fonction."],
}

AIDES_FAMILLE = {
 "F-map": [
   "Cette fonction produit une liste de meme longueur que celle qu'elle recoit.",
   "Traitez le premier element, puis laissez la recursion s'occuper du reste.",
   "Charpente : f [] = ... et f (x:xs) = ... x ... : f xs"],
 "F-filter": [
   "Cette fonction produit une liste plus courte, sans modifier les elements gardes.",
   "Deux conduites sont possibles pour un element : le garder ou l'ignorer. Une "
   "definition par gardes permet de choisir.",
   "Charpente : f [] = [] puis f (x:xs) avec deux gardes, dont l'une conserve x et "
   "l'autre non ; l'appel recursif est le meme dans les deux."],
 "F-fold": [
   "Cette fonction ne produit pas une liste : elle produit une seule valeur.",
   "Deux choses sont a decider : ce que vaut le resultat sur la liste vide, et "
   "comment combiner le premier element avec le resultat du reste.",
   "Charpente : f [] = Z et f (x:xs) = ... x ... (f xs). Pour Z, cherchez la valeur "
   "qui ne change rien a l'operation que vous employez."],
}

AIDES_REMONTEE = [
  "Ecrivez vos definitions les unes sous les autres et rayez tout ce qui est "
  "identique dans toutes. Combien de choses restent ?",
  "Le tuteur a fait l'alignement pour vous : les colonnes ci-dessus montrent le cas "
  "de base et le cas recursif de chacune. Les trous notes ?n sont ce qui varie.",
  "Ecrivez une definition qui recoit en arguments ce qui varie, et qui garde tel "
  "quel ce qui ne varie pas. Donnez-lui une signature avant d'ecrire son corps.",
]

NIVEAUX_MAX = 3

# Lecture immediate du message du compilateur. Elle n'est pas un indice et ne compte
# pas dans l'etayage : elle dit seulement, en francais, ce que GHC vient de signaler,
# pour que l'apprenant ne reste pas seul devant un message brut.
LECTURES = {
 "missing-base-case": "Le compilateur signale qu'une forme d'entree n'est pas traitee.",
 "incompatible-types": "Le compilateur a trouve un type la ou il en attendait un autre.",
 "int-double-mix": "Un entier et un nombre fractionnaire se rencontrent dans la meme "
                       "operation.",
 "unknown-name": "Un nom employe dans votre code n'est defini nulle part.",
 "syntax": "Le fichier ne s'analyse pas : le probleme est en amont du sens.",
 "wrong-result": "Votre code compile. L'erreur n'est pas de forme mais de calcul.",
 "unclassified": "Le compilateur a refuse votre definition.",
}

ENCOURAGEMENTS = [
 "C'est juste.", "Correct.", "Ca passe.", "Bien vu.", "Votre definition tient.",
 "Compile et passe les tests.",
]


def lecture(categorie):
    return LECTURES.get(categorie, LECTURES["unclassified"])


# Ce que le tuteur dit quand la solution est correcte mais ecrite autrement que ce
# que la comparaison exige. Il reconnait la reussite, explique ce qu'il lui faut et
# pourquoi, sans jamais nommer le schema vise.

RAISONS = {
 "no-pattern": "elle ne distingue pas les cas : on n'y voit ni ce que vaut le resultat "
               "sur une liste vide, ni ce que vous faites du premier element",
 "accumulateur": "elle applique l'operation avant l'appel recursif et non apres, "
                 "ce qui en fait une autre facon de parcourir",
 "sans recursion explicite": "elle s'appuie sur une fonction toute faite, donc elle "
                             "ne montre pas ce que vous auriez ecrit vous-meme",
 "aucun cas recursif reconnu": "elle ne se decompose pas en un cas de base et un cas "
                               "qui se rappelle",
}


def raison(motif):
    for cle, texte in RAISONS.items():
        if cle in motif:
            return texte
    return "elle ne se compare pas terme a terme avec les autres"


# ------------------------------------------------------------ verification
# Deux questions portant sur la solution que l'apprenant vient de soumettre. Elles
# sont engendrees a partir de sa forme normalisee, donc elles n'ont de reponse que
# pour qui a ecrit ce code. Ce n'est pas un dispositif d'accusation : repondre est
# une auto-explication, dont l'effet d'apprentissage est etabli independamment de
# la question de savoir d'ou vient le code.

def questions_sur(nom, code, autres_bases=()):
    """Engendre au plus deux questions a choix multiple a partir de la soumission,
    formulees dans les termes memes que l'apprenant a ecrits."""
    import re
    a = LANGUE.analyse(nom, code)
    qs = []
    base = a.get("base")
    if base:
        distracteurs = [b for b in ("0", "1", "[]", "True", "-1") if b != base][:3]
        qs.append({"id": "base",
                   "question": "Que rend votre fonction sur l'entree vide ?",
                   "options": [base] + distracteurs,
                   "reponse": base,
                   "suite": "Cette valeur est celle qui ne change rien a l'operation que "
                            "vous employez : c'est ainsi qu'on la trouve."})
    # l'appel recursif, tel qu'il figure dans le code de l'apprenant
    appels = re.findall(r"\b%s\s+([A-Za-z_][\w']*)" % re.escape(nom), code)
    equations = [l for l in code.splitlines() if l.strip().startswith(nom)]
    tete = None
    for l in equations:
        m = re.search(r"\(\s*([A-Za-z_][\w']*)\s*:", l)
        if m:
            tete = m.group(1)
            break
    if appels:
        vrai = "%s %s" % (nom, appels[-1])
        faux = [x for x in [tete, base, "%s %s" % (nom, tete or "x")] if x and x != vrai][:2]
        qs.append({"id": "pas",
                   "question": "Dans votre cas recursif, quelle expression designe le "
                               "resultat deja calcule sur le reste de l'entree ?",
                   "options": [vrai] + faux,
                   "reponse": vrai,
                   "suite": "C'est l'appel recursif : vous supposez que la fonction sait "
                            "deja repondre sur le reste, et vous vous contentez de "
                            "combiner ce resultat avec le premier element."})
    return qs[:2]


def signaux_de_doute(secondes, echecs, aides, code):
    """Indices, jamais une preuve. Le seuil est reglable par l'enseignant."""
    s = []
    if secondes is not None and secondes < 25:
        s.append("soumission tres rapide apres l'ouverture de l'activite")
    if echecs == 0 and aides == 0 and secondes is not None and secondes < 60:
        s.append("aucune tentative intermediaire, aucun etayage")
    if len(code.splitlines()) > 2 and "  " in code and code.count("\n\n") > 1:
        s.append("mise en forme inhabituelle pour une saisie au fil de l'ecriture")
    return s


def commentaire_hors_forme(motif, politique, n_resolutions):
    """Reconnaitre la reussite, expliquer le besoin, dire la suite."""
    tete = ("C'est juste, et votre solution fonctionne. C'est la %de fois que vous "
            "resolvez un probleme autrement que ce que la comparaison attend. "
            % n_resolutions) if n_resolutions > 1 else \
           "C'est juste, et votre solution fonctionne. "
    besoin = ("Pour la suite, le tuteur a besoin de solutions ecrites de la meme "
              "maniere, parce qu'il va vous les montrer cote a cote : c'est en les "
              "comparant que vous trouverez ce qu'elles ont en commun. La votre est "
              "correcte mais " + raison(motif) + ".")
    suites = {
     "explain_and_rewrite":
        " Reecrivez la meme fonction en distinguant explicitement le cas de la liste "
        "vide et le cas ou elle a au moins un element. Votre version actuelle est "
        "conservee : vous la retrouverez dans vos solutions.",
     "explain_and_continue":
        " Le tuteur passe a un autre probleme de meme nature. Ecrivez-le en distinguant "
        "le cas de la liste vide et le cas ou elle a au moins un element : c'est cette "
        "forme-la qu'il faut pour la suite.",
     "confront":
        " Vous savez visiblement deja obtenir ce resultat sans le detailler. Ecrivez "
        "maintenant la meme fonction en la detaillant : vous aurez les deux versions "
        "sous les yeux, et la comparaison vaudra la peine.",
    }
    return tete + besoin + suites.get(politique, suites["explain_and_continue"])


# Explication epistemique, fournie a la demande : pourquoi cette forme et pas une
# autre. Elle porte sur la nature de ce qui est en train d'etre construit, non sur
# la correction de la soumission. Elle ne nomme toujours pas le schema vise.

POURQUOI = {
 "F-map":
   ("Vous savez deja obtenir ce resultat. Ce que le cours cherche a construire n'est "
    "pas la reponse, c'est ce que plusieurs reponses ont en commun.\n\n"
    "Une liste en comprehension, ou un appel a une fonction toute faite, donne le bon "
    "resultat en cachant la marche a suivre. Ecrite en distinguant les cas, la meme "
    "fonction montre deux choses : ce que vaut le resultat quand il n'y a plus rien, "
    "et ce que vous faites du premier element. Ce sont ces deux choses que le tuteur "
    "alignera d'une solution a l'autre.\n\n"
    "Autrement dit, la contrainte de forme n'est pas une exigence de style : c'est ce "
    "qui rend la comparaison possible. Sans elle, vous auriez quatre solutions justes "
    "et rien a en tirer."),
 "F-filter":
   ("Votre solution est juste. Mais ce que le cours construit ici est la comparaison "
    "entre plusieurs fonctions qui gardent ou ecartent des elements.\n\n"
    "Ecrite en distinguant le cas vide et le cas ou il reste un element, avec une "
    "decision explicite sur cet element, votre fonction laisse voir ou se trouve la "
    "condition. Quatre fonctions ecrites ainsi se superposent, et ce qui depasse est "
    "exactement ce qui les distingue.\n\n"
    "Une comprehension donne le meme resultat et masque cet endroit precis."),
 "F-fold":
   ("Votre solution fonctionne. Ce que le cours cherche ici est ce qui reste commun "
    "a plusieurs facons de reduire une liste a une seule valeur.\n\n"
    "Pour que la comparaison soit possible, il faut voir deux choses dans chaque "
    "solution : ce que vaut le resultat sur la liste vide, et comment le premier "
    "element se combine au resultat du reste. Une fonction du prelude, ou une boucle "
    "deguisee, donne le total sans montrer ni l'un ni l'autre.\n\n"
    "La contrainte porte donc sur ce que la solution rend visible, pas sur sa qualite."),
}

POURQUOI_DEFAUT = (
 "Votre solution est juste. La forme demandee n'est pas une question de style : le "
 "tuteur va vous montrer plusieurs de vos solutions cote a cote, et seules des "
 "solutions ecrites de la meme maniere peuvent se comparer terme a terme. Ce que vous "
 "avez a trouver est ce qu'elles ont en commun ; il faut donc qu'elles aient une forme "
 "commune ou chercher.")


def pourquoi(famille):
    return POURQUOI.get(famille, POURQUOI_DEFAUT)


def commentaire_reussite(n, minimum, points, attendu, stable, admise, motif=""):
    """Ce que le tuteur dit apres une soumission reussie. Il commente ce que la
    soumission apporte au corpus, sans jamais nommer le schema vise."""
    import random
    tete = random.choice(ENCOURAGEMENTS)
    if not admise:
        return (tete + " Elle est correcte, mais elle n'entre pas dans la comparaison : "
                + motif + ". Elle est conservee a part.")
    if attendu is None:
        return tete + " Votre solution est enregistree."
    if n < minimum:
        return (tete + " %d solution%s au dossier ; le tuteur en attend au moins %d "
                "avant de vous les montrer ensemble."
                % (n, "s" if n > 1 else "", minimum))
    if points != attendu:
        return (tete + " %d solutions au dossier. En les comparant, le tuteur y voit "
                "%d chose%s qui change%s d'une solution a l'autre. Il en cherche %d : "
                "une solution de plus devrait faire apparaitre la derniere."
                % (n, points, "s" if points > 1 else "", "nt" if points > 1 else "", attendu))
    if not stable:
        return (tete + " %d solutions, et %d chose%s qui varie%s : c'est le compte attendu. "
                "Le tuteur verifie sur une solution de plus que ce compte ne bouge pas."
                % (n, points, "s" if points > 1 else "", "nt" if points > 1 else ""))
    return (tete + " %d solutions, %d point%s de variation, et le compte ne bouge plus. "
            "Vous allez pouvoir les regarder ensemble."
            % (n, points, "s" if points > 1 else ""))


def aide(famille, categorie, niveau, contexte="activite"):
    """Renvoie le texte du niveau demande, ou None si le plafond est atteint."""
    if niveau > NIVEAUX_MAX:
        return None
    if contexte == "abstraction":
        return AIDES_REMONTEE[niveau - 1]
    if niveau == 1 and categorie in AIDES_ERREUR:
        return AIDES_ERREUR[categorie][0]
    echelle = AIDES_FAMILLE.get(famille)
    if categorie in AIDES_ERREUR and niveau <= len(AIDES_ERREUR[categorie]):
        propre = AIDES_ERREUR[categorie][niveau - 1]
    else:
        propre = None
    generale = echelle[niveau - 1] if echelle else None
    if propre and generale:
        return propre + " " + generale
    return propre or generale or "Aucun indice supplementaire a ce niveau."


# Les ancrages propres au langage, s'ils existent.
try:
    _act = importlib.import_module("activities_" + LANGUE.name)
    ACTIVITES = _act.ACTIVITES
    REEMPLOIS = _act.REEMPLOIS
except ModuleNotFoundError:
    pass


# ============================================================ referentiel

def referentiel():
    with open(REFERENTIEL, encoding="utf-8") as f:
        return json.load(f)

def concept(ref, cid):
    for p in ref["paliers"]:
        for c in p["concepts"]:
            if c["id"] == cid:
                return c, p
    return None, None

def concepts_ouverts(ref, etats):
    """Un concept est ouvert quand tous ses prerequis sont acquis."""
    ouverts = []
    for p in ref["paliers"]:
        for c in p["concepts"]:
            if etats.get(c["id"]) == "acquired":
                continue
            if all(etats.get(r) == "acquired" for r in c["prerequis"]):
                ouverts.append(c["id"])
    return ouverts

# ============================================================ GHC

def evaluer(code, tests, delai=25):
    """Ecrit la soumission dans un module de test, l'execute par le fournisseur de
    langage, et compare la sortie aux valeurs attendues."""
    source = LANGUE.test_template(code, [e for e, _ in tests])
    with tempfile.TemporaryDirectory() as d:
        chemin = os.path.join(d, "Soumission" + LANGUE.extension)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(source)
        try:
            p = subprocess.run(LANGUE.command(chemin), capture_output=True, text=True,
                               timeout=delai, cwd=d)
        except subprocess.TimeoutExpired:
            return {"compile": False, "reussite": False, "message": "delai depasse",
                    "obtenu": [], "attendu": [a for _, a in tests]}
        if p.returncode != 0:
            return {"compile": False, "reussite": False, "message": p.stderr.strip(),
                    "obtenu": [], "attendu": [a for _, a in tests]}
        obtenu = [l.strip() for l in p.stdout.strip().splitlines()]
        attendu = [a for _, a in tests]
        ok = len(obtenu) == len(attendu) and all(o == a for o, a in zip(obtenu, attendu))
        return {"compile": True, "reussite": ok, "message": p.stderr.strip(),
                "obtenu": obtenu, "attendu": attendu}


# ============================================================ admission

def admettre(nom, code, famille, verdict):
    if not verdict["reussite"]:
        return {"admis": False, "motif": "tests non reussis", "canon": None}
    a = LANGUE.analyse(nom, code)
    if a["forme"] not in getattr(LANGUE, "ALIGNABLE_FORMS", ("constructors",)):
        return {"admis": False,
                "motif": "correcte mais non alignable (%s)" % a["forme"], "canon": None}
    if a["pas"] is None:
        return {"admis": False, "motif": "aucun cas recursif reconnu", "canon": None}
    if "REC" not in a["pas"]:
        return {"admis": False,
                "motif": "correcte mais sans recursion explicite (schema deja employe)",
                "canon": a["pas"]}
    return {"admis": True, "motif": "", "canon": a["pas"], "base": a["base"]}

def etat_alignement(corpus):
    """Anti-unification des formes canoniques rendues par le fournisseur de langage."""
    formes, bases = [], []
    for nom, code in corpus:
        a = LANGUE.analyse(nom, code)
        if a.get("pas") is None:
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

def compte_alignement(ref, famille, corpus):
    """Le compte que la politique compare a la cible : points fins, ou blocs si la
    famille le declare. Le compte fin depend de l'ordre et de la composition du
    corpus lorsque les parties qui varient ont la meme forme (des predicats qui sont
    tous des comparaisons, par exemple) ; le compte par blocs n'en depend pas."""
    nb, forme, blocs = etat_alignement(corpus)
    v = ref.get("familles", {}).get(famille, {}).get("validation", {})
    return (blocs if v.get("granularite") == "blocs" else nb), forme, blocs

# ============================================================ politique

def decider(ref, ap, cid):
    c, _ = concept(ref, cid)
    r = ref["reglages"]
    corpus = ap["corpus"].get(cid, [])
    n = len(corpus)
    gen = c.get("generalisation")
    attendu = gen["points_de_variation_attendus"] if gen else None
    etat = ap["etats"].get(cid, "instances")

    if etat == "generalised":
        if ap["reemplois"].get(cid, 0) >= r["reemploi_requis"]:
            return "next_tier", "reemplois obtenus"
        return "reuse", "reemploi %d sur %d" % (ap["reemplois"].get(cid, 0),
                                                   r["reemploi_requis"])
    if attendu is None:
        return "instance", "concept sans remontee"
    if n < r["instances_min"]:
        return "instance", "corpus insuffisant (%d sur %d)" % (n, r["instances_min"])

    nb, forme, blocs = compte_alignement(ref, c["famille"],
                                         [(x["nom"], x["code"]) for x in corpus])
    # La stabilite se juge d'une solution admise a la suivante. Une relecture de la
    # vue ne constitue pas une nouvelle observation, et une revision d'une solution
    # existante ne confirme pas le compte. Le corpus est memorise sous forme de
    # listes, pour rester comparable apres la relecture de l'etat JSON.
    empreinte = [[x["nom"], x["code"]] for x in corpus]
    precedent = ap["stabilite"].get(cid)
    if isinstance(precedent, dict) and precedent.get("corpus") == empreinte:
        stable = precedent.get("stable", False)
    else:
        stable = (isinstance(precedent, dict) and precedent.get("corpus") == empreinte[:-1]
                  and precedent.get("points") == nb)
    ap["stabilite"][cid] = {"corpus": empreinte, "points": nb, "stable": stable}
    if nb == attendu and stable:
        return "abstraction", "alignement stable a %d points de variation" % nb
    if n >= r["instances_max"]:
        return "guidance", "plafond de %d instances, alignement a %d" % (r["instances_max"], nb)
    if nb != attendu:
        return "instance", "alignement a %d point(s), le referentiel en attend %d" % (nb, attendu)
    return "instance", "alignement a %d points mais instable" % nb

def est_stable(ap, cid):
    """Etat de stabilite enregistre par decider pour ce concept."""
    s = ap.get("stabilite", {}).get(cid)
    return bool(isinstance(s, dict) and s.get("stable"))

def prochaine_activite(famille, servis, pool="instances"):
    source = ACTIVITES if pool == "instances" else REEMPLOIS
    for a in source.get(famille, []):
        if a[0] not in servis:
            return a
    return None


def schema_employe(nom, code):
    """Un reemploi ne compte que si l'apprenant a employe le schema plutot qu'une
    recursion explicite : la soumission ne doit contenir aucun appel recursif."""
    a = LANGUE.analyse(nom, code)
    if a["forme"] in ("no-pattern", "no-recursion", "comprehension", "iterative"):
        return True
    return not (a["pas"] and "REC" in a["pas"])

def alignement_affichable(corpus, ref=None, famille=None):
    """Ce que l'atelier de remontee montre : les equations, ce qui est identique barre."""
    lignes = []
    for x in corpus:
        a = LANGUE.analyse(x["nom"], x["code"])
        lignes.append({"nom": x["nom"], "base": a["base"], "pas": a["pas"]})
    paires = [(x["nom"], x["code"]) for x in corpus]
    nb, forme, blocs = (compte_alignement(ref, famille, paires) if ref is not None
                        else etat_alignement(paires))
    return {"lignes": lignes, "points": nb, "blocs": blocs, "forme": forme}

# ============================================================ etat persistant

def charger_etat():
    if os.path.exists(ETAT):
        with open(ETAT, encoding="utf-8") as f:
            return json.load(f)
    return {"apprenants": {}, "groupes": {}, "contrats": {}}

def sauver_etat(e):
    with open(ETAT, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)

def nouvel_apprenant(nom, cohorte):
    ident = hashlib.sha1((nom + cohorte).encode()).hexdigest()[:4]
    return {"ident": ident, "nom": nom, "cohorte": cohorte, "regime": "solo",
            "etats": {}, "corpus": {}, "ecartes": {}, "servis": {},
            "reemplois": {}, "stabilite": {}, "groupe": {},
            "aides": {}, "derniere_erreur": {}, "echecs": {},
            "generalisations": {}, "invitations": {},
            "preferences": {"avance": "auto"}, "debuts": {}, "suspendu": False,
            "resolutions": {}}

def journaliser(ap, cid, exercice, chapitre, verdict, categorie, hors_delai=False):
    entree = {"horodatage": datetime.datetime.now().isoformat(timespec="seconds"),
              "cohorte": ap["cohorte"], "apprenant": ap["ident"],
              "chapitre": chapitre, "concept": cid, "exercice": exercice,
              "verdict": "reussite" if verdict["reussite"] else "erreur",
              "categorie": categorie,
              "message_ghc": verdict["message"][:2000],
              "silencieuse": bool(verdict["compile"] and not verdict["reussite"]),
              "hors_delai": bool(hors_delai)}
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")

def categoriser(verdict):
    """Delegue au fournisseur de langage, qui rend une categorie du vocabulaire commun."""
    return LANGUE.categorise(verdict["message"],
                              compile_mais_faux=verdict["compile"] and not verdict["reussite"])

# ============================================================ familles

def squelette(forme):
    """Ce que le mode « expose » de la remontee montre : la charpente, sans les noms."""
    if not forme:
        return None
    return ("f BASE = " + "?0" + "\nf (x:xs) = " + forme
            .replace("C1", "x").replace("REC2", "f xs").replace("REC1", "f xs"))


def etat_des_familles(ref):
    """Le controle que la console enseignante affiche."""
    import generateur as G
    out = []
    for nom, spec in ref["familles"].items():
        v = spec.get("validation", {})
        mode = v.get("mode", "none")
        res = {"famille": nom, "chapitre": spec.get("chapitre"),
               "ancrages": len(spec["ancrages"]), "mode": mode,
               "obligation": spec.get("obligation")}
        if mode in ("none", "confrontation"):
            res["verdict"] = "sans alignement"
        elif nom in G.REFERENCES:
            corpus, sigs = G.REFERENCES[nom]
            if mode == "signatures":
                obtenu, forme = N2.aligner_signatures(sigs)
            elif mode == "invariant":
                ok, det = N2.verifier_invariant_final(corpus)
                res["verdict"] = "invariant " + ("verifie" if ok else "NOT VERIFIE")
                out.append(res)
                continue
            else:
                fins, forme, blocs = N2.aligner_corps(corpus)
                obtenu = blocs if v.get("granularite") == "blocs" else fins
            res["obtenu"] = obtenu
            res["attendu"] = v.get("attendu")
            res["verdict"] = "conforme" if obtenu == v.get("attendu") else "NOT CONFORME"
            res["forme"] = forme
        else:
            res["verdict"] = "solutions de reference absentes"
        # Une famille servie doit offrir au moins instances_min + 1 activites :
        # le compte est calcule a instances_min solutions et confirme a la suivante.
        servies = len(ACTIVITES.get(nom, []))
        requis = ref["reglages"]["instances_min"] + 1
        if servies and servies < requis:
            res["verdict"] += " ; trop peu d'activites servies : %d (minimum %d)" % (servies, requis)
        out.append(res)
    return out
