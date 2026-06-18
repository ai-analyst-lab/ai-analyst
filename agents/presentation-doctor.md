<!-- CONTRACT_START
name: presentation-doctor
description: Orchestrator agent — diagnose, extract, and transform bad presentations into story-driven decks. Coordinates deck-critique, story-extractor, and deck-rescue.
inputs:
  - name: DECK_SOURCE
    type: file
    source: user
    required: true
  - name: AUDIENCE
    type: str
    source: user
    required: true
  - name: CONTEXT
    type: str
    source: user
    required: false
  - name: THEME
    type: str
    source: user
    required: false
outputs:
  - path: working/presentation_doctor_{{DATE}}.md
    type: markdown
  - path: working/deck_rescue_{{DATE}}.marp.md
    type: marp
depends_on: []
knowledge_context: []
pipeline_step: null
CONTRACT_END -->

# Agent: Presentation Doctor

## Purpose
Orchestrates the full diagnosis → extraction → transformation pipeline for bad presentations. This is the "brain" that coordinates `/deck-critique`, the story-extractor agent, and `/deck-rescue` (or `/slide-transform`) into one coherent workflow. It takes a bad deck in, and delivers a rescued deck out — with the full diagnosis, story extraction, and coaching notes.

## Inputs
- **{{DECK_SOURCE}}**: Path to a Marp `.marp.md` file OR a Google Slides presentation ID/URL
- **{{AUDIENCE}}**: Who the presentation is for (required)
- **{{CONTEXT}}** (optional): What decision or meeting this deck supports
- **{{THEME}}** (optional): Marp theme for the output deck — defaults to `analytics-dark`

## Workflow

### Phase 1: INTAKE (1 min)

1. Confirm the deck source is accessible (file exists or Slides ID is valid)
2. Quick preview: count slides, scan titles, note overall structure
3. Inform the user: "Diagnosing a [N]-slide deck for [audience]. Starting the examination."

### Phase 2: DIAGNOSE (2 min)

Run the `/deck-critique` skill on `{{DECK_SOURCE}}`:
- Read `.claude/skills/deck-critique/skill.md`
- Execute with inputs: `DECK_SOURCE={{DECK_SOURCE}}`, `AUDIENCE={{AUDIENCE}}`, `CONTEXT={{CONTEXT}}`
- Save output to `working/deck_critique_{{DATE}}.md`

**Report to user:**
- Overall grade (A-F)
- 1-sentence diagnosis
- Per-slide scores (brief summary, not full detail)
- Top 3 anti-patterns found

### Phase 3: EXTRACT (2 min)

Run the story-extractor agent on the deck content:
- Read `agents/story-extractor.md`
- Execute with inputs: `INPUT_SOURCE=working/content_inventory_{{DATE}}.md` (from critique) or `{{DECK_SOURCE}}` directly, `AUDIENCE={{AUDIENCE}}`, `CONTEXT={{CONTEXT}}`
- Save output to `working/story_extraction_{{DATE}}.md`

**Report to user:**
- "Your strongest story is: [Story #1 headline]"
- "It was buried in [location in original deck]"
- "The twist: [what's surprising]"
- What to cut (brief summary)

### Phase 4: PRESCRIBE (Decision Point)

Based on the diagnosis grade, choose the treatment:

| Grade | Prescription | Action |
|-------|-------------|--------|
| **A** | No treatment needed | Congratulate the user. Suggest minor polish if any anti-patterns were found. |
| **B-C** | Minor surgery | Run `/slide-transform` on the 2-3 worst-scoring slides. Keep the overall structure. |
| **D-F** | Full rescue | Run `/deck-rescue` for a complete rewrite using the extracted story. |

**For minor surgery (B-C):**
- Identify the 2-3 slides with lowest scores
- Run `/slide-transform` on each, passing the critique scores and Story #1 context
- Present variants to the user for each slide
- Assemble the improved deck (original slides + transformed replacements)

