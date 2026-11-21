#!/usr/bin/env python3
"""Publie le contrat Linxea Spirit 2, CHIFFRÉ, pour l'app iPhone « Mon Spirit 2 ».

À appeler par « Suivi finances » après chaque récupération du contrat Linxea :

    from publier_spirit2 import publier
    publier(contrat)            # contrat = dict au format Mon Spirit 2

ou en ligne de commande :

    python publier_spirit2.py contrat.json      (ou le JSON sur l'entrée standard)
    python publier_spirit2.py --init            (crée la phrase secrète et le Gist, affiche le lien)
    python publier_spirit2.py --infos           (réaffiche le lien et la phrase secrète)

Ce script ne contient aucune donnée personnelle. La phrase secrète, le jeton GitHub
et l'identifiant du Gist sont rangés HORS de tout dépôt, dans :
    Windows : %APPDATA%\\SpiritSync\\config.json
    autres  : ~/.config/spirit-sync/config.json
Seul le contenu chiffré (AES-256-GCM, clé PBKDF2-SHA256 200 000 itérations) quitte le PC.

Dépendance : pip install cryptography
"""
import base64, json, os, secrets, sys, urllib.request, urllib.error
from datetime import date

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITER = 200_000
FICHIER = "spirit2.json"

# Mots courts sans accents ni majuscules, faciles à saisir sur iPhone (512 mots : 9 bits par mot).
MOTS = """abeille abri acier actif adorer agile aigle aimer air algue allure alpage ambre ami ancre angle anis antre
appel arbre arche argile arome art astre atlas aube audace auge aurore autel avion azur badge bague baie
baleine balise bambou banane banc bandit banjo barbe barque bassin bateau baume bazar beige berger beton beurre
biche bijou bille biscuit bison blason bleu bloc bocal boheme bois bolide bonbon bonnet bord bosquet botte
boucle bougie boule bourse boussole bouton brebis brise brosse brume bruyere bulle bureau buste cabane cacao
cactus cadeau cadran cahier caillou calme camion canal canard canot cantine cape caramel carte cascade casque castor
cave cedre cerf cerise chalet chamois chant chapeau charbon chardon chat chemin chene cheval chevre chiffre
cidre ciel cigale cirque citron clairon clef clocher clou cobalt cocon colline comete compas comptoir conte
copain coquille corail corde cornet coton coucou coude coupole courage cousin crabe craie crayon creme creux
crocus cuivre cumin cygne dague dahlia danse dauphin delta desert dessin diamant digue dindon disque divan
domino donjon douane dragon drapeau dune duvet eau ebene echelle eclair ecorce ecran ecume email emeraude
encre enigme envol epice epi erable escale espoir etoile etang etoffe facteur faucon fenetre fer feuille
fiable figue filet flamme fleche fleur flocon flute foin fontaine forge foret fougere four fraise framboise
frene fromage fruit fumee fusee galet gamme garage gateau gazon gecko geste girafe givre glace gland globe
gomme gondole gorille goutte grain grange grappe grenier griffe grille grotte groseille guitare hamac hameau
harpe hautbois herbe heron hibou hiver homard horloge hublot humour huppe icone igloo ile indigo iris ivoire
jade jardin jasmin jeton jockey jonc journal joyau judo jungle jupe kayak kimono kiwi koala laine lagune
lama lampe lanterne lapin laser laurier lavande lecture legume lezard liane lierre lilas limace lime linge
lion litchi livre loge losange loupe loutre lucarne lune lutin luxe lynx macaron magie maison malle mammouth
manche mangue manoir marais marche marmotte marron masque matin mauve melodie melon menthe merle meteore miel
mimosa miroir moineau montagne morse mouette moulin mousse mouton muguet mulot muse musique myrtille nacre
nappe navire nectar neige nenuphar nid noisette noix nomade nougat nuage oasis ocean ocre odeur oeillet
olive ombre onde opale orage orange orchidee orge orgue ortie osier otarie ouragan ours outil ovale pagaie
paille palme panda panier papier papillon parc pastel patin paume pavot pecheur pelican pelle pepite perle
persil phare piano pierre pigeon pilote piment pin pinceau pirate piste pivoine plage planche platane plume
poire pois poivre pollen pomme pont potager poulpe poutre prairie prisme prune puits pupitre quai quartz
quille racine radar radis raisin rameau rampe ravin rayon recif refuge regard renard requin rivage riviere
robot roche roseau rouet rubis ruche ruisseau sable sabot safran salade sapin satin saule sauge savane
savon scarabee sentier serpent sirop soleil sorbet souris sphinx spirale studio sucre sureau tablier tambour
tango tapis tartine taupe theiere thym tigre tilleul tipi tisane toile tomate tonneau topaze torche tortue
toucan toupie tour trefle tresor tribu tulipe tunnel turban urne vague vallon vanille velours vent verger
vernis vigne village violon vitrail voile volcan voyage wagon yaourt yeti zebre zenith zeste zinc""".split()


