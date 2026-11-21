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

## Mise à jour sans intervention (code Linxea lu dans Gmail)

À chaque connexion à l'espace client, Linxea envoie un **code de sécurité à 6 chiffres par e-mail**. L'objet est « Votre code de sécurité : 123456 », l'expéditeur noreply@auth.linxea.com, et le code reste valable environ 5 minutes. Sans ce code, « Suivi finances » ne peut pas se reconnecter seul. `code_linxea_gmail.py` lit ce code dans Gmail.

1. Activez la validation en 2 étapes Google, puis créez un mot de passe d'application sur https://myaccount.google.com/apppasswords.
2. Lancez `python code_linxea_gmail.py --init` et saisissez l'adresse et ce mot de passe. Ils sont rangés dans `%APPDATA%\SpiritSync\config.json`.
3. Dans le code de connexion Linxea de « Suivi finances », appelez la fonction juste avant de valider le code :

```python
import time
from code_linxea_gmail import attendre_code
t0 = time.time()                 # avant de cliquer « recevoir le code »
...                              # Linxea envoie l'e-mail
code = attendre_code(depuis=t0)  # attend au plus 3 min, renvoie "123456"
```

4. Planifiez la mise à jour (PowerShell, dans le dossier « Suivi finances ») :
   `.\installer_tache.ps1 -Commande "python <script de mise à jour Linxea>" -Heure "07:43"`

`python code_linxea_gmail.py --test` affiche les codes reçus dans les dernières 24 h.

## À ne jamais commiter

`config.json` (jeton, phrase secrète) et tout JSON du contrat en clair. Seul le contenu chiffré quitte le PC.
