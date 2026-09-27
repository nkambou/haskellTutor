"""Serveur de HaskellTutor : deux applications sur un meme noyau.

    python3 serveur.py            puis http://localhost:8080  (apprenant)
                                       http://localhost:8080/enseignant

Bibliotheque standard uniquement. GHC doit etre installe : les soumissions sont
reellement compilees et testees.
"""

import json, os, datetime, urllib.parse
import os, sys
_ICI = os.path.dirname(os.path.abspath(__file__))
if _ICI not in sys.path:
    sys.path.insert(0, _ICI)
from http.server import BaseHTTPRequestHandler, HTTPServer

import noyau as K
import textes as TX

ICI = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8080"))

FAMILLES_EXECUTABLES = set(K.ACTIVITES)

DEFAUT_CONTRAT = {"assistance": "on-request", "abstraction": "discovery", "regime": "free",
                  "sequence": "free", "delai_minutes": 0,
                  "off_form": "explain_and_continue",
                  "verification": "on-doubt"}
VALEURS = {"assistance": ["none", "on-request", "guidance"],
           "abstraction": ["discovery", "guided", "exposed"],
           "regime": ["free", "solo", "pair", "team"],
           "sequence": ["free", "must-complete"],
           "off_form": ["explain_and_rewrite", "explain_and_continue", "confront"],
           "verification": ["never", "on-doubt", "always"]}


def ref():
    return K.referentiel()


# ------------------------------------------------------------------ contrats

def contrat(e, cid):
    c = dict(DEFAUT_CONTRAT)
    c.update(e.get("contrats", {}).get(cid, {}))
    return c


def plafond_aide(e, cid):
    return 0 if contrat(e, cid)["assistance"] == "none" else K.NIVEAUX_MAX


def cle_aide(cid, activite):
    return "%s/%s" % (cid, activite or "abstraction")


# ------------------------------------------------------------------ parcours

def concept_courant(r, ap):
    for cid in K.concepts_ouverts(r, ap["etats"]):
        c, _ = K.concept(r, cid)
        if c["famille"] in FAMILLES_EXECUTABLES:
            return cid
    return None


def amorcer(r, ap):
    for p in r["paliers"]:
        for c in p["concepts"]:
            if c["famille"] not in FAMILLES_EXECUTABLES:
                ap["etats"].setdefault(c["id"], "acquired")


def carte(r, ap):
    out = []
    for p in r["paliers"]:
        cs = []
        for c in p["concepts"]:
            etat = ap["etats"].get(c["id"], "verrou")
            if etat != "acquired" and all(ap["etats"].get(x) == "acquired" for x in c["prerequis"]):
                etat = ap["etats"].get(c["id"], "instances")
                if etat == "instances":
                    etat = "%d instance(s)" % len(ap["corpus"].get(c["id"], []))
            cs.append({"id": c["id"], "libelle": c["libelle"], "etat": etat,
                       "executable": c["famille"] in FAMILLES_EXECUTABLES})
        out.append({"palier": p["id"], "titre": p["titre"], "concepts": cs})
    return out


# ------------------------------------------------------------------ groupes

def mode_groupes(r, e):
    """Mode autorise par l'administrateur dans le referentiel, ajuste par l'enseignant."""
    g = dict(r.get("groupes", {}))
    g.update(e.get("groupes_reglages", {}))
    return g


def groupe_de(e, ident, cid):
    for gid, g in e.get("groupes", {}).items():
        if g["concept"] == cid and ident in g["membres"]:
            return dict(g, id=gid)
    return None


def pairs_eligibles(e, ap, cid):
    """Auto-organisation bornee : seuls les pairs au meme etat sur le concept vise."""
    mien = ap["etats"].get(cid, "instances")
    out = []
    for ident, autre in e["apprenants"].items():
        if ident == ap["ident"] or autre["cohorte"] != ap["cohorte"]:
            continue
        if autre["etats"].get(cid, "instances") != mien:
            continue
        out.append({"ident": ident, "nom": autre["nom"], "etat": mien,
                    "disponible": groupe_de(e, ident, cid) is None})
    return out


