# HaskellTutor

Tuteur intelligent pour l'abstraction ascendante en programmation fonctionnelle.
L'apprenant écrit plusieurs définitions récursives qui partagent une structure
que personne n'a nommée ; le schéma est ensuite obtenu en alignant ses propres
solutions.

## Lancer

    python3 serveur.py

    apprenant  : http://localhost:8080/
    enseignant : http://localhost:8080/enseignant

Anglais par défaut ; `?lang=fr` pour le français. Le réglage atteint aussi les
messages engendrés par le tuteur.

## Prérequis

Python 3.8 ou plus récent, sans aucune bibliothèque externe. GHC dans le
`PATH` : chaque soumission est réellement compilée et exécutée.

## Reproduire les mesures de l'article

| Mesure | Commande |
| --- | --- |
| Contrôle des seize familles contre le référentiel | `python3 generateur.py` |
| Induction des obligations par ablation d'ancrage | `python3 obligations.py` |
| Ablations des composants du moteur | `python3 ablations.py` |
| Relevés de cohorte par chapitre | `python3 releves.py journal.jsonl` |

## Les fichiers

    noyau.py              activités, évaluation, admission, politique, journal
    remontee.py           anti-unification, plus petite généralisation commune
    normalisation.py      normalisation textuelle
    normalisation2.py     constructeurs, gardes, signatures, commutativité
    language_haskell.py   les cinq éléments propres au langage
    referentiel.json      17 concepts, 9 paliers, 16 familles, obligations
    serveur.py            routes, vues, contrats, politique de séance
    textes.py             catalogue de messages, anglais et français
    etude.py              consentement et export anonymisé
    export_donnees.py     fichiers d'analyse dérivés des journaux
    generateur.py         contrôle des familles
    obligations.py        inducteur d'obligations
    ablations.py          ablations des composants
    releves.py            relevés de cohorte
    etudiant.html         application apprenante
    enseignant.html       console enseignante

## Licence

MIT. Aucune restriction pour un usage non académique.
# haskellTutor
