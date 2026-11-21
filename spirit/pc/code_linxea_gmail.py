#!/usr/bin/env python3
"""Lit automatiquement dans Gmail le code de sécurité Linxea (connexion à l'espace client).

Linxea envoie à chaque connexion un e-mail de noreply@auth.linxea.com dont l'objet est
« Votre code de sécurité : 123456 » (valable environ 5 minutes). Ce module attend cet
e-mail et renvoie le code, pour que « Suivi finances » se connecte sans intervention.

    from code_linxea_gmail import attendre_code
    t0 = time.time()                 # juste AVANT de demander le code à Linxea
    ...                              # Linxea envoie l'e-mail
    code = attendre_code(depuis=t0)  # -> "123456"

Accès : IMAP Gmail avec un « mot de passe d'application » Google (lecture seule,
révocable à tout moment). Il est rangé avec la config de publier_spirit2.py, HORS dépôt :
    Windows : %APPDATA%\\SpiritSync\\config.json   (clés gmail_user, gmail_app_password)

    python code_linxea_gmail.py --init    (enregistre l'adresse et le mot de passe d'application)
    python code_linxea_gmail.py --test    (affiche le dernier code reçu, pour vérifier)
"""
import email, email.header, email.utils, imaplib, re, sys, time

from publier_spirit2 import chemin_config, ecrire_config, lire_config

EXPEDITEUR = "noreply@auth.linxea.com"
RE_CODE = re.compile(r"\b(\d{6})\b")


def _objet(msg):
    return "".join(p.decode(c or "utf-8", "replace") if isinstance(p, bytes) else p
                   for p, c in email.header.decode_header(msg.get("Subject", "")))


def extraire_code(msg):
    """Renvoie le code à 6 chiffres d'un e-mail Linxea, ou None."""
    if EXPEDITEUR not in (msg.get("From") or "").lower():
        return None
    objet = _objet(msg)
    if "code" not in objet.lower():
        return None
    m = RE_CODE.search(objet)
    return m.group(1) if m else None


def _connexion(cfg):
    if not (cfg.get("gmail_user") and cfg.get("gmail_app_password")):
        raise RuntimeError("Accès Gmail non configuré : lancez « python code_linxea_gmail.py --init ».")
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    imap.login(cfg["gmail_user"], cfg["gmail_app_password"].replace(" ", ""))
    imap.select("INBOX", readonly=True)
    return imap


def derniers_codes(imap, n=5):
    """[(horodatage, code)] des derniers e-mails de code Linxea, du plus récent au plus ancien."""
    typ, data = imap.search(None, "X-GM-RAW", f'"from:{EXPEDITEUR} newer_than:1d"')
    ids = (data[0] or b"").split()[-n:]
    res = []
    for i in reversed(ids):
        typ, d = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        msg = email.message_from_bytes(d[0][1])
        code = extraire_code(msg)
        if code:
            res.append((email.utils.parsedate_to_datetime(msg["Date"]).timestamp(), code))
    return res


def attendre_code(depuis=None, delai=180, pas=5):
    """Attend un code reçu après `depuis` (timestamp ; 30 s de marge) et le renvoie."""
    depuis = (time.time() if depuis is None else depuis) - 30
    cfg = lire_config()
    fin = time.time() + delai
    while True:
        imap = _connexion(cfg)
        try:
            for t, code in derniers_codes(imap):
                if t >= depuis:
                    return code
        finally:
            imap.logout()
        if time.time() > fin:
            raise TimeoutError(f"Aucun code Linxea reçu en {delai} s")
        time.sleep(pas)


def _init():
    import getpass
    cfg = lire_config()
    print("Créez un mot de passe d'application sur https://myaccount.google.com/apppasswords")
    print("(nécessite la validation en 2 étapes Google). Nom suggéré : « Suivi finances ».")
    cfg["gmail_user"] = input("Adresse Gmail : ").strip()
    cfg["gmail_app_password"] = getpass.getpass("Mot de passe d'application (16 lettres, masqué) : ").strip()
    ecrire_config(cfg)
    _connexion(cfg).logout()
    print("Connexion Gmail OK. Config :", chemin_config())


if __name__ == "__main__":
    if sys.argv[1:2] == ["--init"]:
        _init()
    elif sys.argv[1:2] == ["--test"]:
        imap = _connexion(lire_config())
        codes = derniers_codes(imap); imap.logout()
        print("Derniers codes Linxea (24 h) :", [(time.strftime("%d/%m %H:%M", time.localtime(t)), c) for t, c in codes] or "aucun")
    else:
        print(__doc__)
