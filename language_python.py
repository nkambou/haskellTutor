"""Fournisseur de langage Python pour FPTutor-Shell.

Expose l'interface du tableau 2 (name, extension, command, test_template,
analyse, categorise) au-dessus de langue_python, qui contient l'analyseur
fonde sur le module ast. Les noms de formes et de categories sont traduits
vers le vocabulaire commun du cadre.
"""

import langue_python as _L

name = "python"
extension = ".py"

FORMES = {"constructeurs": "constructors", "comprehension": "comprehension",
          "iteratif": "iterative", "sans-recursion": "no-recursion",
          "non-analysable": "unanalysable", "sans-motif": "no-pattern"}

CATEGORIES = {"resultat-faux": "wrong-result", "appel-mauvaise-valeur": "missing-base-case",
              "cas-de-base-oublie": "missing-base-case",
              "types-incompatibles": "incompatible-types", "nom-inconnu": "unknown-name",
              "syntaxe": "syntax", "non-classee": "unclassified"}


def command(chemin):
    return _L.commande(chemin)


def test_template(code, expressions):
    return _L.gabarit_test(code, expressions)


def analyse(function_name, code):
    a = dict(_L.analyser(function_name, code))
    a["forme"] = FORMES.get(a["forme"], a["forme"])
    return a


def categorise(message, compile_mais_faux=False):
    c = _L.categoriser(message, compile_mais_faux=compile_mais_faux)
    return CATEGORIES.get(c, c)


# formes rendues par analyse qui sont admissibles a l'alignement
ALIGNABLE_FORMS = ("constructors",)
