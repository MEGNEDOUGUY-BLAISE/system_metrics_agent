# System Metrics Agent

Un agent Python modulaire capable de collecter les métriques système,
de les formater et de les transmettre en temps réel vers une API ou un
Webhook externe. Le projet est conteneurisé (Docker, Docker Compose) et
livré par un pipeline CI/CD GitHub Actions (tests, SonarQube, Trivy,
publication sur Docker Hub).

## Fonctionnalités

- Collecte du pourcentage CPU.
- Collecte de la mémoire RAM totale, utilisée et disponible.
- Utilisation de `psutil`.
- Utilisation de **`subprocess`** pour exécuter la commande système
  `uptime` et récupérer la charge système.
- Architecture modulaire :
  - `collector.py` : collecte ;
  - `formatter.py` : normalisation du payload ;
  - `sender.py` : envoi HTTP ;
  - `agent.py` : orchestration ;
  - `api.py` : API de réception avec **FastAPI**.
- Configuration externe avec `.env`.
- Gestion des erreurs réseau et des erreurs de collecte.
- Tests automatisés avec `pytest` (22 tests, couverture 92 %).

## Architecture

```text
system_metrics_agent/
├── .github/
│   └── workflows/
│       └── ci-cd.yml            # pipeline CI/CD
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── api.py
│   ├── collector.py
│   ├── config.py
│   ├── formatter.py
│   ├── sender.py
│   └── tests/
│       ├── __init__.py
│       ├── test_agent.py
│       ├── test_api.py
│       ├── test_collector.py
│       ├── test_config.py
│       ├── test_formatter.py
│       └── test_sender.py
├── .coveragerc
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile.agent
├── Dockerfile.api
├── docker-compose.yml
├── requirements-agent.in / .txt # dépendances de l'agent (source / verrouillé)
├── requirements-api.in / .txt   # dépendances de l'API (source / verrouillé)
├── requirements-dev.in / .txt   # dépendances de développement et de test
├── sonar-project.properties
└── README.md
```

Les fichiers `.in` décrivent les dépendances souhaitées. Les fichiers
`.txt` sont générés par `pip-compile` (pip-tools) : ils figent les
versions exactes de toutes les dépendances, directes et indirectes, avec
leurs empreintes SHA-256. Ils sont générés pour Linux / Python 3.12
(images Docker et CI).

## Installation locale

Créer un environnement virtuel :

```bash
python -m venv .venv
```

Linux/macOS :

```bash
source .venv/bin/activate
```

Windows :

```powershell
.venv\Scripts\Activate.ps1
```

Installer les dépendances de développement :

```bash
pip install -r requirements-dev.in
```

Sous Linux avec Python 3.12, on peut utiliser le fichier verrouillé :
`pip install --require-hashes -r requirements-dev.txt`.

Créer le fichier de configuration :

```bash
cp .env.example .env
```

Sous Windows : `Copy-Item .env.example .env`.

## Démarrer l'API FastAPI

```bash
uvicorn app.api:app --reload
```

L'API est alors disponible sur `http://127.0.0.1:8000`, et sa
documentation interactive sur `http://127.0.0.1:8000/docs`.

## Démarrer l'agent

Dans un deuxième terminal :

```bash
python -m app.agent
```

L'agent collecte les métriques selon l'intervalle défini dans `.env`
puis les envoie automatiquement vers `METRICS_ENDPOINT`.

## Exécution avec Docker Compose

```bash
docker compose up --build
```

Puis, dans un autre terminal :

```bash
curl http://localhost:8000/metrics/latest
```

Compose crée un réseau dédié (`metrics-net`). L'agent joint l'API par
son nom de service (`http://api:8000/metrics`) et ne démarre qu'une fois
l'API déclarée saine (`depends_on: condition: service_healthy`).

Images publiées sur Docker Hub :

- `douguyblaise4747/metrics-api`
- `douguyblaise4747/metrics-agent`

## Exemple de configuration

```env
METRICS_ENDPOINT=http://127.0.0.1:8000/metrics
COLLECTION_INTERVAL=5
REQUEST_TIMEOUT=5
```

Pour envoyer vers un webhook externe, remplacer simplement :

```env
METRICS_ENDPOINT=https://example.com/webhook
```

## Exemple de métrique envoyée

```json
{
  "agent": "system-metrics-agent",
  "event_type": "system_metrics",
  "data": {
    "timestamp": "2026-08-27T12:00:00.000000+00:00",
    "hostname": "server-01",
    "cpu": {
      "percent": 23.4,
      "logical_cores": 8
    },
    "memory": {
      "total_bytes": 16777216000,
      "available_bytes": 8000000000,
      "used_bytes": 7777216000,
      "percent": 48.2
    },
    "system": {
      "load_1m": 0.12,
      "load_5m": 0.18,
      "load_15m": 0.20
    }
  }
}
```

## Endpoints