def former_groupe(e, ap, cid, invites, mode):
    membres = [ap["ident"]] + [i for i in invites if i in e["apprenants"]]
    gid = "g%d" % (len(e.get("groupes", {})) + 1)
    e.setdefault("groupes", {})[gid] = {
        "concept": cid, "membres": membres,
        "statut": "valide" if mode == "auto" else "en attente",
        "cree": datetime.datetime.now().isoformat(timespec="seconds"),
        "cohorte": ap["cohorte"]}
    return dict(e["groupes"][gid], id=gid)


def atelier(e, ap, cid):
    """Consolidation : les generalisations reellement produites par le groupe."""
    g = groupe_de(e, ap["ident"], cid)
    if not g or g["statut"] != "valide":
        return None
    lignes = []
    for m in g["membres"]:
        autre = e["apprenants"].get(m)
        if not autre:
            continue
        lignes.append({"nom": autre["nom"], "moi": m == ap["ident"],
                       "generalisation": autre.get("generalisations", {}).get(cid),
                       "etat": autre["etats"].get(cid, "instances")})
    pretes = [l for l in lignes if l["generalisation"]]
    return {"groupe": g["id"], "membres": lignes, "pretes": len(pretes),
            "ouvert": len(pretes) == len(lignes) and len(lignes) > 1}


# ------------------------------------------------------------------ vue

def vue_apprenant(r, e, ap):
    cid = concept_courant(r, ap)
    c, pal = K.concept(r, cid) if cid else (None, None)
    corpus = ap["corpus"].get(cid, []) if cid else []
    ct = contrat(e, cid) if cid else DEFAUT_CONTRAT
    decision, motif = (K.decider(r, ap, cid) if cid
                       else ("fin", "tous les concepts executables sont acquis"))

    vue = {"ident": ap["ident"], "nom": ap["nom"], "cohorte": ap["cohorte"],
           "regime": ap["regime"], "concept": cid,
           "libelle": c["libelle"] if c else None,
           "palier": pal["titre"] if pal else None,
           "famille": c["famille"] if c else None,
           "etat": ap["etats"].get(cid, "instances") if cid else None,
           "corpus": [x["nom"] for x in corpus],
           "ecartes": ap["ecartes"].get(cid, []),
           "reemplois": ap["reemplois"].get(cid, 0),
           "decision": decision, "motif": motif,
           "carte": carte(r, ap), "contrat": ct,
           "aides_max": plafond_aide(e, cid) if cid else 0,
           "generalisation": ap.get("generalisations", {}).get(cid)}

    if cid:
        gen = c.get("generalisation")
        attendu = gen["points_de_variation_attendus"] if gen else None
        pts, forme, blocs = (K.compte_alignement(r, c["famille"],
                                                 [(x["nom"], x["code"]) for x in corpus])
                             if len(corpus) >= 2 else (0, None, 0))
        vue["progres"] = {
            "solutions": len(corpus), "minimum": r["reglages"]["instances_min"],
            "maximum": r["reglages"]["instances_max"],
            "points": pts, "attendu": attendu,
            "stable": K.est_stable(ap, cid),
            "etat": ap["etats"].get(cid, "instances"),
            "reemplois": ap["reemplois"].get(cid, 0),
            "reemplois_requis": r["reglages"]["reemploi_requis"],
            "ecartees": len(ap["ecartes"].get(cid, [])),
            "resolutions": ap.get("resolutions", {}).get(cid, 0),
            "objectif": ("écrire assez de solutions comparables, y trouver ce qu'elles "
                         "ont en commun, puis l'employer sans y être invité"
                         if gen else "pratiquer jusqu'à ce que la forme soit acquise")}
        vue["consigne_forme"] = ap.get("consignes", {}).get(cid)
        vue["politique_hors_forme"] = ct.get("off_form", "explain_and_continue")
        vue["solutions"] = [{"activite": x["nom"], "code": x["code"],
                             "forme": x.get("canon"), "statut": "au dossier"}
                            for x in corpus] + \
                           [{"activite": x[0], "code": x[2] if len(x) > 2 else None,
                             "forme": None, "statut": "hors forme : " + x[1]}
                            for x in ap["ecartes"].get(cid, [])]

    if decision == "next_tier":
        ap["etats"][cid] = "acquired"
        return vue_apprenant(r, e, ap)

    if decision in ("instance", "reuse"):
        pool = "instances" if decision == "instance" else "reemplois"
        cle = cid if pool == "instances" else cid + "@reemploi"
        a = K.prochaine_activite(c["famille"], set(ap["servis"].get(cle, [])), pool)
        if a:
            vue["activite"] = {"id": a[0], "enonce": a[1], "signature": a[2], "amorce": a[3]}
        else:
            vue["activite"] = None
            vue["decision"] = decision = "guidance"
            vue["motif"] = "plus d'ancrage disponible dans la famille"

    if decision in ("abstraction", "guidance") and corpus:
        al = K.alignement_affichable(corpus, r, c["famille"])
        al["mode"] = ct["abstraction"] if decision == "abstraction" else "guided"
        al["guide"] = decision == "guidance"
        if al["mode"] == "exposed":
            al["squelette"] = K.squelette(al["forme"])
        vue["abstraction"] = al

    if cid and vue.get("activite"):
        cle = cle_aide(cid, vue["activite"]["id"])
        debuts = ap.setdefault("debuts", {})
        if cle not in debuts:
            debuts[cle] = datetime.datetime.now().isoformat(timespec="seconds")
        vue["debut"] = debuts[cle]
        d = int(ct.get("delai_minutes") or 0)
        if d:
            ecoule = (datetime.datetime.now()
                      - datetime.datetime.fromisoformat(debuts[cle])).total_seconds()
            vue["reste_secondes"] = int(max(0, d * 60 - ecoule))

    if cid:
        vue["preferences"] = ap.get("preferences", {"avance": "auto"})
        vue["sequence"] = ct.get("sequence", "free")
        vue["delai_minutes"] = int(ct.get("delai_minutes") or 0)
        vue["peut_quitter"] = (ct.get("sequence", "free") == "free"
                               or ap["etats"].get(cid) == "acquired")
        vue["suspendu"] = bool(ap.get("suspendu"))
        k = cle_aide(cid, vue["activite"]["id"] if vue.get("activite") else None)
        vue["aides_prises"] = ap.get("aides", {}).get(k, 0)
        vue["echecs"] = ap.get("echecs", {}).get(k, 0)
        vue["aide_proposee"] = (ct["assistance"] == "guidance" and vue["echecs"] >= 2
                                and vue["aides_prises"] < vue["aides_max"])
        vue["groupe"] = groupe_de(e, ap["ident"], cid)
        vue["mode_groupes"] = mode_groupes(r, e)
        vue["collaboration_requise"] = ct["regime"] in ("pair", "team")
        if ap["etats"].get(cid) == "generalised":
            vue["atelier"] = atelier(e, ap, cid)
    return vue


