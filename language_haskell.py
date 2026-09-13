"""Fournisseur de langage Haskell pour FPTutor-Shell.

Implemente l'interface attendue par le noyau : identification, commande
d'execution, gabarit du module de test, analyse vers le vocabulaire commun,
et classement des messages d'erreur.
"""

import normalisation2 as N2

name = "haskell"
extension = ".hs"


def command(chemin):
    return ["runghc", "-Wincomplete-patterns", chemin]


GABARIT = """module Main where
%s

main :: IO ()
main = do
%s
"""


def test_template(code, expressions):
    lignes = "\n".join("  print (%s)" % e for e in expressions)
    return GABARIT % (code.rstrip(), lignes)


def analyse(function_name, code):
    return N2.analyser(function_name, code)


def categorise(message, compile_mais_faux=False):
    if compile_mais_faux:
        return "wrong-result"
    if "non-exhaustive" in message:
        return "missing-base-case"
    if "Couldn't match expected type" in message and "Int" in message and "Double" in message:
        return "int-double-mix"
    if "Couldn't match" in message:
        return "incompatible-types"
    if "Variable not in scope" in message:
        return "unknown-name"
    if "parse error" in message:
        return "syntax"
    return "unclassified"


# formes rendues par analyser qui sont admissibles a l'alignement
ALIGNABLE_FORMS = ("constructors",)
