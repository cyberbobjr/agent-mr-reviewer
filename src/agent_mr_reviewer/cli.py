import argparse
import os
import sys

from agent_mr_reviewer.gitlab_client import GitLabClient
from agent_mr_reviewer.llm_client import OpenAICompatibleClient
from agent_mr_reviewer.reviewer import run_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GitLab MR reviewer agent")
    parser.add_argument("--gitlab-url", default=os.getenv("GITLAB_URL"))
    parser.add_argument("--project-id", default=os.getenv("PROJECT_ID"))
    parser.add_argument("--mr-iid", default=os.getenv("MR_IID"))
    parser.add_argument("--token-env", default="CI_JOB_TOKEN")
    parser.add_argument("--max-comments", type=int, default=50)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--llm-disable", action="store_true")
    parser.add_argument("--llm-base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com"))
    parser.add_argument("--llm-model", default=os.getenv("OPENAI_MODEL"))
    parser.add_argument("--llm-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--llm-max-context", type=int, default=50000)
    parser.add_argument("--llm-chunk-tokens", type=int, default=12000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    missing = [
        name
        for name, value in (
            ("gitlab-url", args.gitlab_url),
            ("project-id", args.project_id),
            ("mr-iid", args.mr_iid),
        )
        if not value
    ]
    if missing:
        print(f"Missing required args or env vars: {', '.join(missing)}", file=sys.stderr)
        return 2

    token = os.getenv(args.token_env)
    if not token:
        print(f"Missing token env var: {args.token_env}", file=sys.stderr)
        return 2

    token_type = "job" if args.token_env == "CI_JOB_TOKEN" else "private"
    client = GitLabClient(args.gitlab_url, token, token_type=token_type)

    llm_client = None
    if not args.llm_disable:
        api_key = os.getenv(args.llm_api_key_env)
        if not api_key:
            print(f"Missing LLM API key env var: {args.llm_api_key_env}", file=sys.stderr)
            return 2
        if not args.llm_model:
            print("Missing LLM model (set OPENAI_MODEL or --llm-model)", file=sys.stderr)
            return 2
        llm_client = OpenAICompatibleClient(
            base_url=args.llm_base_url,
            api_key=api_key,
            model=args.llm_model,
        )

    run_review(
        client=client,
        project_id=args.project_id,
        mr_iid=args.mr_iid,
        max_comments=args.max_comments,
        summary_only=args.summary_only,
        dry_run=args.dry_run,
        llm_client=llm_client,
        llm_max_context=args.llm_max_context,
        llm_chunk_tokens=args.llm_chunk_tokens,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
