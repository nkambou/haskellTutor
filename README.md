# HaskellTutor

An intelligent tutoring system for bottom-up abstraction in functional
programming. Learners write several recursive definitions that share a
structure nobody has named; the schema is then obtained by aligning their own
solutions, and the tutor decides when that shared structure has stabilised
enough to be shown.

This is the artefact described in the accompanying paper. It is the whole
system: no framework layer, no second language instantiation.

## Run

    python3 serveur.py

    learner : http://localhost:8080/
    teacher : http://localhost:8080/enseignant

## Requirements

Python 3.8 or later, with no external library. GHC in the `PATH`: every
submission is really compiled and executed.

## Reproducing the measurements of the paper

| Measurement | Command |
| --- | --- |
| Validation of the sixteen families against the referential | `python3 generateur.py` |
| Obligation induction by anchor ablation | `python3 obligations.py` |
| Ablations of the recognition engine's components | `python3 ablations.py` |
| Cohort records by chapter | `python3 releves.py journal.jsonl` |

Each is a single command and needs no data beyond the referential.

## Files

    noyau.py              activities, evaluation, admission, policy, log
    remontee.py           anti-unification, least general generalization
    normalisation.py      textual normalization
    normalisation2.py     constructors, guards, signatures, commutativity
    language_haskell.py   the five language-specific elements
    referentiel.json      17 concepts, 9 tiers, 16 families, obligations
    serveur.py            routes, views, contracts, session policy
    textes.py             message catalogue
    generateur.py         family validator
    obligations.py        obligation inducer
    ablations.py          component ablations
    releves.py            cohort records
    etudiant.html         learner application
    enseignant.html       teacher console

The source text of the system is French for historical reasons; `textes.py`
supplies the English the interface presents. Activity names in traces are
reproduced as they occur in the running system: `doubler` doubles each element,
`carres` squares it, `aplatir` concatenates a list of lists.

## Writing exercises

The referential declares concepts, tiers and families. A family is a set of
anchors intended to produce one generalization, and the validator checks that
it can: it aligns the reference solutions and compares the number of variation
points obtained with the number declared. Run it before serving a family.

The obligation inducer reports which anchor of a family is load-bearing, that
is, the only one exhibiting a variation the family must show. Removing it
changes the alignment count. This is the check that replaces weeks of trial and
error, and it found in our own material an obligation that manual review had
missed.

## Licence

MIT. See LICENSE.
