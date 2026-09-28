# Connect a separate context store

AI Analyst can read business context from a separate local folder, including a cloned Git repository. It reads the files directly; there is no sync cache in `source: path` mode.

The public course starter is [ai-analyst-context](https://github.com/ai-analyst-lab/ai-analyst-context). It contains workspace guidance and dataset metadata, not completed business definitions or answer keys. Ask Claude to clone it beside AI Analyst and follow its `docs/SETUP.md`. Keep existing folders and local changes.

After preserving your previous configuration, set `.knowledge/context-source.yaml` in AI Analyst to:

```yaml
source: path
path: ../ai-analyst-context
```

Paths are resolved relative to the AI Analyst project. Leave `.env`, `.knowledge/active.yaml` and your local connection manifest unchanged. Context metadata does not replace data-access credentials.

## What loads, and when

1. `helpers.knowledge.context_snapshot.knowledge_root` locates the store. Dataset readers use `resolve_context_dir` from `helpers.knowledge.context_sync`.
2. `guide_catalog(project_root, dataset=...)` returns `workspace.md` and guide descriptions, scope and review metadata. It does not return every guide body.
3. Claude chooses relevant guides for the question. `load_guide` requires the guide ID, question, selection reason, analysis ID and catalog hash. It returns the complete body and records it in `working/context_loads_<analysis_id>.jsonl`.
4. Check the executed query and result to see whether the definition was applied correctly. A loading log alone does not establish correctness.

Project instructions and the knowledge-bootstrap skill direct Claude through this process. The loader is ordinary Python, not a background service, vector database or automatic semantic-layer execution engine. The model still has to call it.

## Guide format

Each `guides/<id>.yaml` needs `id`, `description`, `dataset`, `owner`, `source`, `status`, `reviewed_on`, `review_after` and `content`. Optional `scope` helps selection. The filename must match the ID. The description should name the questions for which the guide is useful; the content supplies the actual guidance. Review dates use `YYYY-MM-DD`. A human reviews the meaning before `status: reviewed` is set.

The catalog excludes drafts, expired reviews and other datasets. Loading fails if the guide changed since catalog selection. A configured but missing store is an error, not permission to fall back to another definition. Conflicting definitions require clarification; the loader does not decide business policy.

## Repeated runs

The reliability runner accepts `--context-store /path/to/store`. It saves one context snapshot and gives identical copies to the fresh trial workspaces. Later edits affect a new run, not an existing snapshot. Run outputs contain `context-snapshot/`, `trials.json`, `reliability.md` and `trials/<number>/` with an input inventory, response and trace files.

Snapshots control supplied inputs; they are not an operating-system security sandbox. Keep credentials and evaluation answers out of context stores. Traces can contain business information, so review them before sharing.