| Méthode | Route | Rôle |
|---|---|---|
| `GET` | `/health` | État de l'API (`{"status": "ok"}`) |
| `POST` | `/metrics` | Réception d'une métrique |
| `GET` | `/metrics` | Liste des métriques reçues |
| `GET` | `/metrics/latest` | Dernière métrique reçue |

## Tests

```bash
pytest -q
pytest --cov=app --cov-report=term-missing
```

## Pipeline CI/CD

Fichier : `.github/workflows/ci-cd.yml`. Déclenché sur `push` (`main`,
`feature/**`) et sur `pull_request` vers `main`.

1. **Job `test`** : installation des dépendances verrouillées, `black`,
   `flake8`, `pytest` avec couverture XML, analyse **SonarQube Cloud**
   avec attente de la Quality Gate (`sonar.qualitygate.wait=true`) :
   le job échoue si la Quality Gate n'est pas validée.
2. **Job `build-scan-push`** (`needs: test`, matrice `api` / `agent`) :
   build de l'image (`load: true`), scan **Trivy** (échec sur toute
   vulnérabilité HIGH ou CRITICAL corrigeable), puis connexion et push
   sur Docker Hub (tags `<sha>` et `latest`) **uniquement sur un push
   vers `main`**, jamais sur une pull request.

Secrets GitHub utilisés : `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`,
`SONAR_TOKEN`, `SONAR_HOST_URL`. Aucun secret n'est présent dans le dépôt.

## Rapport

### Choix techniques

- **Images multi-stage** sur `python:3.12.15-slim-trixie` (tag précis) :
  l'étape *builder* installe les dépendances dans un venv `/opt/venv`,
  l'image finale ne copie que ce venv et le code applicatif.
- **Une image par composant**, avec des dépendances séparées : l'agent
  n'embarque ni FastAPI ni Uvicorn.
- **Utilisateur non-root** (`app`, UID 10001) dans les deux images ;
  **healthcheck** de l'API en Python (`curl` absent de l'image slim) ;
  `uvicorn` sans `--reload`, à l'écoute sur `0.0.0.0`.
- **Dépendances verrouillées avec empreintes** (`pip-compile
  --generate-hashes`), installées avec `--require-hashes --only-binary
  :all:` : un paquet modifié est refusé et aucun script d'installation
  n'est exécuté.
- **Actions GitHub épinglées par SHA de commit**, droits du jeton limités
  à `contents: read`, tokens à durée de validité limitée.

### Tailles des images (mesurées en local avec `docker images`)

| Image | Sur disque | Compressée |
|---|---|---|
| `python:3.12.15-slim-trixie` (base) | 179 Mo | 45,4 Mo |
| `metrics-api` | 252 Mo | 59,7 Mo |
| `metrics-agent` | 203 Mo | 49,1 Mo |

### Agent conteneurisé et métriques de l'hôte

Dans un conteneur, l'agent lit le noyau Linux qui exécute Docker (ici la
VM WSL2 : environ 16 Go de RAM au lieu des 32 Go du PC) et se présente
sous l'identifiant du conteneur, et non sous le nom de la machine. Pour
superviser un vrai serveur, il faut l'installer sur l'hôte ou lui donner
un accès explicite aux informations de l'hôte (par exemple `--pid=host`
et `/proc` de l'hôte en lecture seule) ; cette piste n'a pas été testée.

### Difficultés rencontrées

- **Tests dépendants de l'OS** : deux tests du collecteur échouaient sous
  Windows (`platform.system()` non simulé) ; corrigés et complétés.
- **README et dépôt non alignés** (`tests/` annoncé à la racine), fichier
  parasite `app/montFichier.py`, ancien pipeline de déploiement SSH
  inutilisable (secrets absents du fork, chemin Windows dans un script
  Linux) : corrigés ou supprimés.
- **`uptime` absent de l'image slim** : vérifié dans un conteneur, puis
  résolu en installant le paquet Debian `procps`.
- **Docker Desktop sans WSL** : installation de WSL2 nécessaire.
- **SonarQube** : injection de logs signalée dans `api.py` (champ
  `agent` du client écrit dans les logs), corrigée ; couverture portée
  de 58 % à 92 % pour satisfaire la Quality Gate (80 % sur le nouveau
  code).
- **Chaîne d'approvisionnement** : l'action `aquasecurity/trivy-action`
  a été compromise en mars 2026 ; la version saine v0.35.0 est épinglée
  par son SHA.
- **Syntaxe YAML** : `--only-binary :all:` (deux-points suivis d'un
  espace) rendait le workflow invalide ; corrigé avec un bloc `run: |`.
- **Secrets** : tokens SonarCloud et Docker Hub refusés (mauvaise copie,
  token supprimé, permissions par défaut en lecture seule). Les tokens
  exposés par erreur ont été révoqués et remplacés.

### Démonstration d'échec

Sur la branche `feature/demo-echec`, un test volontairement faux
(`{"status": "ko"}`) fait échouer le job `test` : les jobs de build et de
push sont alors ignorés, aucune image n'est publiée. Un `git revert`
rétablit un pipeline vert.
