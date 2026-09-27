"""Localisation par catalogue de messages, applique a la frontiere.

Le texte source du systeme est en francais. Ce module rend la version anglaise
en substituant des phrases entieres, en une seule passe : une portion deja
traduite n'est jamais reexaminee, ce qui evite les substitutions en cascade du
genre « exclus » -> « excluded » -> « excludeded ».

Deux fonctions publiques :

    traduire_texte(s, langue)   une chaine
    traduire(obj, langue)       recursivement, une structure JSON

Cette distribution est unilingue anglaise. Le texte source du systeme est
francais, pour des raisons historiques : ce module en rend la version anglaise,
qui est la seule que l'interface presente. Ajouter une langue consiste a
ajouter une table ici, la substitution etant appliquee a la frontiere plutot
que dispersee dans le code.
"""

import re

# ------------------------------------------------------------ catalogue
# Regle : une entree fait au moins quinze caracteres, ou figure dans ETIQUETTES
# et n'est alors substituee qu'en mot entier.

CATALOGUE = {
 'transforme en rapport « ce que le tuteur observe ». Une erreur classée': 'turns into the report “what the tutor observes”. An error classified as',
 ', qui en tire le rapport « ce que le tuteur observe ». ': ', which derives from it the report “what the tutor observes”. ',
 'Les étayages pris y figurent sous la catégorie': 'Scaffolding taken appears there under the category',
 "engendre le rapport complet de l'unité 4, messages GHC compris.": 'generates the complete report for unit 4, GHC messages included.',
 "reprendre comme ancrages les trois fonctions malhonnetes rencontrees dans les unites precedentes, pour que la remontee solde des dettes reelles de l'apprenant": 'take as anchors the three dishonest functions met in earlier units, so that the abstraction settles real debts of the learner',
 # --- console enseignante : autres onglets
 'Aucun groupe formé.': 'No group formed.',
 "Un groupe en attente ne donne pas accès à l'atelier de consolidation tant qu'il n'est pas validé.": 'A pending group gives no access to the consolidation workshop until it is approved.',
 'Tout le monde est affecté.': 'Everyone is assigned.',
 "Cette liste ne va qu'à vous : aucun apprenant ne voit qui n'a été invité par personne.": 'This list is for you only: no learner sees who has not been invited by anyone.',
 "Aucun apprenant au plafond d'instances.": 'No learner at the instance ceiling.',
 'Activités exécutables': 'Executable activities',
 ' famille(s) sans activités exécutables': ' family(ies) without executable activities',
 ". Elles sont spécifiées dans le référentiel mais aucun ancrage n'a encore été écrit. Pour en ajouter un, une seule chose est à écrire dans le dictionnaire ACTIVITES de noyau.py : un identifiant, un énoncé, une signature, une amorce, et la liste des tests sous forme de couples (expression, résultat attendu).": '. They are specified in the referential but no anchor has been written yet. To add one, a single entry is written in the ACTIVITES dictionary of noyau.py: an identifier, a statement, a signature, a stub, and the list of tests as pairs (expression, expected result).',
 'Formation des groupes': 'Group formation',
 'autorisé par': 'allowed by',
 'mode de formation': 'formation mode',
 "fenêtre d'auto-organisation (h)": 'self-organisation window (h)',
 "L'auto-organisation ne s'exerce que dans l'ensemble éligible : seuls les pairs au même état sur le concept visé sont proposés à l'apprenant.": 'Self-organisation only operates within the eligible set: only peers in the same state on the target concept are offered to the learner.',
 "L'auto-organisation ne s'exerce que dans l'ensemble eligible : seuls les pairs au meme etat sur le concept vise sont proposes.": 'Self-organisation only operates within the eligible set: only peers in the same state on the target concept are offered.',
 'Ces réglages se modifient dans': 'These settings are changed in',
 ', qui est le seul fichier de configuration du cours.': ", which is the course's only configuration file.",
 'Relevés par chapitre': 'Records by chapter',
 "Aucune soumission enregistrée pour l'instant.": 'No submission recorded yet.',
 'Ces relevés sont ceux que': 'These records are the ones that',
 'est une erreur que le compilateur ne signale pas : le code compile et calcule faux. Une catégorie inconnue signale une erreur nouvelle, à ajouter au catalogue de': 'is an error the compiler does not report: the code compiles and computes the wrong result. An unknown category signals a new error, to be added to the catalogue of',
 'En ligne de commande :': 'From the command line:',
 'Journal des soumissions': 'Submission log',
 'Le journal est écrit dans': 'The log is written to',
 ', au format attendu par': ', in the format expected by',
 ' soumissions': ' submissions',
 "Un relevé nom-note : ne gardez que les reçus, ceux qui ont au moins 60.":
   "A name-and-mark record: keep only those who passed, with at least 60.",
 " ; trop peu d'activites servies : ": "; too few served activities: ",
 # typographie : l'espace avant le deux-points ne se garde pas en anglais
 " : ": ": ",
 " ; ": "; ",
 " : l'apprenant ne pourra pas quitter la séance avant d'avoir acquis le concept. À réserver aux séances encadrées.": ': the learner may not leave the session before acquiring the concept, and this should be reserved for supervised sessions.',
 'console enseignante': 'teacher console',
 'sans remontée': 'no abstraction',
 'sans alignement': 'no alignment',
 'invariant verifie': 'verified invariant',
 # --- console enseignante : familles et contrats
 "Familles d'activités": 'Activity families',
 "Le contrôle aligne les solutions de référence de chaque famille et compare le résultat à ce que le référentiel annonce. Une famille non conforme n'est pas servie : elle produirait un plateau.": "The check aligns each family's reference solutions and compares the result with what the referential declares. A non-conforming family is not served: it would produce a plateau.",
 'au moins un ancrage a deux niveaux, sans quoi le motif compose reste invisible': 'at least one two-level anchor, without which the composed pattern stays invisible',
 "au moins un ancrage ou ce n'est pas une liste qui decroit (repete)": 'at least one anchor where what decreases is not a list (repete)',
 "servir en reemploi un cas ou l'argument n'est pas en derniere position (div x 2), pour que la condition soit eprouvee et non seulement enoncee": 'serve as a reuse item a case where the argument is not in final position (div x 2), so that the condition is tested and not merely stated',
 'au moins un ancrage a constructeurs sans champ, pour que le type enumere soit rencontre': 'at least one anchor with fieldless constructors, so that the enumerated type is met',
 "au moins un ancrage dont l'operation ne combine pas les deux appels par la meme structure (hauteurA) ; sans lui la generalisation obtenue est trop etroite": 'at least one anchor whose step does not combine the two recursive calls with the same structure (hauteurA); without it the generalisation obtained is too narrow',
 "au moins un ancrage sur un type parametre, pour faire apparaitre la contrainte d'instance": 'at least one anchor on a parameterised type, to bring out the instance constraint',
 "servir en reemploi une instance fautive (Paire qui echange ses champs), pour eprouver les deux regles qu'aucun compilateur ne verifie": 'serve as a reuse item a faulty instance (Paire swapping its fields), to test the two laws that no compiler checks',
 'au moins un ancrage a trois etapes : a deux niveaux, la branche Nothing -> Nothing ne se percoit pas encore comme du bruit': 'at least one three-step anchor: at two levels the repeated Nothing -> Nothing branch is not yet perceived as noise',
 "le coeur pur doit etre appelable depuis GHCi sans entree-sortie ; l'activite le verifie": 'the pure core must be callable from GHCi without input or output; the activity checks it',
 "au moins un ancrage a definition circulaire (fibs) : c'est le seul qui montre ce que la paresse permet et non seulement ce qu'elle evite": 'at least one anchor with a circular definition (fibs): it is the only one that shows what laziness permits and not merely what it avoids',
 "l'ancrage de mesure est obligatoire : la difference ne se voit pas sans +RTS -s": 'the measurement anchor is mandatory: the difference is invisible without +RTS -s',
 ": le concept sera présenté avant d'avoir été produit, et l'indicateur de réemploi y perdra sa valeur diagnostique. Le réglage est conservé : la console signale, elle n'interdit pas.": ': the concept will be presented before it has been produced, and the reuse indicator will lose its diagnostic value there. The setting is kept: the console warns, it does not forbid.',
 'auto_avec_accord': 'self-organisation with approval',
 'groupes de 2 à 3': 'groups of 2 to 3',
 'groupes de 2 à 4': 'groups of 2 to 4',
 'groupes de 2 à 5': 'groups of 2 to 5',
 'groupes de 3 à 4': 'groups of 3 to 4',
 'groupes de 3 à 5': 'groups of 3 to 5',
 'groupes de 3 à 6': 'groups of 3 to 6',
 "Étayage, niveau 1 sur 3": "Scaffolding, level 1 of 3",
 "Étayage, niveau 2 sur 3": "Scaffolding, level 2 of 3",
 "Étayage, niveau 3 sur 3": "Scaffolding, level 3 of 3",
 # --- libelles d'interface verifies sur les captures de l'article
 "soumission(s) enregistrée(s).": "submission(s) recorded.",
 "Aucune solution enregistrée pour ce concept.": "No solution recorded for this concept yet.",
 "parcours vers la programmation fonctionnelle": "a pathway to functional programming",
 "points mais instable": "variation point(s), not yet stable",
 "Voici les fonctions que ": "These are the functions ",
 # --- messages du tuteur, reussite
 "Bien vu.": "Well spotted.",
 "solution au dossier ; le tuteur en attend au moins":
   "solution in the dossier; the tutor expects at least",
 "solutions au dossier ; le tuteur en attend au moins":
   "solutions in the dossier; the tutor expects at least",
 "avant de vous les montrer ensemble.": "before showing them to you together.",
 "solutions au dossier. En les comparant, le tuteur y voit":
   "solutions in the dossier. Comparing them, the tutor sees",
 "chose qui change d'une solution a l'autre. Il en cherche":
   "thing that changes from one solution to the next. It is looking for",
 "choses qui changent d'une solution a l'autre. Il en cherche":
   "things that change from one solution to the next. It is looking for",
 "Le tuteur verifie sur une solution de plus que ce compte ne bouge pas.":
   "The tutor checks on one more solution that this count does not move.",
 "et le compte ne bouge plus.": "and the count no longer moves.",
 "point de variation, et le compte ne bouge plus.":
   "variation point, and the count no longer moves.",
 "points de variation, et le compte ne bouge plus.":
   "variation points, and the count no longer moves.",
 "c'est le compte attendu.": "that is the expected count.",
 "Vous allez pouvoir les regarder ensemble.":
   "You will be able to look at them together.",
 "Votre solution est enregistree.": "Your solution is recorded.",
 "Elle est conservee a part.": "It is kept separately.",

 # --- messages du tuteur, solution correcte mais hors forme
 "C'est juste, et votre solution fonctionne.":
   "That is right, and your solution works.",
 "Pour la suite, le tuteur a besoin de solutions ecrites de la meme maniere, parce qu'il va vous les montrer cote a cote : c'est en les comparant que vous trouverez ce qu'elles ont en commun.":
   "For what follows, the tutor needs solutions written in the same way, because it is going to show them to you side by side: it is by comparing them that you will find what they have in common.",
 "La votre est correcte mais elle ne se compare pas terme a terme avec les autres.":
   "Yours is correct, but it does not compare term by term with the others.",
 "Le tuteur passe a un autre probleme de meme nature. Ecrivez-le en distinguant le cas de la liste vide et le cas ou elle a au moins un element : c'est cette forme-la qu'il faut pour la suite.":
   "The tutor moves to another problem of the same kind. Write it by distinguishing the case of the empty list from the case where it has at least one element: that is the form needed for what follows.",
 "Reecrivez la meme fonction en distinguant explicitement le cas de la liste vide et le cas ou elle a au moins un element.":
   "Write the same function again, distinguishing explicitly the case of the empty list from the case where it has at least one element.",
 "Vous savez visiblement deja obtenir ce resultat sans le detailler. Ecrivez-le maintenant detaille, et vous aurez les deux versions sous les yeux.":
   "You evidently already know how to obtain this result without spelling it out. Write it out now, and you will have both versions in front of you.",
 "Elle est correcte, mais elle n'entre pas dans la comparaison :":
   "It is correct, but it does not enter the comparison:",
 "correcte mais non alignable": "correct but not alignable",
 "correcte mais sans recursion explicite": "correct but without explicit recursion",
 "schema deja employe": "schema already used",
 "aucun cas recursif reconnu": "no recursive case recognised",
 "tests non reussis": "tests not passed",
 "Non admise a l'alignement :": "Not admitted to the alignment:",
 "Soumission admise au corpus d'alignement.":
   "Submission admitted to the alignment corpus.",
 "Compilation reussie.": "Compiled successfully.",
 "tests reussis.": "tests passed.",

 # --- raisons de non-comparabilite
 "une comprehension donne le meme resultat et masque cet endroit precis":
   "a comprehension gives the same result and hides that precise place",
 "un accumulateur applique l'operation avant l'appel recursif, ce qui est un autre schema":
   "an accumulator applies the operation before the recursive call, which is another schema",
 "une fonction toute faite donne le resultat sans montrer la marche":
   "a library function gives the result without showing the procedure",
 "il n'y a pas de cas recursif a comparer":
   "there is no recursive case to compare",

 # --- etayage
 "Trois niveaux, a la demande. Aucun ne donne la solution ni ne nomme le schema.":
   "Three levels, on request. None gives the solution or names the schema.",
 "Le compilateur signale un motif non couvert. Quelle forme d'entree votre definition ne traite-t-elle pas ?":
   "The compiler reports an uncovered pattern. Which form of input does your definition not handle?",
 "Le compilateur signale qu'une forme d'entree n'est pas traitee.":
   "The compiler reports that one form of input is not handled.",
 "Vous pouvez demander un etayage : trois niveaux, aucun ne donne la solution.":
   "You may ask for scaffolding: three levels, none of which gives the solution.",
 "fonde sur votre derniere erreur :": "based on your last error:",
 "Il vous manque une equation dont le motif est":
   "You are missing an equation whose pattern is",
 "Sa valeur est celle qui ne change rien a l'operation que vous employez.":
   "Its value is the one that changes nothing in the operation you are using.",
 "Deux tentatives sans succes : vous pouvez":
   "Two attempts without success: you may",

 # --- consigne de forme et explication epistemique
 "Forme attendue": "Expected form",
 "Ecrivez cette fonction en distinguant explicitement le cas de la liste vide et le cas ou elle a au moins un element. Une solution correcte ecrite autrement sera acceptee et conservee, mais elle ne pourra pas etre comparee aux autres.":
   "Write this function by distinguishing explicitly the case of the empty list from the case where it has at least one element. A correct solution written otherwise will be accepted and kept, but it will not be comparable with the others.",
 "Pourquoi cette forme ?": "Why this form?",
 "Pour que la comparaison soit possible, il faut voir deux choses dans chaque solution :":
   "For the comparison to be possible, two things must be visible in each solution:",
 "Autrement dit, la contrainte de forme n'est pas une exigence de style : c'est ce qui rend la comparaison possible.":
   "The form requirement is therefore not a matter of style: it is what makes the comparison possible.",
 "La contrainte porte donc sur ce que la solution rend visible, pas sur sa qualite.":
   "The requirement concerns what the solution makes visible, not its quality.",
 "Une comprehension donne le meme resultat et masque cet endroit precis.":
   "A comprehension gives the same result and hides that precise place.",

 # --- verification par explication
 "Que rend votre fonction sur l'entree vide ?":
   "What does your function return on the empty input?",
 "Dans votre cas recursif, quelle expression designe le resultat deja calcule sur le reste de l'entree ?":
   "In your recursive case, which expression denotes the result already computed on the rest of the input?",
 "Cette valeur est celle qui ne change rien a l'operation que vous employez : c'est ainsi qu'on la trouve.":
   "That value is the one that changes nothing in the operation you are using, which is how it is found.",
 "C'est l'appel recursif : vous supposez que la fonction sait deja repondre sur le reste, et vous vous contentez de combiner ce resultat avec le premier element.":
   "That is the recursive call: you assume the function already answers on the rest, and you simply combine that result with the first element.",
 "soumission tres rapide apres l'ouverture de l'activite":
   "submission arriving within seconds of the activity being opened",
 "aucune tentative intermediaire, aucun etayage":
   "no intermediate attempt, no scaffolding",
 "mise en forme inhabituelle pour une saisie au fil de l'ecriture":
   "layout unusual for text typed as it is written",
 "Merci : votre explication correspond a ce que votre code fait.":
   "Thank you: your explanation matches what your code does.",
 "Votre reponse ne correspond pas a ce que votre code fait. La solution reste enregistree ; reprenez-la si vous voulez, et demandez un etayage au besoin.":
   "Your answer does not match what your code does. The solution stays recorded; revise it if you wish, and ask for scaffolding if you need it.",

 # --- decisions et motifs
 "corpus insuffisant": "corpus insufficient",
 "alignement stable a": "alignment stable at",
 "points de variation": "variation points",
 "point de variation": "variation point",
 "alignement a": "alignment at",
 "mais pas encore stable": "but not yet stable",
 "plus d'ancrage disponible dans la famille":
   "no anchor left in the family",
 "plafond d'instances atteint": "instance ceiling reached",
 "reemploi a servir": "reuse item to serve",
 "concept acquis": "concept acquired",

 # --- variantes accentuees, telles qu'elles figurent dans le referentiel
 "Des notes sur cent : ne gardez que les reçues.":
   "Marks out of a hundred: keep only the passing ones.",
 "Types définis par l'utilisateur":
   "User-defined types",
 "Listes et filtrage par patterns":
   "Lists and pattern matching",
 "Récursion structurelle":
   "Structural recursion",
 "Évaluation paresseuse":
   "Lazy evaluation",
 "Échec, choix, effets":
   "Failure, choice, effects",
 "Les trois schémas":
   "The three schemas",
 "Ordre supérieur":
   "Higher order",

 "Fichier lu par le générateur. Un enseignant qui change de progression ne modifie que ce fichier.":
   "File read by the generator. A teacher changing the progression edits this file only.",
 "le cas de base doit varier, sinon la troisième variation reste invisible":
   "the base case must vary, otherwise the third variation stays invisible",
 "rendre un type personnel utilisable par une fonction générique":
   "make a user-defined type usable by a generic function",
 "supprimer un argument nommé dans trois définitions existantes":
   "remove a named argument from three existing definitions",
 "Enchaîner deux fonctions sans nommer la valeur intermédiaire":
   "Chain two functions without naming the intermediate value",
 "séparer le calcul pur de l'entrée-sortie dans un programme":
   "separate pure computation from input and output in a program",
 "La récursion suit la forme du type, pas celle de la liste":
   "Recursion follows the shape of the type, not that of the list",
 "Cas de base, cas récursif, décroissance sur la structure":
   "Base case, recursive case, decrease on the structure",
 "écrire le pli d'un type défini par l'apprenant lui-même":
   "write the fold of a type the learner defined",
 "Une fonction à deux arguments en est une à un argument":
   "A two-argument function is a one-argument function",
 "Une liste est une structure récursive, pas un tableau":
   "A list is a recursive structure, not an array",
 "au moins un ancrage dont l'opération ignore l'élément":
   "at least one anchor whose operation ignores the element",
 "écrire une récursion sur une liste non vue en cours":
   "write a recursion over a list not seen in the course",
 "Une fonction qui peut échouer le dit dans son type":
   "A function that may fail says so in its type",
 "Ce qui sort du programme est marqué dans le type":
   "What leaves the program is marked in the type",
 "Le compilateur connaît le type avant l'exécution":
   "The compiler knows the type before execution",
 "écart de surface maximal, écart de structure nul":
   "maximal surface variation, null structural variation",
 "Une même opération sur des types différents":
   "One operation on several types",
 "De Haskell à la programmation fonctionnelle":
   "From Haskell to functional programming",
 "modéliser un domaine en trois constructeurs":
   "model a domain with three constructors",
 "remplacer une fonction partielle du prélude":
   "replace a partial function from the prelude",
 "Ce qui n'est pas demandé n'est pas calculé":
   "What is not asked for is not computed",
 "écrire un motif à deux niveaux (x:y:reste)":
   "write a two-level pattern (x:y:rest)",
 "Enchaîner des calculs qui peuvent échouer":
   "Chain computations that may fail",
 "Deux plis, deux comportements en mémoire":
   "Two folds, two behaviours in memory",
 "redéfinir map ou filter à l'aide du pli":
   "redefine map or filter using the fold",
 "Garder ou écarter selon une condition":
   "Keep or discard on a condition",
 "employer le schéma sans y être invité":
   "use the schema unprompted",
 "map se généralise au-delà des listes":
   "map generalises beyond lists",
 "réécrire un pipeline de trois étapes":
   "rewrite a three-stage pipeline",
 "supprimer trois filtrages imbriqués":
   "remove three nested filters",
 "écrire fmap pour un type personnel":
   "write fmap for a user-defined type",
 "Réduire une liste à une valeur":
   "Reduce a list to a value",
 "Transformer chaque élément":
   "Transform each element",
 "arithmétique unaire":
   "unary arithmetic",
 "ignore l'élément":
   "ignores the element",
 "sur la chaîne":
   "on the string",
 "arithmétique":
   "arithmetic",

 "avez écrites. Le tuteur a aligné leurs cas de base et leurs cas récursifs. Écrivez une seule définition qui les remplace toutes.":
   "have written. The tutor has aligned their base cases and their recursive cases. Write a single definition that replaces them all.",
 "écrire assez de solutions comparables, y trouver ce qu'elles ont en commun, puis l'employer sans y être invité":
   "write enough comparable solutions, find what they share, then use it unprompted",
 "écrire assez de solutions comparables, y trouver ce qu'elles ont en commun, puis l'employer sans y etre invite":
   "write enough comparable solutions, find what they share, then use it unprompted",
 "Cliquez sur une solution pour la revoir et la reprendre. La reprendre remplace votre version dans le dossier.":
   "Click a solution to review and revise it. Revising replaces your version in the dossier.",
 "Un concept passe à « acquis » au réemploi spontané du schéma, pas à la réussite de l'activité.":
   "A concept becomes acquired on spontaneous reuse of the schema, not on completing the activity.",
 "Écrivez votre définition ci-dessous. Elle est conservée et servira à l'atelier d'équipe.":
   "Write your definition below. It is kept and will be used in the team workshop.",
 "Vous pouvez quitter la séance à tout moment ; votre dossier est conservé.":
   "You may leave the session at any time; your dossier is kept.",
 "Aucun groupe sur ce concept.":
   "No group on this concept.",
 "Ce qu'il faut atteindre :":
   "What has to be reached:",
 "enchaîner automatiquement":
   "advance automatically",
 "Valider ma généralisation":
   "Submit my generalisation",
 "attendre que je continue":
   "wait until I continue",
 "Voici les fonctions que":
   "These are the functions",
 "Après une réussite :":
   "After a success:",
 "Rester sur cet écran":
   "Stay on this screen",
 "Demander un étayage":
   "Ask for scaffolding",
 "Atelier de remontée":
   "Abstraction workshop",
 "Compiler et tester":
   "Compile and test",
 "Carte des concepts":
   "Concept map",
 "Décision du tuteur":
   "Tutor's decision",
 "Activité engendrée":
   "Generated activity",
 "Quitter la séance":
   "Leave the session",
 "Activité suivante":
   "Next activity",
 "Gérer mon groupe":
   "Manage my group",
 "Ma progression":
   "My progress",
 "Mes solutions":
   "My solutions",
 "hors forme :":
   "off-form:",
 "Mon activité":
   "My activity",
 "instance(s)":
   "instance(s)",
 "hors ligne":
   "offline",
 "Pas encore":
   "Not yet",
 "au dossier":
   "in the dossier",
 "réemployer":
   "reuse",
 "Décision :":
   "Decision:",
 "Le tuteur":
   "The tutor",
 "Régime :":
   "Regime:",
 "comparer":
   "compare",
 "Étayage":
   "Scaffolding",
 "verrou":
   "locked",
 "Séance":
   "Session",
 "Groupe":
   "Group",
 "écrire":
   "write",

 "Le tuteur ne vous montrera vos solutions ensemble que lorsque ce compte sera atteint et stable. Il n'y a rien à mémoriser d'ici là.":
   "The tutor will show your solutions together only once that count is reached and stable. There is nothing to memorise until then.",
 "avez écrites. Le tuteur a aligné leurs cas de base et leurs cas récursifs. Écrivez une seule définition qui les remplace toutes.":
   "have written. The tutor has aligned their base cases and their recursive cases. Write a single definition that replaces them all.",
 "Cliquez sur une solution pour la revoir et la reprendre. La reprendre remplace votre version dans le dossier.":
   "Click a solution to review and revise it. Revising replaces your version in the dossier.",
 "Un concept passe à « acquis » au réemploi spontané du schéma, pas à la réussite de l'activité.":
   "A concept becomes acquired on spontaneous reuse of the schema, not on completing the activity.",
 "Écrivez votre définition ci-dessous. Elle est conservée et servira à l'atelier d'équipe.":
   "Write your definition below. It is kept and will be used in the team workshop.",
 "Ces réussites sont enregistrées ; elles ne servent simplement pas à la comparaison.":
   "These successes are recorded; they simply do not serve the comparison.",
 "Trois niveaux, à la demande. Aucun ne donne la solution ni ne nomme le schéma.":
   "Three levels, on request. None gives the solution or names the schema.",
 "Vous pouvez demander un étayage : trois niveaux, aucun ne donne la solution.":
   "You may ask for scaffolding: three levels, none of which gives the solution.",
 "Vous pouvez quitter la séance à tout moment ; votre dossier est conservé.":
   "You may leave the session at any time; your dossier is kept.",
 "Enchaîner deux fonctions sans nommer la valeur intermédiaire":
   "Chain two functions without naming the intermediate value",
 "La récursion suit la forme du type, pas celle de la liste":
   "Recursion follows the shape of the type, not that of the list",
 "Cas de base, cas récursif, décroissance sur la structure":
   "Base case, recursive case, decrease on the structure",
 "Une fonction à deux arguments en est une à un argument":
   "A two-argument function is a one-argument function",
 "Une liste est une structure récursive, pas un tableau":
   "A list is a recursive structure, not an array",
 "Une fonction qui peut échouer le dit dans son type":
   "A function that may fail says so in its type",
 "Le compilateur connaît le type avant l'exécution":
   "The compiler knows the type before execution",
 "Ce qui sort du programme est marqué dans le type":
   "What leaves the program is marked in the type",
 "Une même opération sur des types différents":
   "One operation on several types",
 "Ce qui n'est pas demandé n'est pas calculé":
   "What is not asked for is not computed",
 "Enchaîner des calculs qui peuvent échouer":
   "Chain computations that may fail",
 "Ce qui change d'une solution à l'autre :":
   "What varies from one solution to the next:",
 "Deux plis, deux comportements en mémoire":
   "Two folds, two behaviours in memory",
 "Garder ou écarter selon une condition":
   "Keep or discard on a condition",
 "map se généralise au-delà des listes":
   "map generalises beyond lists",
 "— fondé sur votre dernière erreur :":
   "— based on your last error:",
 "fondé sur votre dernière erreur":
   "based on your last error",
 "Types définis par l'utilisateur":
   "User-defined types",
 "Réduire une liste à une valeur":
   "Reduce a list to a value",
 "Problèmes résolus autrement :":
   "Problems solved otherwise:",
 "Aucun groupe sur ce concept.":
   "No group on this concept.",
 "et le compte ne bouge plus.":
   "and the count no longer moves.",
 "Écartées de l'alignement :":
   "Set aside from the alignment:",
 "Transformer chaque élément":
   "Transform each element",
 "enchaîner automatiquement":
   "advance automatically",
 "Solutions au dossier :":
   "Solutions in the dossier:",
 "Récursion structurelle":
   "Structural recursion",
 "Évaluation paresseuse":
   "Lazy evaluation",
 "le tuteur en cherche":
   "the tutor is looking for",
 "Après une réussite :":
   "After a success:",
 "Échec, choix, effets":
   "Failure, choice, effects",
 "Demander un étayage":
   "Ask for scaffolding",
 "Atelier de remontée":
   "Abstraction workshop",
 "remontée discovery":
   "abstraction discovery",
 "Activité engendrée":
   "Generated activity",
 "Décision du tuteur":
   "Tutor's decision",
 "Quitter la séance":
   "Leave the session",
 "Activité suivante":
   "Next activity",
 "Les trois schémas":
   "The three schemas",
 "remontée exposed":
   "abstraction exposed",
 "Gérer mon groupe":
   "Manage my group",
 "Étayage, niveau":
   "Scaffolding, level",
 "remontée guided":
   "abstraction guided",
 "Ordre supérieur":
   "Higher order",
 "Ma progression":
   "My progress",
 "Mes solutions":
   "My solutions",
 "Mon activité":
   "My activity",
 "hors forme :":
   "off-form:",
 "régime free":
   "regime free",
 "régime solo":
   "regime solo",
 "régime pair":
   "regime pair",
 "régime team":
   "regime team",
 "au minimum.":
   "at least.",
 "Décision :":
   "Decision:",
 "réemployer":
   "reuse",
 "Régime :":
   "Regime:",
 "Étayage":
   "Scaffolding",
 "Séance":
   "Session",
 "écrire":
   "write",

 "mode discovery · 1 point(s) de variation":
   "discovery mode · 1 variation point",
 "Voici les fonctions que":
   "These are the functions",
 "point(s) de variation":
   "variation point(s)",

 "Le tuteur vous demande de temps à autre d'expliquer ce que fait votre code. Cela ne met pas votre travail en doute : mettre une solution en mots est une des façons les plus efficaces de l'apprendre.":
   "The tutor asks from time to time what your code does. This does not call your work into question: putting a solution into words is one of the most effective ways of learning it.",
 "Multipliez chaque element par deux.":
   "Multiply each element by two.",
 "Multipliez chaque élément par deux.":
   "Multiply each element by two.",
 "Une question sur votre solution.":
   "A question about your solution.",
 "Continuer":
   "Continue",
 "Répondre":
   "Answer",

 "Dans votre cas récursif, quelle expression désigne le résultat déjà calculé sur le reste de l'entrée ?":
   "In your recursive case, which expression denotes the result already computed on the rest of the input?",
 "Que rend votre fonction sur l'entrée vide ?":
   "What does your function return on the empty input?",
 "Compilation réussie. 2 tests réussis.":
   "Compiled successfully. 2 tests passed.",
 "Compilation réussie. 3 tests réussis.":
   "Compiled successfully. 3 tests passed.",
 "Compilation réussie.":
   "Compiled successfully.",
 "tests réussis.":
   "tests passed.",

 "votre solution ne donne pas le bon résultat":
   "your solution does not give the right result",
 "Compilation réussie, mais ":
   "Compiled successfully, but ",
 "Compilation réussie. ":
   "Compiled successfully. ",
 " tests réussis.":
   " tests passed.",

 " au lieu de ": " instead of ",



 "La votre est correcte mais elle ne distingue pas les cas : on n'y voit ni ce que vaut le resultat sur une liste vide, ni ce que vous faites du premier element.":
   "Yours is correct, but it does not distinguish the cases: it shows neither what the result is on an empty list nor what you do with the first element.",

 " sur 3 au minimum.": " (at least 3 required).",
 " sur 4 au minimum.": " (at least 4 required).",
 " sur 5 au minimum.": " (at least 5 required).",
 "(0 sur 3)": "(0 of 3)", "(1 sur 3)": "(1 of 3)", "(2 sur 3)": "(2 of 3)",
 "(3 sur 3)": "(3 of 3)", "(0 sur 4)": "(0 of 4)", "(1 sur 4)": "(1 of 4)",
 "(2 sur 4)": "(2 of 4)", "(3 sur 4)": "(3 of 4)",
 "niveau 1 sur 3": "level 1 of 3", "niveau 2 sur 3": "level 2 of 3",
 "niveau 3 sur 3": "level 3 of 3",
 "Votre solution est enregistrée.": "Your solution is recorded.",

 "Non admise à l'alignement :": "Not admitted to the alignment:",
 "Non admise a l'alignement :": "Not admitted to the alignment:",

 "Non admise à l'alignement :":
   "Not admitted to the alignment:",
 "Soumission admise au corpus d'alignement.":
   "Submission admitted to the alignment corpus.",
 "Une question sur votre solution.":
   "A question about your solution.",
 "Votre solution est enregistrée.":
   "Your solution is recorded.",

 "exposée": "exposed",
 "été produit": "been produced",

 # --- etayage et lectures d'erreur
 "L'auto-organisation ne s'exerce que dans l'ensemble eligible : seuls les pairs au meme etat sur le concept vise sont proposes.":
   "Self-organisation operates only within the eligible set: only peers at the same state on the target concept are offered.",
 "Il vous manque une equation dont le motif est [] . Sa valeur est celle qui ne change rien a l'operation que vous employez.":
   "You are missing an equation whose pattern is [] . Its value is the one that changes nothing in the operation you are using.",
 "seuls les pairs au meme etat sur le concept vise sont proposes.":
   "only peers at the same state on the target concept are offered.",
 "L'auto-organisation ne s'exerce que dans l'ensemble eligible :":
   "Self-organisation operates only within the eligible set:",
 "change rien a l'operation que vous employez.":
   "changes nothing in the operation you are using.",
 "C'est l'appel recursif : vous supposez que la fonction sait deja repondre sur le reste, et vous vous contentez de combiner ce resultat avec le premier element.":
   "That is the recursive call: you assume the function already answers on the rest, and you simply combine that result with the first element.",
 "Une liste est soit vide, soit un element suivi d'une liste. Vous avez ecrit une equation pour la seconde forme seulement.":
   "A list is either empty or an element followed by a list. You have written an equation for the second form only.",
 "Une liste en comprehension, ou un appel a une fonction toute faite, donne le bon resultat sans montrer ces deux choses.":
   "A list comprehension, or a call to a library function, gives the right result without showing those two things.",
 "Autrement dit, la contrainte de forme n'est pas une exigence de style : c'est ce qui rend la comparaison possible.":
   "The form requirement is therefore not a matter of style: it is what makes the comparison possible.",
 "Le tuteur a fait l'alignement pour vous : les colonnes ci-dessus montrent le cas":
   "The tutor has done the alignment for you: the columns above show the case",
 "Votre solution est juste. Mais ce que le cours construit ici est la comparaison":
   "Your solution is right. But what the course is building here is the comparison",
 "Vous savez deja obtenir ce resultat. Ce que le cours cherche a construire n'est":
   "You already know how to obtain this result. What the course is trying to build is not",
 "Charpente : f [] = Z et f (x:xs) = ... x ... (f xs). Pour Z, cherchez la valeur":
   "Skeleton: f [] = Z and f (x:xs) = ... x ... (f xs). For Z, look for the value",
 "Votre solution fonctionne. Ce que le cours cherche ici est ce qui reste commun":
   "Your solution works. What the course is after here is what remains common",
 "Comparez le type attendu et le type trouve, puis demandez a GHCi le type de la":
   "Compare the expected type with the type found, then ask GHCi for the type of the",
 "Charpente : f [] = [] puis f (x:xs) avec deux gardes, dont l'une conserve x et":
   "Skeleton: f [] = [] then f (x:xs) with two guards, one of which keeps x and",
 "fois que vous resolvez un probleme autrement que ce que la comparaison attend.":
   "time you have solved a problem otherwise than the comparison expects.",
 "Votre solution est juste. La forme demandee n'est pas une question de style :":
   "Your solution is right. The form asked for is not a matter of style:",
 "Le desaccord porte sur l'argument que le message nomme. Verifiez ce que votre":
   "The disagreement concerns the argument the message names. Check what your",
 "Ecrivez une definition qui recoit en arguments ce qui varie, et qui garde tel":
   "Write a definition that takes what varies as arguments, and keeps as it is",
 "Il vous manque une equation dont le motif est [] . Sa valeur est celle qui ne":
   "You are missing an equation whose pattern is [] . Its value is the one that",
 "Une equation tient sur une ligne, ou ses suites sont indentees davantage que":
   "An equation fits on one line, or its continuations are indented more than",
 "Ecrite en distinguant le cas vide et le cas ou il reste un element, avec une":
   "Written by distinguishing the empty case from the case where an element remains, with a",
 "Pour que la comparaison soit possible, il faut voir deux choses dans chaque":
   "For the comparison to be possible, two things must be visible in each",
 "Comparez le resultat obtenu et le resultat attendu sur le premier test qui":
   "Compare the result obtained with the result expected on the first test that",
 "Ecrivez vos definitions les unes sous les autres et rayez tout ce qui est":
   "Write your definitions one below the other and strike out everything that is",
 "Verifiez l'orthographe et la casse : un nom de fonction commence par une":
   "Check the spelling and the case: a function name begins with a",
 "Deroulez votre definition a la main sur l'entree du test qui echoue, en":
   "Unfold your definition by hand on the input of the failing test,",
 "Un entier et un nombre fractionnaire se rencontrent dans la meme":
   "An integer and a fractional number meet in the same",
 "Cette valeur est celle qui ne change rien a l'operation que":
   "That value is the one that changes nothing in the operation you",
 "Dans votre cas recursif, quelle expression designe le":
   "In your recursive case, which expression denotes the",
 "C'est juste, et votre solution fonctionne. C'est la":
   "That is right, and your solution works. This is the",
 "Cette fonction produit une liste plus courte, sans modifier les elements gardes.":
   "This function produces a shorter list, without modifying the elements it keeps.",
 "Deux conduites sont possibles pour un element : le garder ou l'ignorer. Une ":
   "Two courses of action are available for an element, keeping it or ignoring it. One ",
 "Cette fonction produit une liste de meme longueur que celle qu'elle recoit.":
   "This function produces a list of the same length as the one it receives.",
 "Deux choses sont a decider : ce que vaut le resultat sur la liste vide, et ":
   "Two things have to be decided: what the result is on the empty list, and ",
 "Traitez le premier element, puis laissez la recursion s'occuper du reste.":
   "Deal with the first element, then let the recursion take care of the rest.",
 "Cette fonction ne produit pas une liste : elle produit une seule valeur.":
   "This function does not produce a list: it produces a single value.",
 "Si la fonction vient d'un module, il faut l'importer en tete de fichier.":
   "If the function comes from a module, it must be imported at the top of the file.",
 "Mettez chaque chaine en majuscules. import Data.Char (toUpper) autorise.":
   "Put each string in upper case. import Data.Char (toUpper) is allowed.",
 "Enveloppez chaque operande entier dans fromIntegral avant de diviser.":
   "Wrap each integer operand in fromIntegral before dividing.",
 "Les resultats de plusieurs verifications : toutes ont-elles reussi ?":
   "The results of several checks: did they all pass?",
 "Votre code compile : l'erreur n'est pas de forme mais de calcul.":
   "Your code compiles: the error is not one of form but of computation.",
 "Le compilateur a trouve un type la ou il en attendait un autre.":
   "The compiler found one type where it expected another.",
 "Le fichier ne s'analyse pas : le probleme est en amont du sens.":
   "The file does not parse: the problem lies upstream of meaning.",
 "Verifiez l'indentation et les parentheses de la ligne signalee.":
   "Check the indentation and the parentheses of the reported line.",
 "Votre code compile. L'erreur n'est pas de forme mais de calcul.":
   "Your code compiles. The error is not one of form but of computation.",
 "Une division exige des nombres fractionnaires des deux cotes.":
   "Division requires fractional numbers on both sides.",
 "Un nom employe dans votre code n'est defini nulle part.":
   "A name used in your code is not defined anywhere.",
 "Charpente : f [] = ... et f (x:xs) = ... x ... : f xs":
   "Skeleton: f [] = ... and f (x:xs) = ... x ... : f xs",
 "Ne gardez que les mots de moins de quatre lettres.":
   "Keep only the words of fewer than four letters.",
 "Le compilateur a refuse votre definition.":
   "The compiler rejected your definition.",
 "Aucun indice supplementaire a ce niveau.":
   "No further hint at this level.",
 "Remplacez chaque element par son carre.":
   "Replace each element by its square.",
 "Recollez des mots en une seule chaine.":
   "Join words into a single string.",
 "Un texte : ne gardez que les voyelles.":
   "A text: keep only the vowels.",
 "Un nom employe n'est pas defini.":
   "A name you used is not defined.",
 "Compile et passe les tests.":
   "Compiles and passes the tests.",

 # --- console enseignante
 "concept(s) en abstraction exposée : le concept sera présenté avant d'avoir été produit, et l'indicateur de réemploi y perdra sa valeur diagnostique. Le réglage est conservé : la console signale, elle n'interdit pas.":
   "concept(s) set to exposed abstraction: the concept will be presented before it has been produced, and the reuse indicator loses its diagnostic value there. The setting is kept: the console reports, it does not forbid.",
 "généralisation produite":
   "generalization produced",
 "abstraction exposée":
   "exposed abstraction",
 "vérification":
   "verification",
 "expliquées":
   "unexplained",
 "assistance":
   "scaffolding",
 "étayages":
   "scaffolding",
 "réemploi":
   "reuse",
 "conservé":
   "kept",
 "présenté":
   "presented",
 "remontée":
   "abstraction",
 "séquence":
   "sequence",
 "réglage":
   "setting",
 "régime":
   "regime",
 "palier":
   "tier",
 "réglé":
   "set",
 "délai":
   "allowance",
 "état":
   "state",
 ", la demande est déclenchée par des indices — soumission très rapide, aucune tentative intermédiaire, aucun étayage — qui sont des indices et non des preuves. Une explication qui ne correspond pas au code est signalée dans la cohorte ; la solution reste enregistrée et rien n'est retiré à l'apprenant.":
   " mode the request is triggered by indicators, a very fast submission, no intermediate attempt and no scaffolding taken, which are indicators and not evidence. An explanation that does not match the code is reported in the cohort view; the solution stays recorded and nothing is withdrawn from the learner.",
 "exposée : le concept sera présenté avant d'avoir été produit, et l'indicateur de réemploi y perdra sa valeur diagnostique. Le réglage est conservé : la console signale, elle n'interdit pas.":
   "exposed abstraction: the concept will be presented before it has been produced, and the reuse indicator loses its diagnostic value there. The setting is kept: the console reports, it does not forbid.",
 "demande la seconde écriture comme une comparaison plutôt que comme une correction. Dans les trois cas la réussite est comptée et la solution conservée.":
   "asks for the second writing as a comparison rather than a correction. In all three the success is counted and the solution kept.",
 "Le tuteur demande de temps à autre à l'apprenant d'expliquer sa propre solution, par deux questions engendrées à partir du code soumis. En régime":
   "The tutor asks the learner from time to time to explain their own solution, through two questions generated from the submitted code. In",
 "Une soumission hors délai est enregistrée comme telle mais compte quand même : le délai informe, il ne sanctionne pas.":
   "A late submission is recorded as such and still counts: the allowance informs, it does not penalise.",
 "l'apprenant ne pourra pas quitter la séance avant d'avoir acquis le concept. À réserver aux séances encadrées.":
   "the learner may not leave the session before acquiring the concept, and this should be reserved for supervised sessions.",
 "L'échelle d'étayage compte 3 niveaux ; aucun ne donne la solution ni ne nomme le schéma. En régime":
   "The scaffolding ladder has 3 levels; none gives the solution or names the schema. In",
 ", le tuteur propose l'étayage de lui-même après deux tentatives infructueuses.":
   " mode, the tutor offers scaffolding of its own accord after two failed attempts.",
 "passe à un autre problème de même nature avec une consigne de forme ;":
   "moves to another problem of the same kind with a form instruction;",
 "maintient l'exercice et demande une seconde écriture ;":
   "keeps the exercise and asks for a second writing;",
 "Le choix de l'apprenant ne s'y appliquera pas.":
   "The learner's choice will not apply there.",
 "Solution correcte mais hors forme.":
   "Correct but off-form solution.",
 "Appliquer à tous les concepts :":
   "Apply to every concept:",
 "Vérification par explication.":
   "Verification by explanation.",
 "concept(s) sans assistance":
   "concept(s) with scaffolding closed",
 "GENERALISATION PRODUITE":
   "GENERALIZATION PRODUCED",
 "GÉNÉRALISATION PRODUITE":
   "GENERALIZATION PRODUCED",
 "Tout remettre au défaut":
   "Reset everything to default",
 "Familles et validation":
   "Families and validation",
 "concept(s) en remontée":
   "concept(s) set to",
 "Contrats pédagogiques":
   "Pedagogical contracts",
 "Collaboration imposée":
   "Imposed collaboration",
 "aucune généralisation":
   "no generalization",
 "Séquence à compléter":
   "Sequence to be completed",
 "Délai par activité":
   "Allowance per activity",
 "État de la cohorte":
   "Cohort state",
 "NON EXPLIQUÉES":
   "UNEXPLAINED",
 "NON EXPLIQUEES":
   "UNEXPLAINED",
 "Avertissement.":
   "Warning.",
 "délai_minutes":
   "allowance_minutes",
 "VÉRIFICATION":
   "VERIFICATION",
 "HORS FORME":
   "OFF-FORM",
 "ASSISTANCE":
   "SCAFFOLDING",
 "réglés sur":
   "set out of",
 "hors forme":
   "off-form",
 "Activités":
   "Activities",
 "APPRENANT":
   "LEARNER",
 "Contrats":
   "Contracts",
 "Réglages":
   "Settings",
 "ETAYAGES":
   "SCAFFOLDING",
 "ÉTAYAGES":
   "SCAFFOLDING",
 "REMONTÉE":
   "ABSTRACTION",
 "SÉQUENCE":
   "SEQUENCE",
 "Groupes":
   "Groups",
 "Cohorte":
   "Cohort",
 "Relevés":
   "Records",
 "PALIER":
   "TIER",
 "RÉGIME":
   "REGIME",
 "Étude":
   "Study",
 "DÉLAI":
   "ALLOWANCE",
 "RÉGLÉ":
   "SET",
 " sur ":
   " on ",
 "ETAT":
   "STATE",
 "ÉTAT":
   "STATE",

 # --- lignes de contrat et pluriels
 "Contrat : assistance indices": "Contract: scaffolding on request",
 "Contrat : assistance guidage": "Contract: scaffolding proactive",
 "Contrat : assistance aucune": "Contract: scaffolding none",
 "Contrat : assistance": "Contract: scaffolding",
 "remontee decouverte": "abstraction discovery",
 "remontee guidee": "abstraction guided",
 "remontee exposee": "abstraction exposed",
 "regime libre": "regime free",
 "regime solo": "regime solo",
 "sequence libre": "sequence free",
 "1 points de variation": "1 variation point",
 "1 point de variation": "1 variation point",
 "1 chose qui change": "1 thing that changes",
 "mode decouverte": "discovery mode",
 "mode guide": "guided mode",
 "sans contrainte de temps": "no time allowance",
 "Aucune solution enregistree pour ce concept.":
   "No solution recorded for this concept.",
 "Ecartees de l'alignement :": "Set aside from the alignment:",
 "Problemes resolus autrement :": "Problems solved otherwise:",
 "Ces reussites sont enregistrees ; elles ne servent simplement pas a la comparaison.":
   "These successes are recorded; they simply do not serve the comparison.",
 "Solutions au dossier :": "Solutions in the dossier:",
 "au minimum.": "at least.",
 "Ce qui change d'une solution a l'autre :":
   "What varies from one solution to the next:",
 "le tuteur en cherche": "the tutor is looking for",
 "et le compte ne bouge plus": "and the count no longer moves",
 "Ce qu'il faut atteindre : ecrire assez de solutions comparables, y trouver ce qu'elles ont en commun, puis l'employer sans y etre invite.":
   "What has to be reached: write enough comparable solutions, find what they share, then use it unprompted.",
 "Le tuteur ne vous montrera vos solutions ensemble que lorsque ce compte sera atteint et stable. Il n'y a rien a memoriser d'ici la.":
   "The tutor will show your solutions together only once that count is reached and stable. There is nothing to memorise until then.",
 "Une activite de plus vous est servie.": "One more activity is served to you.",

 # --- libelles de concepts
 "Expressions, valeurs, types": "Expressions, values, types",
 "Listes et filtrage par motifs": "Lists and pattern matching",
 "Recursion structurelle": "Structural recursion",
 "Les trois schemas": "The three schemas",
 "Ordre superieur": "Higher order",
 "Types definis par l'utilisateur": "User-defined types",
 "Classes de types": "Type classes",
 "Echec, choix, effets": "Failure, choice, effects",
 "Evaluation paresseuse": "Lazy evaluation",
 "Le compilateur connait le type avant l'execution":
   "The compiler knows the type before execution",
 "Une liste est une structure recursive, pas un tableau":
   "A list is a recursive structure, not an array",
 "Cas de base, cas recursif, decroissance sur la structure":
   "Base case, recursive case, decrease on the structure",
 "Transformer chaque element": "Transform each element",
 "Garder ou ecarter selon une condition": "Keep or discard on a condition",
 "Reduire une liste a une valeur": "Reduce a list to a value",
 "Une fonction a deux arguments en est une a un argument":
   "A two-argument function is a one-argument function",
 "Enchainer deux fonctions sans nommer la valeur intermediaire":
   "Chain two functions without naming the intermediate value",
 "Un type est une somme de constructeurs": "A type is a sum of constructors",
 "La recursion suit la forme du type, pas celle de la liste":
   "Recursion follows the shape of the type, not that of the list",
 "Une meme operation sur des types differents":
   "One operation on several types",
 "map se generalise au-dela des listes": "map generalises beyond lists",
 "Une fonction qui peut echouer le dit dans son type":
   "A function that may fail says so in its type",
 "Enchainer des calculs qui peuvent echouer":
   "Chain computations that may fail",
 "Ce qui sort du programme est marque dans le type":
   "What leaves the program is marked in the type",
 "Ce qui n'est pas demande n'est pas calcule":
   "What is not asked for is not computed",
 "Deux plis, deux comportements en memoire":
   "Two folds, two behaviours in memory",

 # --- enonces d'activite, familles executables
 "Des quantites a convertir : multipliez chaque element par deux.":
   "Quantities to convert: multiply each element by two.",
 "Mettez chaque chaine en majuscules.": "Put each string in upper case.",
 "Donnez la premiere lettre de chaque chaine.":
   "Give the first letter of each string.",
 "Une liste de prenoms : donnez la premiere lettre de chacun.":
   "A list of first names: give the first letter of each.",
 "Des mesures a mettre au carre.": "Measurements to square.",
 "Un releve nom-note. Ne gardez que les notes.":
   "A name-and-mark record. Keep only the marks.",
 "Un releve de couples (nom, note) : ne gardez que les notes.":
   "A record of (name, mark) pairs: keep only the marks.",
 "Des numeros de place : ne gardez que les pairs.":
   "Seat numbers: keep only the even ones.",
 "Des champs de formulaire : ecartez ceux laisses vides.":
   "Form fields: discard those left empty.",
 "Des notes sur cent : ne gardez que celles qui atteignent soixante.":
   "Marks out of a hundred: keep only those that reach sixty.",
 "Des mots : ne gardez que ceux de plus de trois lettres.":
   "Words: keep only those longer than three letters.",
 "Le total des releves de temperature.": "The total of the temperature readings.",
 "Des releves de temperature : donnez le total.":
   "Temperature readings: give the total.",
 "Un facteur d'echelle par etage : donnez le facteur global.":
   "One scale factor per floor: give the overall factor.",
 "Un inventaire dont les elements importent peu : comptez-les.":
   "An inventory whose items matter little: count them.",
 "Des paragraphes decoupes en listes de mots : remettez-les bout a bout.":
   "Paragraphs split into word lists: put them end to end.",
 "Des morceaux de texte : recollez-les en une seule chaine.":
   "Pieces of text: join them into a single string.",
 "Changez le signe de chaque element.": "Change the sign of each element.",
 "Donnez la longueur de chaque chaine.": "Give the length of each string.",
 "Ne gardez que les nombres strictement positifs.":
   "Keep only the strictly positive numbers.",
 "Ne gardez que les voyelles d'un texte.": "Keep only the vowels of a text.",
 "Le plus grand element d'une liste non vide.":
   "The largest element of a non-empty list.",
 "Plusieurs verifications : toutes ont-elles reussi ?":
   "Several checks: did they all pass?",
}