# ---------- configuration locale (hors dépôt) ----------
def dossier_config():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "SpiritSync" if os.environ.get("APPDATA") else "spirit-sync")


def chemin_config():
    return os.environ.get("SPIRIT_SYNC_CONFIG") or os.path.join(dossier_config(), "config.json")


def lire_config():
    try:
        with open(chemin_config(), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def ecrire_config(cfg):
    p = chemin_config()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def nouvelle_phrase(n=7):
    mots = sorted(set(MOTS))
    assert len(mots) >= 512, len(mots)
    return " ".join(secrets.choice(mots) for _ in range(n))  # 7 mots ≈ 63 bits


def phrase_secrete(cfg):
    if not cfg.get("passphrase"):
        cfg["passphrase"] = nouvelle_phrase()
        ecrire_config(cfg)
    return cfg["passphrase"]


# ---------- chiffrement (compatible decryptPayload de spirit/index.html) ----------
def chiffrer(obj, passphrase, iterations=ITER):
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations).derive(passphrase.encode("utf-8"))
    clair = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    data = AESGCM(key).encrypt(iv, clair, None)  # texte chiffré + tag de 16 octets
    b = lambda x: base64.b64encode(x).decode("ascii")
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": iterations, "salt": b(salt), "iv": b(iv), "data": b(data)}


def dechiffrer(o, passphrase):
    salt, iv, data = (base64.b64decode(o[k]) for k in ("salt", "iv", "data"))
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=o.get("iter", ITER)).derive(passphrase.encode("utf-8"))
    return json.loads(AESGCM(key).decrypt(iv, data, None))


# ---------- contrôle du format ----------
def _date(s, ou):
    try:
        date.fromisoformat(s)
    except (TypeError, ValueError):
        raise ValueError(f"{ou} : date « {s} » invalide (attendu AAAA-MM-JJ)")


def valider(c, solde=None, tolerance=1.0):
    """Vérifie le format Mon Spirit 2 et, si `solde` est donné, que la somme des supports le retrouve."""
    if not isinstance(c, dict) or not isinstance(c.get("supports"), list) or not c["supports"]:
        raise ValueError("« supports » doit être une liste non vide")
    ct = c.get("contract") or {}
    if ct.get("openDate"):
        _date(ct["openDate"], "contract.openDate")
    total = 0.0
    for i, s in enumerate(c["supports"]):
        ou = f"supports[{i}] ({s.get('name', '?')})"
        if s.get("type") not in ("euro", "uc", "scpi"):
            raise ValueError(f"{ou} : type doit être euro, uc ou scpi")
        for k in ("units", "nav", "pru", "amount"):
            if not isinstance(s.get(k, 0), (int, float)):
                raise ValueError(f"{ou} : « {k} » doit être un nombre")
        if s["type"] != "euro" and s.get("units") and s.get("nav"):
            calc = s["units"] * s["nav"]
            if abs(calc - s.get("amount", 0)) > max(1.0, 0.005 * calc):
                raise ValueError(f"{ou} : amount {s.get('amount')} ≠ parts × VL = {calc:.2f}")
        total += float(s.get("amount", 0))
    for i, o in enumerate(c.get("operations") or []):
        _date(o.get("date"), f"operations[{i}]")
        if o.get("type") not in ("versement", "rachat", "arbitrage", "interets", "frais"):
            raise ValueError(f"operations[{i}] : type « {o.get('type')} » inconnu")
        if not isinstance(o.get("amount"), (int, float)):
            raise ValueError(f"operations[{i}] : « amount » doit être un nombre")
    for i, h in enumerate(c.get("history") or []):
        _date(h.get("date"), f"history[{i}]")
    if solde is not None and abs(total - float(solde)) > tolerance:
        raise ValueError(f"Somme des supports {total:.2f} € ≠ solde Linxea {float(solde):.2f} €")
    return round(total, 2)


