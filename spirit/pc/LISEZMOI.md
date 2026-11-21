# Publier le contrat Linxea vers Mon Spirit 2 (iPhone), chiffré

`publier_spirit2.py` reçoit le contrat au format Mon Spirit 2. Il le vérifie, puis le chiffre en AES-256-GCM avec une clé PBKDF2-SHA256 de 200 000 itérations. Il publie ensuite le résultat dans un Gist GitHub secret. L'iPhone relit ce Gist à chaque ouverture de l'app.

Le script ne contient aucune donnée personnelle. La phrase secrète, le jeton et l'identifiant du Gist restent sur le PC, dans `%APPDATA%\SpiritSync\config.json`, hors de tout dépôt.

## Installation sur le PC (une seule fois)

1. Copiez `publier_spirit2.py` dans le dossier « Suivi finances ».
2. Installez la dépendance : `pip install cryptography`.
3. Créez un jeton GitHub sur https://github.com/settings/tokens/new. Cochez **uniquement** « gist » et choisissez une longue durée.
4. Lancez `python publier_spirit2.py --init` et collez le jeton quand il est demandé. La commande crée la phrase secrète (7 mots aléatoires) et le Gist secret. Elle affiche ensuite le **lien** et la **phrase secrète**.
5. Sur l'iPhone, ouvrez Mon Spirit 2 › Contrat › Synchronisation automatique. Collez le lien et la phrase secrète, puis enregistrez.

`python publier_spirit2.py --infos` réaffiche le lien et la phrase.

## Brancher sur « Suivi finances »

Juste après l'enregistrement du contrat Linxea dans « Suivi finances » :

```python
from publier_spirit2 import publier
publier(contrat, solde=solde_linxea)   # lève une erreur si la somme des supports ≠ solde
```

`contrat` doit avoir ce format (montants en nombres, dates AAAA-MM-JJ) :

```json
{"contract":{"name":"Linxea Spirit 2","number":"","holder":"","insurer":"Spirica","openDate":"AAAA-MM-JJ","mode":"","feesEntry":"","feesUC":"","feesEuro":"","beneficiary":""},
 "supports":[{"id":"s1","name":"","isin":"","type":"euro|uc|scpi","units":0,"nav":0,"pru":0,"amount":0}],
 "operations":[{"id":"o1","date":"AAAA-MM-JJ","type":"versement|rachat|arbitrage|interets|frais","amount":0,"label":""}],
 "history":[{"date":"AAAA-MM-JJ","value":0}]}
```

- Support `euro` : le montant va dans `amount`.
- Support `uc` : remplissez `units` et `nav`. `amount` est la valeur actuelle, soit parts × VL.

Si « Suivi finances » n'est pas écrit en Python, il peut écrire ce JSON dans un fichier puis lancer :
`python publier_spirit2.py contrat.json --solde 12345.67`

## À ne jamais commiter

`config.json` (jeton, phrase secrète) et tout JSON du contrat en clair. Seul le contenu chiffré quitte le PC.