# etiquettes courtes, substituees en mot entier seulement
ETIQUETTES = {
 "instance": "instance", "remontee": "abstraction", "abstraction": "abstraction",
 "reemploi": "reuse", "guidage": "guidance", "acquis": "acquired",
 "generalise": "generalised", "instances": "instances",
 "solo": "solo", "libre": "free", "oui": "yes", "non": "no",
 "toujours": "always", "jamais": "never",
 "aide-niveau-1": "scaffolding-level-1",
 "aide-niveau-2": "scaffolding-level-2", "aide-niveau-3": "scaffolding-level-3", "réussi": "passed",
 "Inscription": "Registration", "Régime": "Regime", "Parcours": "Pathway",
 
}

# Libelles courts qui ne se traduisent que lorsqu'ils forment a eux seuls tout le
# texte d'un element (un en-tete de colonne, un mot en gras ou en italique). Dans
# une phrase francaise non traduite, ils restent en francais : mieux vaut une
# phrase entierement francaise qu'une phrase melangee.
LIBELLES = {
 'défaut': 'default', 'Sans groupe': 'No group', 'énoncé': 'statement', 'catégorie': 'category',
 "vous": "you", "vide": "empty", "famille": "family", "ancrages": "anchors",
 "obtenu": "obtained", "attendu": "expected", "corps": "bodies", "conforme": "conforming",
 "si doute": "on-doubt", "expliquer_et_reecrire": "explain_and_rewrite",
 "expliquer_et_poursuivre": "explain_and_continue", "confronter": "confront",
}

