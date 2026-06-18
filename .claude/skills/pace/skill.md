---
name: pace
description: Change how visibly Claude surfaces analytical work during L3+ analyses. Three modes — guided (announce each phase and pause for /continue), narrated (announce each phase and run end-to-end), autopilot (silent end-to-end, final output only). Use this skill whenever the user invokes `/pace`, `/pace guided`, `/pace narrated`, `/pace autopilot`, or says things like "slow down and walk me through", "pause between steps", "just run it silently", "narrate each step", "don't stop to ask me", "stop narrating". Pace is orthogonal to complexity level — it changes surfacing, not which agents run. Full spec and phase-banner format live in the question-router skill. This skill is the write-side: it persists the user's explicit pace choice to `working/session_state.yaml` so it survives across phases, across `/resume-pipeline`, and across sessions.
---

# Skill: Pace

## Purpose

Persist the user's explicit choice of **pace mode** — how visibly the analytical
machinery surfaces during L3+ analyses. Pace is orthogonal to complexity level
(L1–L5). Level decides which agents run; pace decides how visible the work is.

## Modes

| Mode | Behavior |
|------|----------|
| `guided` | Announce each phase, run it, **pause** and wait for `/continue` before the next phase |
| `narrated` | Announce each phase, run it, announce the result, continue to the next phase without pausing (the safe default) |
| `autopilot` | Silent end-to-end. No phase banners. Final output only. |

## Invocation

The user types one of:
- `/pace guided`
- `/pace narrated`
- `/pace autopilot`
- `/pace` (no argument) — show the current mode and the three options
- Natural language: "slow down, pause between steps" → guided; "just run it silently" → autopilot; "narrate but don't stop" → narrated

## Behavior

1. **Resolve the target mode.** If the argument is one of `guided|narrated|autopilot`,
   use it. If no argument, print the current mode (read from
   `working/session_state.yaml` → `pace_mode`) and the three options. Stop.
2. **Validate.** If the argument is anything else, echo the three valid modes
   and ask which one the user wants. Do NOT guess or silently fall back.
3. **Read existing state.** Load `working/session_state.yaml` if it exists;
   otherwise start with an empty dict. Preserve every other key.
4. **Write atomically.** Write the updated YAML to
   `working/session_state.yaml.tmp`, then rename to `working/session_state.yaml`.
   This prevents corruption if the process is interrupted mid-write.
5. **Confirm to the user.** One line:
   - `guided` → "Pace set to **guided**. I'll pause after each phase and wait for `/continue`."
   - `narrated` → "Pace set to **narrated**. I'll announce each phase and run end-to-end."
   - `autopilot` → "Pace set to **autopilot**. I'll run silently and show you the final output."
6. **Apply on next phase boundary.** If an analysis is already in flight, the
   new mode takes effect starting with the **next** phase. Tell the user so.
   Never switch mid-phase — it produces inconsistent banner state.

## Failure Handling

- **Write fails** (permissions, disk full, working/ missing): honor the mode
  in the current session **in memory** and warn: "Pace set to {mode} for this
  session, but I couldn't write `working/session_state.yaml` ({reason}). Run
  `/pace {mode}` again after resume to restore it."
- **YAML parse fails on existing file**: back up the broken file to
  `working/session_state.yaml.broken-{timestamp}`, write a fresh one with just
  `pace_mode`, and tell the user. Never overwrite without backing up.
- **No `working/` directory**: create it (`mkdir -p working`), then proceed.

## Implementation

Use Python for atomic write and YAML safety. Keep it minimal:

```python
import yaml, os, pathlib, datetime

STATE_PATH = pathlib.Path("working/session_state.yaml")

def set_pace(mode: str) -> tuple[bool, str]:
    assert mode in {"guided", "narrated", "autopilot"}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    state = {}
    if STATE_PATH.exists():
        try:
            state = yaml.safe_load(STATE_PATH.read_text()) or {}
        except yaml.YAMLError:
            bak = STATE_PATH.with_suffix(
                f".yaml.broken-{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}"
            )
            STATE_PATH.rename(bak)
            state = {}

    state["pace_mode"] = mode
    tmp = STATE_PATH.with_suffix(".yaml.tmp")
    try:
        tmp.write_text(yaml.safe_dump(state, sort_keys=False))
        os.replace(tmp, STATE_PATH)
        return True, ""
    except OSError as e:
        return False, str(e)
```

## Edge Cases

- **Mid-phase invocation**: honor at next phase boundary, not immediately. Tell the user.
- **No L3+ analysis running**: still persist the mode. It applies to the next one.
- **User types `/pace` during a guided pause**: show current mode + options, do not consume the pause.
- **`working/session_state.yaml` already has other keys** (from session-handoff, resume-pipeline): preserve them all; only touch `pace_mode`.

## See Also

- Full pace-mode spec and auto-detection rules: `.claude/skills/question-router/skill.md` → "Step 3.5: Pace Mode Selection" and "Phase Banner Format".
- Session state schema and other persisted keys: `.claude/skills/session-handoff/skill.md`.
