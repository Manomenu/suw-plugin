---
name: business-plan-tree
description: Draw interactive decision trees that answer the key questions of a business plan (does the business make sense at all, what blocks it, who pays) as one self-contained HTML page, a forest of independent trees with pan and zoom and a detail panel, published as a claude.ai artifact; then keep editing that page conversationally whenever the user asks for a change (add, move or remove a question, rename, merge trees, fill in statuses with findings and sources after research).
when_to_use: The user wants to see whether a business idea or plan holds up, asks for a decision tree of a business, wants a plan's risks or open questions as a tree, or asks to change an existing tree page; or says "business plan tree", "decision tree", "drzewo decyzyjne", "drzewo planu biznesu", "rozrysuj drzewo", "drzewa decyzyjne biznesu", "zmień drzewo", "dodaj pytanie do drzewa".
argument-hint: "[business idea, path to a brief/plan, or the change to make in an existing tree]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/business-plan-tree/scripts/tree.py *)
---

# Business plan tree

One page, `docs/visual/tree/<YYYY-MM-DD>-<slug>.html`, answers "does this business make sense?" as a forest of
decision trees. The engine (layout, pan/zoom, panel, light/dark) is fixed; **all content is one JSON data
block** in the page. You write and edit only that block.

Helper: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/business-plan-tree/scripts/tree.py` (below: `tree.py`).
Template: `${CLAUDE_PLUGIN_ROOT}/skills/business-plan-tree/template.html` (its data block is a small valid example).

Publishing mode: **${user_config.publish_mode}**. `artifact` (default when the value above is empty or unresolved):
publish with the Artifact tool and register the link. `local`: never publish; open the file
(`xdg-open` / `open`) and give its path. If the session has no Artifact tool, work as `local` and say so in one line.

## Sources

Take the business from, in this order: `$ARGUMENTS`; a brief or plan file in the project (`README.md`,
`docs/`, `*brief*`, `*plan*`); the conversation. If a plan with numbered steps exists, every gate names the plan
step that answers it (`step`). Ask only if none of these says what the business is.

## How to build a good tree

1. **Split independent questions into their own trees.** Questions that don't depend on each other (legal
   freedom to operate, competition and how contrarian the idea is, market size and money in it) each get their
   own root with `mode: "must"` and `need` "musi przejść" / "must pass": if one fails, the idea fails. The choice
   (usually: who is the client) is one tree with `mode: "any"`, a branch per option (`branches[].edge` names it,
   its nodes carry `path`) and `need` "wystarczy jedna ścieżka" / "one path is enough".
2. **A question that applies to every branch of a choice is not under the fork.** It moves to an independent
   root. Only what differs per option stays on that option's path.
3. **Phrase each gate so "tak / yes" continues.** The other answer either stops the path (`stop`, plus
   `meaning`: what that answer would mean, written as a hypothesis) or leads to another node (e.g. "empty market"
   as an ok leaf). The first out is drawn downwards, further outs to the right, so put the continuing out first.
4. **Order gates cheapest to check first**: laws, registers and data at a desk before interviews and pilots.
5. **Each gate lists concrete things to check** (`check`): named laws and articles, registers, data sources,
   reports, how many interviews with whom. Vague items ("research the market") are not checks.
6. **Nothing is verified when first drawn**: every status is `open`; the page then says on its own that the
   answers are hypotheses. Don't fill a status until research has been done and has sources.
7. Write the verdict rule (`rule`) as one line naming the must-pass trees and the choice, with `**bold**`.
   `overview` says how the trees relate and how the questions are ordered.

## Data block (the only part you edit)

Between `<!-- TREE DATA START … -->` and `<!-- TREE DATA END -->`, inside
`<script type="application/json" id="tree-data">`. Text is plain (escaped); `**bold**` is the only markup, and in
`note` a blank line (`\n\n`) starts a paragraph. Inside strings write `<\/` for `</`.

```jsonc
{
  "lang": "pl",                        // pl | en: language of the UI labels; use the user's language
  "title": "…",                        // tab and artifact title (tree.py refresh copies it into <title>)
  "eyebrow": "…", "heading": "…", "rule": "… **wolne ręce** …", "asOf": "13.11.2026",
  "overview": { "title": "…", "text": "…", "note": "…" },
  "rows": [["L", "K", "S"], ["C"]],    // tree ids per row; every tree exactly once
  "trees": [{ "id": "C", "mode": "any", "frame": "wystarczy jedna ścieżka · krok 2", "need": "wystarczy jedna ścieżka",
              "title": "Kto jest klientem?", "sub": "…", "desc": "…", "okNote": "optional",
              "branches": [{ "edge": "gmina", "to": "G1" }] }],
  "paths": { "B": "gmina" },
  "nodes": {
    "G1": { "type": "gate", "tree": "C", "path": "B", "status": "open", "step": "Krok 2 · Prawo",
            "q": "Czy gmina może …?", "check": ["Ustawa …", "Raporty NIK …"],
            "outs": [{ "label": "tak", "to": "G2" },
                     { "label": "nie", "stop": "ścieżka B odpada", "meaning": "…" }] },
    "B_OK": { "type": "ok", "tree": "C", "label": "Biznes B: B2G", "sub": "…" }
  }
}
```

After research, a gate also gets: `status` `yes` / `no` / `unclear`; `note` (what was found, first sentence in
`**bold**`); `checked` (e.g. "zwiad 13.11.2026"); `caveat` (what is still unsure); `sources` `[{title, url}]`;
optionally `answer` (the label of the out research picked, when it isn't the first out for yes / the second for
no). Node ids: short, by tree (`L1`, `G3`, `A_OK`). Each node is reached from exactly one place.

## Steps

1. `tree.py links <file>` if a page exists, to know whether it is already published.
2. New page: `tree.py new <slug> --title "<title>" --lang pl|en` (from the project root; `--root DIR` for
   another folder). Then replace the example in the data block with the real trees.
3. `tree.py check <file>` and fix every ERROR (invalid JSON, `</script` in the block, missing or duplicate ids,
   targets that don't exist, unreachable nodes, rows vs trees, bad status, a gate without a continuing out and an
   ending out, unknown path). Fix WARNs unless there is a reason (say it).
4. One visual look if the session can: wrap the file in `<!doctype html><html><head><meta charset="utf-8"></head><body>…</body></html>`
   in a temp folder and screenshot it with headless Firefox or Chrome (e.g. `firefox --headless --screenshot out.png
   --window-size=1400,900 file:///…`), then open the PNG. Look for overlapping labels, cut text, an empty page.
5. Publish (`artifact` mode): Artifact tool with the page file, `icon` "tree", a one-sentence `description`. Then
   `tree.py register <file> <artifact-url>`. Every later publish passes the same file path (or the registered URL
   in a new session), so the link stays the same.

## Conversational edits

When the user asks to change the tree (add, move or remove a question, rename, split or merge trees, change the
order, fill a status after research with `note` and `sources`):

- Edit only the data block, run `tree.py check`, republish to the same artifact, `tree.py register` again.
- Reply in a few lines: what changed, the link, what waits on the user.
- Don't touch the engine (CSS/JS) unless the user explicitly asks for an engine change. Then change only this
  page and say in one line that the plugin's template could get the same change.
- An old page with an outdated engine: `tree.py refresh <file>` swaps in the current engine and keeps the data.

## Hand-off

In chat: the link (or the local path), one sentence on what the trees show, and what waits on the user (e.g. which
gates to research first). The page's language is the user's language.