_ENTREES = None


def _entrees():
    global _ENTREES
    if _ENTREES is None:
        _ENTREES = sorted(CATALOGUE.items(), key=lambda kv: -len(kv[0]))
    return _ENTREES


def traduire_texte(s, langue="en"):
    """Substitution en une passe : les portions deja traduites sont figees."""
    if langue == "fr" or not isinstance(s, str) or not s:
        return s
    if s.strip() in LIBELLES:
        return s.replace(s.strip(), LIBELLES[s.strip()])
    morceaux = [(s, False)]                      # (texte, deja traduit)
    for fr, en in _entrees():
        suivants = []
        for texte, fige in morceaux:
            if fige or fr not in texte:
                suivants.append((texte, fige))
                continue
            parts = texte.split(fr)
            for i, p in enumerate(parts):
                if i:
                    suivants.append((en, True))
                if p:
                    suivants.append((p, False))
        morceaux = suivants
    # Les etiquettes ne s'appliquent qu'aux portions non encore traduites : une
    # phrase deja rendue en anglais n'est pas reexaminee mot a mot.
    sortie = []
    for texte, fige in morceaux:
        if not fige:
            for fr, en in ETIQUETTES.items():
                if fr != en:
                    texte = re.sub(r"(?<![\w-])%s(?![\w-])" % re.escape(fr), en, texte)
        sortie.append(texte)
    return "".join(sortie)


def traduire(obj, langue="en"):
    if langue == "fr":
        return obj
    if isinstance(obj, str):
        return traduire_texte(obj, langue)
    if isinstance(obj, list):
        return [traduire(x, langue) for x in obj]
    if isinstance(obj, dict):
        return {k: (v if k in ("code", "canon", "message_ghc", "message", "texte_generalisation")
                    else traduire(v, langue)) for k, v in obj.items()}
    return obj


def catalogue_json():
    """Le catalogue, pour que les clients traduisent leurs propres libelles."""
    return {"phrases": CATALOGUE, "etiquettes": ETIQUETTES, "libelles": LIBELLES}
