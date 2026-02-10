# Agent MR Reviewer

Objectif: agent execute par Jenkins lors de la creation d'une Merge Request (GitLab). Il lit le contenu de la MR, recupere les modifications (diff/commits) et publie des commentaires de revue (inline + resume global).

## Fonctionnalites

- Recupere details MR, commits et changements via API GitLab.
- Analyse les lignes ajoutees avec des regles simples (qualite, nommage, doc, clean code).
- Poste des commentaires inline sur les lignes concernees.
- Poste un commentaire global de synthese.
- Mode dry-run pour validation sans commentaire.

## Prerequis

- Python 3.9+
- Variables d'environnement (exemple Jenkins):
  - `GITLAB_URL` (ex: https://gitlab.example.com)
  - `PROJECT_ID` (id numerique ou path URL-encode)
  - `MR_IID` (IID de la MR)
  - `CI_JOB_TOKEN` (token de job GitLab)
  - `OPENAI_API_KEY` (cle API LLM compatible OpenAI)
  - `OPENAI_MODEL` (ex: gpt-4o-mini ou modele fourni par votre endpoint)
  - `OPENAI_BASE_URL` (ex: https://api.openai.com)

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Execution

```bash
python -m agent_mr_reviewer.cli \
  --gitlab-url "$GITLAB_URL" \
  --project-id "$PROJECT_ID" \
  --mr-iid "$MR_IID"
```

Options utiles:

- `--dry-run` : n'envoie rien a GitLab, affiche les commentaires.
- `--summary-only` : n'envoie pas de commentaires inline, uniquement le resume.
- `--max-comments 50` : limite pour eviter le spam.
- `--token-env CI_JOB_TOKEN` : nom de la variable contenant le token.
- `--llm-disable` : desactive l'analyse LLM, utilise les regles internes.
- `--llm-model` : modele LLM a utiliser (sinon `OPENAI_MODEL`).
- `--llm-base-url` : endpoint OpenAI compatible (sinon `OPENAI_BASE_URL`).
- `--llm-api-key-env` : nom de la variable contenant la cle LLM.
- `--llm-max-context 50000` : limite de contexte tokens LLM.
- `--llm-chunk-tokens 12000` : taille des chunks pour le map-reduce.

## Exemple Jenkins

```groovy
pipeline {
  agent any
  stages {
    stage('MR Review') {
      steps {
        sh '''
          python -m venv .venv
          . .venv/bin/activate
          pip install -r requirements.txt
          python -m agent_mr_reviewer.cli \
            --gitlab-url "$GITLAB_URL" \
            --project-id "$PROJECT_ID" \
            --mr-iid "$MR_IID"
        '''
      }
    }
  }
}
```

## Notes API GitLab

- Commentaire inline: `POST /projects/:id/merge_requests/:iid/discussions`
- Commentaire global: `POST /projects/:id/merge_requests/:iid/notes`

## Roadmap

- Ajouter regles par langage.
- Prise en charge de severites par type de commentaire.
- Edition pour eviter les doublons.
# agent-mr-reviewer