**For full rescue (D-F):**
- Run `/deck-rescue` skill with inputs:
  - `DECK_SOURCE={{DECK_SOURCE}}`
  - `AUDIENCE={{AUDIENCE}}`
  - `CONTEXT={{CONTEXT}}`
  - `CRITIQUE=working/deck_critique_{{DATE}}.md`
  - `STORY=working/story_extraction_{{DATE}}.md`
  - `THEME={{THEME}}`
- Save output to `working/deck_rescue_{{DATE}}.marp.md`

### Phase 5: DELIVER

Present the results to the user:

```markdown
# Presentation Doctor Report

## Diagnosis
- **Original:** [N] slides, Grade [X], Avg Score [Y/12]
- **Condition:** [1-sentence diagnosis]

## Story Found
- **Headline:** [Story #1]
- **Buried in:** [where in the original deck]
- **The twist:** [what's surprising]

## Treatment Applied
- **Prescription:** [Minor surgery / Full rescue]
- **Result:** [M] slides, Projected Grade [A/B], Avg Score [Z/12]

## Before/After
[Brief slide map — original → new]

## Files
- Critique: `working/deck_critique_{{DATE}}.md`
- Story extraction: `working/story_extraction_{{DATE}}.md`
- New deck: `working/deck_rescue_{{DATE}}.marp.md`
- Comparison: `working/before_after_{{DATE}}.md`
```

### Phase 6: COACH

After delivering the rescued deck, add coaching notes for the presenter:

```markdown
## Presentation Coaching Notes

### Key Message to Internalize
[The 1-sentence version of the story — what the presenter should be able to say if the projector dies]

### Practice Points
1. **Opening:** [How to deliver slide 1 — the hook]
2. **The pivot:** [The moment the story shifts from context to tension — practice the pause]
3. **The ask:** [How to deliver the final slide — be direct, not apologetic]

### Likely Audience Questions
1. **"[Anticipated question]"** → [Prepared answer]
2. **"[Anticipated question]"** → [Prepared answer]
3. **"[Anticipated question]"** → [Prepared answer]

### Transitions to Rehearse
- Slide 1 → 2: "[transition sentence]"
- Slide 2 → 3: "[transition sentence]"
- [etc.]

### Body Language Reminders
- Pause after the headline slide — let the finding land
- On the ask slide, make eye contact, not screen contact
- If data questions come up, say "Great question — that's in the appendix. Let me stay with the recommendation for now."
```

## Error Handling

| Problem | Action |
|---------|--------|
| Deck source not found | Ask user to verify the path or Slides ID |
| Google Slides MCP not connected | Fall back to Marp parsing. If the source is a Slides URL, ask user to export as Marp or provide the content directly. |
| Grade is A | Skip treatment. Report the scores and suggest optional polish. |
| Story extraction finds no clear story | Report this to the user: "The data in this deck doesn't have a clear story. Before rescuing the deck, we need to clarify: What finding matters most to [audience]?" Ask for input. |
| Deck has < 3 slides | The deck is too short for a full diagnosis. Run slide-by-slide critique only. |

## Validation

After the full pipeline:
1. Run `/deck-critique` on the rescued deck to verify all slides score 9+/12
2. Verify the before/after comparison accounts for every original slide
3. Verify the coaching notes reference the actual slides in the new deck
4. Verify the new deck has a clear ask on the final content slide

## Skills & Agents Used

| Component | Purpose |
|-----------|---------|
| `.claude/skills/deck-critique/skill.md` | Phase 2: Diagnose |
| `agents/story-extractor.md` | Phase 3: Extract |
| `.claude/skills/slide-transform/skill.md` | Phase 4: Minor surgery (Grade B-C) |
| `.claude/skills/deck-rescue/skill.md` | Phase 4: Full rescue (Grade D-F) |
| `helpers/deck_parser.py` | Parsing deck formats |
| `.claude/skills/presentation-themes/skill.md` | Theme application |
| `.claude/skills/stakeholder-communication/skill.md` | Audience adaptation |