# ---------- GitHub Gist ----------
def _api(method, path, token, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "spirit-sync",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub {method} {path} : HTTP {e.code} {e.read()[:300]!r}") from None


def jeton(cfg):
    t = os.environ.get("SPIRIT_GIST_TOKEN") or cfg.get("token")
    if not t:
        raise RuntimeError("Jeton GitHub manquant : lancez « python publier_spirit2.py --init ».")
    return t


def lien_raw(cfg):
    return f"https://gist.githubusercontent.com/{cfg['gist_user']}/{cfg['gist_id']}/raw/{FICHIER}"


def publier(contrat, solde=None):
    """Valide, chiffre et publie le contrat. Renvoie le lien raw à saisir sur l'iPhone."""
    valider(contrat, solde)
    cfg = lire_config()
    contenu = json.dumps(chiffrer(contrat, phrase_secrete(cfg)))
    tok = jeton(cfg)
    if cfg.get("gist_id"):
        _api("PATCH", f"/gists/{cfg['gist_id']}", tok, {"files": {FICHIER: {"content": contenu}}})
    else:
        g = _api("POST", "/gists", tok, {"description": "Mon Spirit 2 (chiffré)", "public": False,
                                         "files": {FICHIER: {"content": contenu}}})
        cfg.update(gist_id=g["id"], gist_user=g["owner"]["login"])
        ecrire_config(cfg)
    return lien_raw(cfg)


def _init():
    import getpass
    cfg = lire_config()
    phrase_secrete(cfg)
    if not (os.environ.get("SPIRIT_GIST_TOKEN") or cfg.get("token")):
        print("Créez un jeton sur https://github.com/settings/tokens/new avec UNIQUEMENT la case « gist »,")
        print("sans date d'expiration (ou longue), puis collez-le ici (il ne s'affiche pas) :")
        cfg["token"] = getpass.getpass("Jeton : ").strip()
        ecrire_config(cfg)
    if not cfg.get("gist_id"):
        attente = {"v": 1, "info": "en attente de la première mise à jour de Suivi finances"}
        tok = jeton(cfg)
        g = _api("POST", "/gists", tok, {"description": "Mon Spirit 2 (chiffré)", "public": False,
                                         "files": {FICHIER: {"content": json.dumps(attente)}}})
        cfg.update(gist_id=g["id"], gist_user=g["owner"]["login"])
        ecrire_config(cfg)
    _infos()


def _infos():
    cfg = lire_config()
    print("Configuration locale :", chemin_config())
    if cfg.get("gist_id"):
        print("Lien de synchronisation :", lien_raw(cfg))
    print("Phrase secrète :", cfg.get("passphrase", "(pas encore créée)"))
    print("→ À saisir une seule fois dans Mon Spirit 2 › Contrat › Synchronisation automatique.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--init"]:
        _init()
    elif args[:1] == ["--infos"]:
        _infos()
    else:
        solde = None
        if "--solde" in args:
            i = args.index("--solde"); solde = float(args[i + 1]); del args[i:i + 2]
        src = open(args[0], encoding="utf-8") if args else sys.stdin
        contrat = json.load(src)
        print("Publié :", publier(contrat, solde), "— total", valider(contrat, solde), "€")