# ------------------------------------------------------------------ api

def e_etat_courant():
    return K.charger_etat()


def langue_de(params, corps):
    """Cette distribution est unilingue anglaise."""
    return "en"


def api(chemin, params, corps):
    _lang = langue_de(params, corps)
    if chemin == "/api/textes":
        return TX.catalogue_json()
    rep = _api(chemin, params, corps)
    return TX.traduire(rep, _lang)


def _api(chemin, params, corps):
    e = K.charger_etat()
    r = ref()

    def fin(v):
        K.sauver_etat(e)
        return v

    if chemin == "/api/version":
        return {"version": K.VERSION,
                "routes": ["etat", "regime", "soumettre", "generalisation", "aide",
                           "pairs", "groupe", "familles", "contrats", "reglages",
                           "groupes", "cohorte", "activites", "journal"]}

    if chemin == "/api/inscription":
        ap = K.nouvel_apprenant(corps["nom"], corps["cohorte"])
        ap["regime"] = corps.get("regime", "solo")
        amorcer(r, ap)
        e["apprenants"][ap["ident"]] = ap
        return fin({"ident": ap["ident"]})

    if chemin == "/api/etat":
        return fin(vue_apprenant(r, e, e["apprenants"][params["ident"][0]]))

    if chemin == "/api/regime":
        ap = e["apprenants"][corps["ident"]]
        ap["regime"] = corps["regime"]
        return fin(vue_apprenant(r, e, ap))

    if chemin == "/api/soumettre":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        c, _ = K.concept(r, cid)
        gen = ap["etats"].get(cid) == "generalised"
        pool = K.REEMPLOIS if gen else K.ACTIVITES
        cle = cid + "@reemploi" if gen else cid
        act = next(a for a in pool[c["famille"]] if a[0] == corps["activite"])
        verdict = K.evaluer(corps["code"], act[4])
        categorie = K.categoriser(verdict)
        ct = contrat(e, cid)
        d = int(ct.get("delai_minutes") or 0)
        debut = ap.get("debuts", {}).get(cle_aide(cid, act[0]))
        hors = False
        if d and debut:
            hors = ((datetime.datetime.now()
                     - datetime.datetime.fromisoformat(debut)).total_seconds() > d * 60)
        K.journaliser(ap, cid, act[0], r["familles"][c["famille"]].get("chapitre"),
                      verdict, categorie, hors)
        k = cle_aide(cid, act[0])
        if verdict["reussite"]:
            ap.setdefault("echecs", {})[k] = 0
        else:
            ap.setdefault("derniere_erreur", {})[k] = categorie
            ap.setdefault("echecs", {})[k] = ap.get("echecs", {}).get(k, 0) + 1
        rep = {"verdict": verdict, "hors_delai": hors}
        if not verdict["reussite"]:
            rep["tuteur"] = {"ton": "echec", "texte": K.lecture(categorie),
                             "categorie": categorie,
                             "invite": ("Vous pouvez demander un etayage : trois niveaux, "
                                        "aucun ne donne la solution.")}
        if verdict["reussite"]:
            deja = act[0] in ap["servis"].get(cle, [])
            if gen:
                if not deja:
                    ap["servis"].setdefault(cle, []).append(act[0])
                emploie = K.schema_employe(act[0], corps["code"])
                if emploie:
                    ap["reemplois"][cid] = ap["reemplois"].get(cid, 0) + 1
                rep["reuse"] = {"schema_employe": emploie,
                                   "compte": ap["reemplois"].get(cid, 0)}
            else:
                adm = K.admettre(act[0], corps["code"], c["famille"], verdict)
                rep["admission"] = adm
                politique = ct.get("off_form", "explain_and_continue")
                if not adm["admis"]:
                    kk = cle_aide(cid, act[0])
                    n_hf = ap.setdefault("hors_forme_suite", {}).get(kk, 0) + 1
                    ap["hors_forme_suite"][kk] = n_hf
                    if politique == "explain_and_rewrite" and n_hf >= 2:
                        politique = "explain_and_continue"
                        rep["desescalade"] = True
                    # la reussite est reelle : elle est comptee a part, jamais perdue
                    ap.setdefault("resolutions", {})[cid] = \
                        ap.get("resolutions", {}).get(cid, 0) + 1
                    ap.setdefault("ecartes", {}).setdefault(cid, []).append(
                        [act[0], adm["motif"], corps["code"]])
                    if politique != "explain_and_rewrite" and not deja:
                        ap["servis"].setdefault(cle, []).append(act[0])
                    ap.setdefault("consignes", {})[cid] = politique
                    rep["off_form"] = {"politique": politique, "motif": adm["motif"]}
                    rep["tuteur"] = {
                        "ton": "off_form",
                        "texte": K.commentaire_hors_forme(
                            adm["motif"], politique,
                            ap["resolutions"].get(cid, 1))}
                    rep["etat"] = vue_apprenant(r, e, ap)
                    return fin(rep)
                if not deja:
                    ap["servis"].setdefault(cle, []).append(act[0])
                ap.setdefault("hors_forme_suite", {}).pop(cle_aide(cid, act[0]), None)
                corpus = ap["corpus"].setdefault(cid, [])
                anciennes = [x for x in corpus if x["nom"] == act[0]]
                entree = {"nom": act[0], "code": corps["code"], "canon": adm["canon"]}
                if anciennes:
                    corpus[corpus.index(anciennes[0])] = entree
                    rep["revision"] = True
                else:
                    corpus.append(entree)
                ap.get("consignes", {}).pop(cid, None)
                mode_v = ct.get("verification", "on-doubt")
                if mode_v != "never":
                    secondes = None
                    if debut:
                        secondes = (datetime.datetime.now()
                                    - datetime.datetime.fromisoformat(debut)).total_seconds()
                    signaux = K.signaux_de_doute(
                        secondes, ap.get("echecs", {}).get(k, 0),
                        ap.get("aides", {}).get(k, 0), corps["code"])
                    if mode_v == "always" or signaux:
                        qs = K.questions_sur(act[0], corps["code"])
                        if qs:
                            ap.setdefault("verifications", {})[k] = {
                                "activite": act[0], "questions": qs,
                                "signaux": signaux, "statut": "en attente"}
                            rep["verification"] = {"questions": [
                                {"id": q["id"], "question": q["question"],
                                 "options": q["options"]} for q in qs]}
                gen2 = c.get("generalisation")
                att = gen2["points_de_variation_attendus"] if gen2 else None
                pts = (K.compte_alignement(r, c["famille"],
                                           [(x["nom"], x["code"]) for x in corpus])[0]
                       if len(corpus) >= 2 else 0)
                rep["tuteur"] = {
                    "ton": "reussite",
                    "texte": K.commentaire_reussite(
                        len(corpus), r["reglages"]["instances_min"], pts, att,
                        K.est_stable(ap, cid),
                        adm["admis"], adm.get("motif", ""))}
        rep["etat"] = vue_apprenant(r, e, ap)
        return fin(rep)

    if chemin == "/api/refus_atelier":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        c, _ = K.concept(r, cid)
        ap.setdefault("refus_atelier", {})[cid] = \
            ap.get("refus_atelier", {}).get(cid, 0) + 1
        K.journaliser(ap, cid, "", r["familles"][c["famille"]].get("chapitre"),
                      {"reussite": True, "compile": True, "message": ""},
                      "refus-atelier")
        return fin({"message": "Une activite de plus vous est servie.",
                    "etat": vue_apprenant(r, e, ap)})

    if chemin == "/api/generalisation":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        texte = (corps.get("texte") or "").strip()
        if not texte:
            return {"refus": "Ecrivez votre definition avant de valider la remontee."}
        ap.setdefault("generalisations", {})[cid] = texte
        ap["etats"][cid] = "generalised"
        ap["reemplois"].setdefault(cid, 0)
        return fin(vue_apprenant(r, e, ap))

    if chemin == "/api/reprendre":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        c, _ = K.concept(r, cid)
        nom = corps["activite"]
        act = next((a for a in K.ACTIVITES.get(c["famille"], []) if a[0] == nom), None)
        if not act:
            act = next((a for a in K.REEMPLOIS.get(c["famille"], []) if a[0] == nom), None)
        if not act:
            return {"refus": "activite inconnue"}
        ancienne = next((x["code"] for x in ap["corpus"].get(cid, []) if x["nom"] == nom), None)
        if ancienne is None:
            ancienne = next((x[2] for x in ap.get("ecartes", {}).get(cid, [])
                             if x[0] == nom and len(x) > 2), None)
        return {"activite": {"id": act[0], "enonce": act[1], "signature": act[2],
                             "amorce": ancienne or act[3]},
                "reprise": True}

    if chemin == "/api/preference":
        ap = e["apprenants"][corps["ident"]]
        ap.setdefault("preferences", {})["avance"] = corps.get("avance", "auto")
        return fin(vue_apprenant(r, e, ap))

    if chemin == "/api/seance":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        ct = contrat(e, cid) if cid else DEFAUT_CONTRAT
        if corps.get("action") == "quitter":
            if ct.get("sequence") == "must-complete" and ap["etats"].get(cid) != "acquired":
                return {"refus": "Votre enseignant demande de terminer la sequence sur ce "
                                 "concept avant de quitter la seance."}
            ap["suspendu"] = True
        else:
            ap["suspendu"] = False
        return fin(vue_apprenant(r, e, ap))

    if chemin == "/api/verifier":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        c, _ = K.concept(r, cid)
        k = cle_aide(cid, corps["activite"])
        v = ap.get("verifications", {}).get(k)
        if not v:
            return {"refus": "aucune verification en attente"}
        justes = 0
        retours = []
        for q in v["questions"]:
            donnee = (corps.get("reponses") or {}).get(q["id"])
            ok = donnee == q["reponse"]
            justes += 1 if ok else 0
            retours.append({"id": q["id"], "correct": ok, "suite": q["suite"]})
        v["statut"] = "expliquee" if justes == len(v["questions"]) else "non expliquee"
        v["justes"] = justes
        K.journaliser(ap, cid, corps["activite"],
                      r["familles"][c["famille"]].get("chapitre"),
                      {"reussite": v["statut"] == "expliquee", "compile": True,
                       "message": ""},
                      "verification-" + v["statut"].replace(" ", "-"))
        return fin({"statut": v["statut"], "justes": justes,
                    "total": len(v["questions"]), "retours": retours,
                    "message": ("Merci : votre explication correspond a ce que votre code "
                                "fait." if v["statut"] == "expliquee" else
                                "Votre reponse ne correspond pas a ce que votre code fait. "
                                "La solution reste enregistree ; reprenez-la si vous "
                                "voulez, et demandez un etayage au besoin."),
                    "etat": vue_apprenant(r, e, ap)})

    if chemin == "/api/pourquoi":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        c, _ = K.concept(r, cid)
        K.journaliser(ap, cid, corps.get("activite") or "—",
                      r["familles"][c["famille"]].get("chapitre"),
                      {"reussite": False, "compile": True, "message": ""},
                      "explication-forme")
        return fin({"texte": K.pourquoi(c["famille"])})

    if chemin == "/api/aide":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        c, _ = K.concept(r, cid)
        contexte = corps.get("contexte", "activite")
        activite = corps.get("activite")
        cle = cle_aide(cid, activite if contexte == "activite" else None)
        nmax = plafond_aide(e, cid)
        if nmax == 0:
            return {"refus": "L'enseignant a ferme l'assistance sur ce concept.",
                    "niveau": 0, "sur": 0}
        niveau = ap.setdefault("aides", {}).get(cle, 0) + 1
        categorie = ap.get("derniere_erreur", {}).get(cle_aide(cid, activite), "none")
        if niveau > nmax:
            return {"refus": "Vous avez pris les %d niveaux d'etayage prevus. "
                             "Le tuteur ne va pas plus loin : la suite vous appartient." % nmax,
                    "niveau": nmax, "sur": nmax,
                    "rappel": [K.aide(c["famille"], categorie, x, contexte)
                               for x in range(1, nmax + 1)]}
        texte = K.aide(c["famille"], categorie, niveau, contexte)
        ap["aides"][cle] = niveau
        K.journaliser(ap, cid, activite or "abstraction",
                      r["familles"][c["famille"]].get("chapitre"),
                      {"reussite": False, "compile": True, "message": ""},
                      "aide-niveau-%d" % niveau)
        return fin({"niveau": niveau, "sur": nmax, "texte": texte, "fonde_sur": categorie})

    # ---------------- groupes, cote apprenant

    if chemin == "/api/pairs":
        ap = e["apprenants"][params["ident"][0]]
        cid = concept_courant(r, ap)
        return {"pairs": pairs_eligibles(e, ap, cid), "mode": mode_groupes(r, e),
                "concept": cid, "groupe": groupe_de(e, ap["ident"], cid)}

    if chemin == "/api/groupe":
        ap = e["apprenants"][corps["ident"]]
        cid = concept_courant(r, ap)
        mode = mode_groupes(r, e)
        if corps.get("action") == "quitter":
            g = groupe_de(e, ap["ident"], cid)
            if g:
                e["groupes"][g["id"]]["membres"].remove(ap["ident"])
                if not e["groupes"][g["id"]]["membres"]:
                    del e["groupes"][g["id"]]
            return fin({"etat": vue_apprenant(r, e, ap)})
        if mode.get("formation") == "enseignant":
            return {"refus": "La composition des groupes est reservee a l'enseignant."}
        invites = corps.get("invites", [])
        if not (mode["taille_min"] - 1 <= len(invites) <= mode["taille_max"] - 1):
            return {"refus": "Un groupe compte de %d a %d membres."
                             % (mode["taille_min"], mode["taille_max"])}
        g = former_groupe(e, ap, cid, invites, mode.get("formation"))
        return fin({"groupe": g, "etat": vue_apprenant(r, e, ap)})

    # ---------------- cote enseignant

    if chemin == "/api/familles":
        return {"familles": K.etat_des_familles(r), "reglages": r["reglages"],
                "groupes": mode_groupes(r, e)}

    if chemin == "/api/contrats":
        if corps:
            if corps.get("tous"):
                for p in r["paliers"]:
                    for c in p["concepts"]:
                        actuel = dict(DEFAUT_CONTRAT)
                        actuel.update(e.get("contrats", {}).get(c["id"], {}))
                        actuel.update(corps["contrat"])
                        e.setdefault("contrats", {})[c["id"]] = actuel
            elif corps.get("reinitialiser"):
                e.get("contrats", {}).pop(corps["concept"], None)
            else:
                e.setdefault("contrats", {})[corps["concept"]] = corps["contrat"]
            K.sauver_etat(e)
        concepts = []
        for p in r["paliers"]:
            for c in p["concepts"]:
                concepts.append({"id": c["id"], "libelle": c["libelle"], "palier": p["id"],
                                 "famille": c["famille"],
                                 "executable": c["famille"] in FAMILLES_EXECUTABLES,
                                 "abstraction": bool(c.get("generalisation"))})
        return {"concepts": concepts, "contrats": e.get("contrats", {}),
                "defaut": DEFAUT_CONTRAT, "valeurs": VALEURS,
                "niveaux_aide": K.NIVEAUX_MAX}

    if chemin == "/api/reglages":
        if corps:
            e.setdefault("groupes_reglages", {}).update(corps.get("groupes", {}))
            K.sauver_etat(e)
        return {"referentiel": r.get("groupes", {}), "effectif": mode_groupes(r, e),
                "reglages_parcours": r["reglages"]}

    if chemin == "/api/groupes":
        if corps and corps.get("groupe"):
            gid = corps["groupe"]
            if corps["action"] == "valider":
                e["groupes"][gid]["statut"] = "valide"
            elif corps["action"] == "refuser":
                e["groupes"][gid]["statut"] = "refuse"
            elif corps["action"] == "dissoudre":
                del e["groupes"][gid]
            K.sauver_etat(e)
        if corps and corps.get("action") == "composer":
            mode = mode_groupes(r, e)
            restants = {}
            for ident, ap in e["apprenants"].items():
                cid = concept_courant(r, ap)
                if cid and not groupe_de(e, ident, cid):
                    cle = (cid, ap["etats"].get(cid, "instances"), ap["cohorte"])
                    restants.setdefault(cle, []).append(ident)
            formes = 0
            for (cid, _etat, cohorte), gens in restants.items():
                taille = mode["taille_max"]
                for k in range(0, len(gens), taille):
                    lot = gens[k:k + taille]
                    if len(lot) < mode["taille_min"]:
                        continue
                    gid = "g%d" % (len(e.get("groupes", {})) + 1)
                    e.setdefault("groupes", {})[gid] = {
                        "concept": cid, "membres": lot, "statut": "valide",
                        "cree": datetime.datetime.now().isoformat(timespec="seconds"),
                        "cohorte": cohorte, "origine": "attribution d'office"}
                    formes += 1
            K.sauver_etat(e)
        gs = [dict(g, id=gid, noms=[e["apprenants"][m]["nom"] for m in g["membres"]
                                    if m in e["apprenants"]])
              for gid, g in e.get("groupes", {}).items()]
        sans = []
        for ident, ap in e["apprenants"].items():
            cid = concept_courant(r, ap)
            if cid and not groupe_de(e, ident, cid):
                sans.append({"ident": ident, "nom": ap["nom"], "concept": cid,
                             "etat": ap["etats"].get(cid, "instances")})
        return {"groupes": gs, "sans_groupe": sans}

    if chemin == "/api/cohorte":
        lignes = []
        for ident, ap in e["apprenants"].items():
            for p in r["paliers"]:
                for c in p["concepts"]:
                    if c["famille"] in FAMILLES_EXECUTABLES:
                        lignes.append({
                            "apprenant": ap["nom"], "ident": ident, "concept": c["id"],
                            "etat": ap["etats"].get(c["id"], "instances"),
                            "instances": len(ap["corpus"].get(c["id"], [])),
                            "ecartes": len(ap["ecartes"].get(c["id"], [])),
                            "aides": sum(v for k, v in ap.get("aides", {}).items()
                                         if k.startswith(c["id"] + "/")),
                            "non_expliquees": sum(
                                1 for k, v in ap.get("verifications", {}).items()
                                if k.startswith(c["id"] + "/") and v.get("statut") == "non expliquee"),
                            "generalisation": ap.get("generalisations", {}).get(c["id"])})
        return {"lignes": lignes, "apprenants": len(e["apprenants"])}

    if chemin == "/api/activites":
        out = []
        for fam, actes in K.ACTIVITES.items():
            for a in actes:
                out.append({"famille": fam, "pool": "instances", "id": a[0],
                            "enonce": a[1], "signature": a[2], "tests": len(a[4])})
        for fam, actes in K.REEMPLOIS.items():
            for a in actes:
                out.append({"famille": fam, "pool": "reemplois", "id": a[0],
                            "enonce": a[1], "signature": a[2], "tests": len(a[4])})
        return {"activites": out,
                "familles_sans_activites": [f for f in r["familles"] if f not in K.ACTIVITES]}

    if chemin == "/api/releves":
        import releves as RL
        journal = RL.lire_journal(K.JOURNAL) if os.path.exists(K.JOURNAL) else []
        chapitres = []
        for ch in sorted(RL.CATALOGUE):
            ag = RL.agreger(journal, ch)
            if not ag["soumissions"]:
                continue
            dom, n = (ag["par_categorie"].most_common(1) or [("—", 0)])[0]
            chapitres.append({
                "chapitre": ch, "soumissions": ag["soumissions"], "erreurs": ag["erreurs"],
                "apprenants": ag["apprenants"],
                "taux": round(100.0 * ag["erreurs"] / ag["soumissions"]),
                "dominante": ag["libelles"].get(dom, dom), "occurrences": n,
                "detail": [{"categorie": c, "libelle": ag["libelles"].get(c, c),
                            "n": k, "touches": ag["touches"].get(c, 0),
                            "silencieuse": c in RL.SILENCIEUSES}
                           for c, k in ag["par_categorie"].most_common()]})
        return {"chapitres": chapitres, "total": len(journal)}

    if chemin == "/api/journal":
        entrees = []
        if os.path.exists(K.JOURNAL):
            with open(K.JOURNAL, encoding="utf-8") as f:
                for ligne in f:
                    if ligne.strip():
                        entrees.append(json.loads(ligne))
        qui = (params or {}).get("ident", [None])[0]
        if qui:
            entrees = [x for x in entrees if x.get("apprenant") == qui]
        return {"total": len(entrees), "dernieres": entrees[-30:]}

    return {"erreur": "route inconnue : " + chemin}


