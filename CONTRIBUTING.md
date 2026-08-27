# Contributing

Thanks for helping make the analyst better. The bar for a change is simple: it has to make the
analyst more correct, more honest, or easier to use, and it has to pass the same checks CI runs.

## Before you open a PR

```bash
pip install -e ".[dev]"
python scripts/repo_lint.py     # frontmatter, file case, secrets, private paths, public hosts, residue
python -m pytest tests/         # 882 tests; add one for any helper you change
```

Both must pass. The lint's allowlist is `scripts/repo_lint_allow.txt`; add a line only for a
reviewed, legitimate exception (say why in the comment).

## Adding a skill

1. Create `.claude/skills/<name>/SKILL.md`. The file name is case-sensitive: `SKILL.md`.
2. Frontmatter with `name:` (must equal the directory name) and a `description:` written as a
   `>-` block scalar. The description is the trigger: name the tasks and the phrases a user would
   say, and say when NOT to use it if a sibling skill overlaps.
3. Add it to `docs/SKILLS.md` in the right group.
4. Reference helpers by their package path (`helpers/data/...`), never by a path outside the repo.
5. Never upload data anywhere the user did not ask for. Drive-only for chart hosting.

## Adding an agent

Copy `agents/CONTRACT_TEMPLATE.md` into the right folder (`pipeline/`, `experiments/`, `causal/`,
`export/`, `review/`), fill in the contract (inputs, outputs, when it runs), then register it in
`agents/registry.yaml` and `agents/INDEX.md`.

## Changing a helper

Helpers are the deterministic layer; the model reasons, the code computes. A statistical change
needs a test with a known answer (see `tests/` for the pattern) and a note in the module docstring
about the method. Keep imports as `from helpers.<package>.<module> import ...`.

## Style

Plain language in skills and docs. No em dashes. Say what a thing does, not how clever it is.
Numbers in docs must be real (counts, test totals) and updated when they change.

## Reporting a security issue

See [SECURITY.md](.github/SECURITY.md).
