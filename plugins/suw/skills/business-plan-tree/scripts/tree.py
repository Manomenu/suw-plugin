#!/usr/bin/env python3
"""Helper for business-plan-tree pages: interactive decision trees whose whole content is one JSON data block.

    tree.py new SLUG [--title T] [--lang pl|en] [--root DIR]   create DIR/<date>-SLUG.html (DIR: docs/visual/tree)
    tree.py check PATH                                         report ERRORs and WARNs in the data block
    tree.py register PATH URL                                  record the published artifact in claude-artifacts.md
    tree.py links PATH                                         whether the page already has an artifact URL
    tree.py refresh PATH                                       give the page the current template's engine, data kept

Standard library only, so it runs wherever python3 does.
"""

import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template.html"
REGISTRY = "claude-artifacts.md"
DEFAULT_ROOT = "docs/visual/tree"
STATUSES = ("open", "yes", "no", "unclear")
LANGS = ("pl", "en")
START = "<!-- TREE DATA START"
END = "<!-- TREE DATA END -->"
DATA_RE = re.compile(r"(<!-- TREE DATA START[^\n]*-->\s*<script type=\"application/json\" id=\"tree-data\">)(.*?)(</script>\s*<!-- TREE DATA END -->)", re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
# Same registry format as suwagent's vdoc.py register, so both tools read each other's tables.
ROW_RE = re.compile(r"^\| (?P<title>.*?) \| \[(?P<file>[^\]]+)\]\([^)]*\) \| <?(?P<url>https://[^ >|]+)>? \| (?P<date>[^|]*?) \|$")
ARTIFACT_URL_RE = re.compile(r"^https://claude\.ai/(?:code/)?artifact/[\w-]+$")

EXAMPLES = {
    "pl": {
        "lang": "pl",
        "title": "Drzewa planu biznesu",
        "eyebrow": "Przykład · drzewa decyzyjne",
        "heading": "Czy ten biznes ma sens?",
        "rule": "Idziemy dalej, gdy przejdzie **rynek**, a do tego **co najmniej jedna ścieżka klienta**.",
        "asOf": "",
        "overview": {
            "title": "Dwa niezależne drzewa",
            "text": "Pierwsze nie zależy od tego, kto płaci, i musi przejść. Drugie wybiera klienta i wystarczy w nim jedna ścieżka.",
            "note": "W każdym drzewie pytania stoją od najtańszych do sprawdzenia (dane, przy biurku) do najdroższych (rozmowy z ludźmi).",
        },
        "rows": [["M"], ["C"]],
        "trees": [
            {"id": "M", "mode": "must", "frame": "musi przejść", "need": "musi przejść",
             "title": "Czy rynek jest wart uwagi?", "sub": "skala problemu i pieniądze w nim",
             "desc": "Jeśli problem jest mały, żaden klient go nie uratuje.",
             "branches": [{"to": "M1"}]},
            {"id": "C", "mode": "any", "frame": "wystarczy jedna ścieżka", "need": "wystarczy jedna ścieżka",
             "title": "Kto jest klientem?", "sub": "od tego zależy, jaki to będzie biznes",
             "desc": "Każda ścieżka to inny biznes. Wystarczy, że przejdzie jedna.",
             "branches": [{"edge": "firmy", "to": "B1"}, {"edge": "osoby prywatne", "to": "P1"}]},
        ],
        "paths": {"B": "firmy", "P": "osoby prywatne"},
        "nodes": {
            "M1": {"type": "gate", "tree": "M", "status": "open", "step": "Krok 1 · Skala",
                   "q": "Czy problem dotyczy wystarczająco wielu ludzi lub firm?",
                   "check": ["Dane GUS i raporty branżowe", "Liczba podmiotów w rejestrach"],
                   "outs": [{"label": "tak", "to": "M_OK"},
                            {"label": "nie", "stop": "za mały rynek", "meaning": "Problem jest niszowy i nie utrzyma firmy."}]},
            "M_OK": {"type": "ok", "tree": "M", "label": "Rynek wart uwagi", "sub": "jest dość klientów z tym problemem"},
            "B1": {"type": "gate", "tree": "C", "path": "B", "status": "open", "step": "Krok 2 · Płatnicy",
                   "q": "Czy firmy zapłacą za rozwiązanie?",
                   "check": ["3–5 rozmów z osobami, które kupują takie usługi", "Cenniki obecnych dostawców"],
                   "outs": [{"label": "tak", "to": "B_OK"},
                            {"label": "nie", "stop": "ścieżka firm odpada", "meaning": "Firmy rozwiązują to same albo nie mają budżetu."}]},
            "B_OK": {"type": "ok", "tree": "C", "label": "Biznes B2B", "sub": "usługa dla firm"},
            "P1": {"type": "gate", "tree": "C", "path": "P", "status": "open", "step": "Krok 2 · Płatnicy",
                   "q": "Czy osoby prywatne zapłacą za rozwiązanie?",
                   "check": ["Fora i grupy osób z tym problemem", "3–5 rozmów z potencjalnymi klientami"],
                   "outs": [{"label": "tak", "to": "P_OK"},
                            {"label": "nie", "stop": "ścieżka osób prywatnych odpada", "meaning": "Ludzie wolą darmowe obejścia problemu."}]},
            "P_OK": {"type": "ok", "tree": "C", "label": "Biznes B2C", "sub": "usługa dla osób prywatnych"},
        },
    },
    "en": {
        "lang": "en",
        "title": "Business plan trees",
        "eyebrow": "Example · decision trees",
        "heading": "Does this business make sense?",
        "rule": "We go on when the **market** passes, plus **at least one client path**.",
        "asOf": "",
        "overview": {
            "title": "Two independent trees",
            "text": "The first does not depend on who pays and must pass. The second picks the client, and one path in it is enough.",
            "note": "In each tree, questions go from the cheapest to check (data, at a desk) to the most expensive (talking to people).",
        },
        "rows": [["M"], ["C"]],
        "trees": [
            {"id": "M", "mode": "must", "frame": "must pass", "need": "must pass",
             "title": "Is the market worth it?", "sub": "size of the problem and the money in it",
             "desc": "If the problem is small, no client will save it.",
             "branches": [{"to": "M1"}]},
            {"id": "C", "mode": "any", "frame": "one path is enough", "need": "one path is enough",
             "title": "Who is the client?", "sub": "this decides what business it is",
             "desc": "Each path is a different business. One passing path is enough.",
             "branches": [{"edge": "companies", "to": "B1"}, {"edge": "consumers", "to": "P1"}]},
        ],
        "paths": {"B": "companies", "P": "consumers"},
        "nodes": {
            "M1": {"type": "gate", "tree": "M", "status": "open", "step": "Step 1 · Size",
                   "q": "Does the problem affect enough people or companies?",
                   "check": ["Statistics office data and industry reports", "Number of entities in public registers"],
                   "outs": [{"label": "yes", "to": "M_OK"},
                            {"label": "no", "stop": "market too small", "meaning": "The problem is niche and won't sustain a company."}]},
            "M_OK": {"type": "ok", "tree": "M", "label": "Market worth it", "sub": "enough clients have this problem"},
            "B1": {"type": "gate", "tree": "C", "path": "B", "status": "open", "step": "Step 2 · Payers",
                   "q": "Will companies pay for a solution?",
                   "check": ["3–5 interviews with people who buy such services", "Price lists of current providers"],
                   "outs": [{"label": "yes", "to": "B_OK"},
                            {"label": "no", "stop": "company path fails", "meaning": "Companies solve it in-house or have no budget."}]},
            "B_OK": {"type": "ok", "tree": "C", "label": "B2B business", "sub": "a service for companies"},
            "P1": {"type": "gate", "tree": "C", "path": "P", "status": "open", "step": "Step 2 · Payers",
                   "q": "Will consumers pay for a solution?",
                   "check": ["Forums and groups of people with this problem", "3–5 interviews with potential clients"],
                   "outs": [{"label": "yes", "to": "P_OK"},
                            {"label": "no", "stop": "consumer path fails", "meaning": "People prefer free workarounds."}]},
            "P_OK": {"type": "ok", "tree": "C", "label": "B2C business", "sub": "a service for consumers"},
        },
    },
}


def dump(data):
    """The data as text that is safe inside <script type="application/json">: no </ and no <!-- in it."""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    return text.replace("</", "<\\/").replace("<!--", "<\\u0021--")


def put_data(page, data_text):
    m = DATA_RE.search(page)
    if not m:
        sys.exit("the TREE DATA START/END markers or the tree-data script are missing")
    return page[:m.start(2)] + "\n" + data_text.strip("\n") + "\n" + page[m.end(2):]


def put_title(page, title):
    return TITLE_RE.sub(lambda m: f"<title>{html.escape(title, quote=False)}</title>", page, count=1)


def as_of(lang, day):
    return day.strftime("%d.%m.%Y") if lang == "pl" else day.isoformat()


# ---------- check ----------

def _pairs_no_dupes(dupes):
    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                dupes.append(k)
            seen[k] = v
        return seen
    return hook


def problems(page):
    """(errors, warnings) for a page's text."""
    errors, warns = [], []
    m = DATA_RE.search(page)
    if not m:
        if START in page and END in page:
            errors.append("the data block ends early: a </script inside it closes the script (write <\\/ instead of </)")
        else:
            errors.append("no data block: <!-- TREE DATA START --> <script type=\"application/json\" id=\"tree-data\"> … </script> <!-- TREE DATA END --> is missing")
        return errors, warns
    raw = m.group(2)
    if re.search(r"</script", raw, re.I):
        errors.append("the data block contains </script, which ends the script early in the browser; write <\\/script")
    if "<!--" in raw:
        errors.append("the data block contains <!--; write <\\u0021-- in strings")
    elif re.search(r"</", raw):
        warns.append("the data block contains </; write <\\/ so it can never close the script")
    dupes = []
    try:
        data = json.loads(raw, object_pairs_hook=_pairs_no_dupes(dupes))
    except json.JSONDecodeError as e:
        errors.append(f"invalid JSON in the data block: {e}")
        return errors, warns
    for k in dupes:
        errors.append(f"duplicate key {k!r} in the data block")
    if not isinstance(data, dict):
        errors.append("the data block must be a JSON object")
        return errors, warns

    if data.get("lang", "pl") not in LANGS:
        errors.append(f"lang must be one of {', '.join(LANGS)}, not {data.get('lang')!r}")
    if not data.get("title"):
        errors.append("title is missing")
    title_tag = TITLE_RE.search(page)
    if title_tag and data.get("title") and html.unescape(title_tag.group(1).strip()) != data["title"]:
        warns.append("the <title> tag differs from data.title; `tree.py refresh` copies data.title into it")

    trees = data.get("trees")
    nodes = data.get("nodes")
    rows = data.get("rows")
    paths = data.get("paths", {}) or {}
    if not isinstance(trees, list) or not trees:
        errors.append("trees must be a non-empty list")
        trees = []
    if not isinstance(nodes, dict):
        errors.append("nodes must be an object of id → node")
        nodes = {}
    if not isinstance(rows, list) or not all(isinstance(r, list) for r in rows):
        errors.append("rows must be a list of lists of tree ids")
        rows = []
    if not isinstance(paths, dict):
        errors.append("paths must be an object of path id → name")
        paths = {}

    tree_ids = []
    for i, t in enumerate(trees):
        if not isinstance(t, dict) or not t.get("id"):
            errors.append(f"trees[{i}] has no id")
            continue
        if t["id"] in tree_ids:
            errors.append(f"duplicate tree id {t['id']!r}")
        tree_ids.append(t["id"])
        if not t.get("title"):
            errors.append(f"tree {t['id']}: title is missing")
        if t.get("mode", "must") not in ("must", "any"):
            errors.append(f"tree {t['id']}: mode must be must or any")
        branches = t.get("branches")
        if not isinstance(branches, list) or not branches:
            errors.append(f"tree {t['id']}: branches must list at least one {{to}}")
            continue
        for b in branches:
            to = b.get("to") if isinstance(b, dict) else None
            if not to:
                errors.append(f"tree {t['id']}: a branch has no to")
            elif to not in nodes:
                errors.append(f"tree {t['id']}: branch to {to!r}, which is not a node")

    in_rows = [i for r in rows for i in r]
    for i in in_rows:
        if i not in tree_ids:
            errors.append(f"rows reference unknown tree {i!r}")
    for i in sorted(set(in_rows)):
        if in_rows.count(i) > 1:
            errors.append(f"tree {i!r} appears in rows more than once")
    for i in tree_ids:
        if i not in in_rows:
            errors.append(f"tree {i!r} is missing from rows, so it is never drawn")

    for nid, n in nodes.items():
        if not isinstance(n, dict):
            errors.append(f"node {nid}: must be an object")
            continue
        kind = n.get("type")
        if n.get("tree") not in tree_ids:
            errors.append(f"node {nid}: tree {n.get('tree')!r} does not exist")
        if "path" in n and n["path"] not in paths:
            errors.append(f"node {nid}: path {n['path']!r} is not in paths")
        if kind == "ok":
            if not n.get("label"):
                errors.append(f"node {nid}: ok leaf without label")
            continue
        if kind != "gate":
            errors.append(f"node {nid}: type must be gate or ok, not {kind!r}")
            continue
        if n.get("status") not in STATUSES:
            errors.append(f"node {nid}: status {n.get('status')!r} is not one of {', '.join(STATUSES)}")
        if not n.get("q"):
            errors.append(f"node {nid}: gate without q (the question)")
        outs = n.get("outs")
        if not isinstance(outs, list) or not outs:
            errors.append(f"node {nid}: gate without outs")
            continue
        has_to = has_end = False
        for j, o in enumerate(outs):
            if not isinstance(o, dict):
                errors.append(f"node {nid}: outs[{j}] must be an object")
                continue
            if not o.get("label"):
                errors.append(f"node {nid}: outs[{j}] has no label")
            if ("to" in o) == ("stop" in o):
                errors.append(f"node {nid}: outs[{j}] needs exactly one of to or stop")
                continue
            if "to" in o:
                if o["to"] not in nodes:
                    errors.append(f"node {nid}: out {o.get('label')!r} goes to {o['to']!r}, which is not a node")
                    continue
                has_to = True
                if isinstance(nodes[o["to"]], dict) and nodes[o["to"]].get("type") == "ok":
                    has_end = True
            else:
                has_end = True
                if not o.get("meaning"):
                    warns.append(f"node {nid}: stop out {o.get('label')!r} has no meaning (what that answer would mean)")
        if not has_to:
            errors.append(f"node {nid}: gate needs at least one out with to (the path continues)")
        if not has_end:
            errors.append(f"node {nid}: gate needs at least one out that ends: a stop, or a to an ok leaf")
        if not n.get("check"):
            warns.append(f"node {nid}: gate has no check items (what to look at to answer it)")
        if "answer" in n and n["answer"] not in [o.get("label") for o in outs if isinstance(o, dict)]:
            errors.append(f"node {nid}: answer {n['answer']!r} is not the label of one of its outs")
        for s in n.get("sources", []) or []:
            if not isinstance(s, dict) or not s.get("title"):
                errors.append(f"node {nid}: every source needs a title (and usually a url)")
        if n.get("status") in ("yes", "no") and not n.get("sources"):
            warns.append(f"node {nid}: status {n['status']} without sources")
        if n.get("status") in ("yes", "no", "unclear") and not n.get("note"):
            warns.append(f"node {nid}: status {n['status']} without a note saying what was found")

    # Reachability: each node is reached once, from a root of its own tree, with no cycles.
    parents = {}
    for t in trees:
        if not isinstance(t, dict) or not t.get("id"):
            continue
        for b in t.get("branches") or []:
            if isinstance(b, dict) and b.get("to") in nodes:
                parents.setdefault(b["to"], []).append((f"tree {t['id']}", t["id"]))
    for nid, n in nodes.items():
        if isinstance(n, dict) and n.get("type") == "gate":
            for o in n.get("outs") or []:
                if isinstance(o, dict) and o.get("to") in nodes:
                    parents.setdefault(o["to"], []).append((f"node {nid}", n.get("tree")))
    for nid, n in nodes.items():
        ps = parents.get(nid, [])
        if not ps:
            errors.append(f"node {nid}: unreachable from any root (no branch or out leads to it)")
            continue
        if len(ps) > 1:
            errors.append(f"node {nid}: reached from more than one place ({', '.join(p for p, _ in ps)}); give each place its own node")
        for p, tree in ps:
            if isinstance(n, dict) and tree != n.get("tree"):
                errors.append(f"node {nid}: belongs to tree {n.get('tree')!r} but {p} of tree {tree!r} leads to it")
    reachable = set()
    stack = [b["to"] for t in trees if isinstance(t, dict) for b in t.get("branches") or [] if isinstance(b, dict) and b.get("to") in nodes]
    while stack:
        nid = stack.pop()
        if nid in reachable:
            continue
        reachable.add(nid)
        n = nodes[nid]
        if isinstance(n, dict) and n.get("type") == "gate":
            stack += [o["to"] for o in n.get("outs") or [] if isinstance(o, dict) and o.get("to") in nodes]
    for nid in nodes:
        if nid not in reachable and parents.get(nid):
            errors.append(f"node {nid}: unreachable from any root (it hangs only under other unreachable nodes, or in a cycle)")
    return errors, warns


def cmd_check(a):
    path = Path(a.path)
    if not path.is_file():
        sys.exit(f"{path} does not exist")
    errors, warns = problems(path.read_text(encoding="utf-8"))
    for e in errors:
        print(f"ERROR {path}: {e}")
    for w in warns:
        print(f"WARN  {path}: {w}")
    if errors:
        sys.exit(1)
    print(f"ok    {path}" + (f" ({len(warns)} warnings)" if warns else ""))


# ---------- new / refresh ----------

def cmd_new(a):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.slug):
        sys.exit("SLUG must be kebab-case, such as tutoring-app")
    day = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    dest = Path(a.root) / f"{day.isoformat()}-{a.slug}.html"
    if dest.exists() and not a.force:
        sys.exit(f"{dest} already exists; edit it, or pass --force to start over")
    data = json.loads(json.dumps(EXAMPLES[a.lang]))
    if a.title:
        data["title"] = a.title
    data["asOf"] = as_of(a.lang, day)
    page = put_title(put_data(TEMPLATE.read_text(encoding="utf-8"), dump(data)), data["title"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")
    print(f"created {dest}")
    print("next: replace the example in the JSON data block (between TREE DATA START and END), then `tree.py check` it")


def cmd_refresh(a):
    path = Path(a.path)
    old = path.read_text(encoding="utf-8")
    m = DATA_RE.search(old)
    if not m:
        sys.exit(f"{path}: the data block is missing or broken, so the data can't be told from the engine; run check")
    page = put_data(TEMPLATE.read_text(encoding="utf-8"), m.group(2))
    try:
        title = json.loads(m.group(2)).get("title")
    except (json.JSONDecodeError, AttributeError):
        title = None
    old_title = TITLE_RE.search(old)
    page = put_title(page, title or (html.unescape(old_title.group(1).strip()) if old_title else path.stem))
    path.write_text(page, encoding="utf-8")
    print(f"refreshed {path} from {TEMPLATE.name}" + ("" if page != old else " (already current)"))


# ---------- register / links ----------

def read_registry(folder):
    reg = folder / REGISTRY
    rows = {}
    if reg.exists():
        for line in reg.read_text(encoding="utf-8").splitlines():
            m = ROW_RE.match(line.strip())
            if m:
                rows[m["file"]] = {"title": m["title"], "url": m["url"], "date": m["date"].strip()}
    return rows


def write_registry(folder, rows):
    kind = folder.name
    lines = [
        f"# Claude artifacts: {kind}",
        "",
        f"Published claude.ai artifact of each {kind} document in this folder. The local `.html` file is the",
        "source; the artifact is its published copy. Maintained by `tree.py register`, so edit with care.",
        "",
        "| Document | File | Artifact | Updated |",
        "| :- | :- | :- | :- |",
    ]
    for file, r in sorted(rows.items()):
        title = r["title"].replace("|", "\\|")
        lines.append(f"| {title} | [{file}]({file}) | <{r['url']}> | {r['date']} |")
    (folder / REGISTRY).write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_register(a):
    path = Path(a.path)
    if not path.is_file():
        sys.exit(f"{path} does not exist")
    url = a.url.strip().rstrip("/")
    if not ARTIFACT_URL_RE.match(url):
        sys.exit(f"{url} is not a claude.ai artifact URL (https://claude.ai/artifact/<id>)")
    m = TITLE_RE.search(path.read_text(encoding="utf-8"))
    title = html.unescape(m.group(1).strip()) if m else path.stem
    rows = read_registry(path.parent)
    old = rows.get(path.name)
    rows[path.name] = {"title": title, "url": url, "date": datetime.date.today().isoformat()}
    write_registry(path.parent, rows)
    note = "" if not old or old["url"] == url else f" (replaced {old['url']})"
    print(f"registered {path.name} → {url} in {path.parent / REGISTRY}{note}")


def cmd_links(a):
    path = Path(a.path)
    own = read_registry(path.parent).get(path.name)
    print(f"published at {own['url']} (update that artifact)" if own else "not published yet")


def main(argv=None):
    p = argparse.ArgumentParser(prog="tree.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("slug")
    n.add_argument("--title")
    n.add_argument("--lang", choices=LANGS, default="pl")
    n.add_argument("--root", default=DEFAULT_ROOT, help=f"folder for the page (default {DEFAULT_ROOT})")
    n.add_argument("--date", help="YYYY-MM-DD instead of today")
    n.add_argument("--force", action="store_true")
    n.set_defaults(fn=cmd_new)
    for name, fn in (("check", cmd_check), ("links", cmd_links), ("refresh", cmd_refresh)):
        s = sub.add_parser(name)
        s.add_argument("path")
        s.set_defaults(fn=fn)
    r = sub.add_parser("register")
    r.add_argument("path")
    r.add_argument("url")
    r.set_defaults(fn=cmd_register)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