# ------------------------------------------------------------------ http

class Handler(BaseHTTPRequestHandler):
    def _envoyer(self, code, contenu, mime="application/json"):
        d = contenu if isinstance(contenu, bytes) else contenu.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def _fichier(self, nom):
        p = os.path.join(ICI, nom)
        if not os.path.exists(p):
            return self._envoyer(404, "introuvable : " + nom, "text/plain")
        with open(p, "rb") as f:
            self._envoyer(200, f.read(), "text/html")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._fichier("etudiant.html")
        if u.path == "/enseignant":
            return self._fichier("enseignant.html")
        if u.path.endswith(".html") and "/" not in u.path[1:]:
            return self._fichier(u.path[1:])
        if u.path.startswith("/api/"):
            try:
                return self._envoyer(200, json.dumps(
                    api(u.path, urllib.parse.parse_qs(u.query), None), ensure_ascii=False))
            except Exception as exc:
                return self._envoyer(500, json.dumps({"erreur": str(exc)}))
        return self._envoyer(404, "introuvable", "text/plain")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        corps = json.loads(self.rfile.read(n) or b"{}")
        try:
            return self._envoyer(200, json.dumps(api(u.path, {}, corps), ensure_ascii=False))
        except Exception as exc:
            return self._envoyer(500, json.dumps({"erreur": str(exc)}))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("HaskellTutor sur http://localhost:%d" % PORT)
    print("  apprenant  : http://localhost:%d/" % PORT)
    print("  enseignant : http://localhost:%d/enseignant" % PORT)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
