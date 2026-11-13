"""tree.py: check passes on good pages and names each broken one; new, refresh, register and links keep their promises."""
import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins" / "suw" / "skills" / "business-plan-tree"
sys.path.insert(0, str(SKILL / "scripts"))
import tree  # noqa: E402

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "alimenty.json").read_text(encoding="utf-8"))


def page(data):
    """A page from the current template carrying this data."""
    return tree.put_title(tree.put_data(tree.TEMPLATE.read_text(encoding="utf-8"), tree.dump(data)), data.get("title", ""))


def run(*argv):
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out):
        try:
            tree.main(list(argv))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            if not isinstance(e.code, int) and e.code:
                out.write(str(e.code))
    return code, out.getvalue()


def example():
    return copy.deepcopy(tree.EXAMPLES["pl"])


class Check(unittest.TestCase):
    def assertError(self, text, fragment):
        errors, _ = tree.problems(text)
        self.assertTrue(any(fragment in e for e in errors), f"no error with {fragment!r} in {errors}")

    def test_the_template_example_passes(self):
        errors, warns = tree.problems(tree.TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual([], errors)
        self.assertEqual([], warns)

    def test_the_template_carries_the_pl_example(self):
        m = tree.DATA_RE.search(tree.TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(tree.EXAMPLES["pl"], json.loads(m.group(2)))

    def test_both_examples_pass(self):
        for lang in tree.LANGS:
            with self.subTest(lang=lang):
                self.assertEqual([], tree.problems(page(tree.EXAMPLES[lang]))[0])

    def test_the_reference_alimenty_page_passes(self):
        errors, _ = tree.problems(page(FIXTURE))
        self.assertEqual([], errors)
        self.assertEqual(25, len(FIXTURE["nodes"]))
        self.assertEqual("unclear", FIXTURE["nodes"]["K2"]["status"])

    def test_check_command_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / "good.html", Path(tmp) / "bad.html"
            good.write_text(page(FIXTURE), encoding="utf-8")
            broken = example()
            broken["nodes"]["M1"]["status"] = "maybe"
            bad.write_text(page(broken), encoding="utf-8")
            self.assertEqual(0, run("check", str(good))[0])
            code, out = run("check", str(bad))
            self.assertEqual(1, code)
            self.assertIn("ERROR", out)

    def test_invalid_json(self):
        text = page(example()).replace('"lang": "pl",', '"lang": "pl",,', 1)
        self.assertError(text, "invalid JSON")

    def test_unescaped_script_end(self):
        d = example()
        d["nodes"]["M1"]["q"] = "x </script> y"
        text = page(d).replace("<\\/script>", "</script>")
        self.assertError(text, "</script")

    def test_duplicate_node_id(self):
        text = page(example()).replace('"M_OK": {', '"M1": {"type": "ok", "tree": "M", "label": "dup"},\n    "M_OK": {', 1)
        self.assertError(text, "duplicate key 'M1'")

    def test_duplicate_tree_id(self):
        d = example()
        d["trees"][1]["id"] = "M"
        self.assertError(page(d), "duplicate tree id 'M'")

    def test_missing_tree_id(self):
        d = example()
        del d["trees"][0]["id"]
        self.assertError(page(d), "has no id")

    def test_out_to_a_missing_node(self):
        d = example()
        d["nodes"]["M1"]["outs"][0]["to"] = "NOPE"
        self.assertError(page(d), "'NOPE', which is not a node")

    def test_branch_to_a_missing_node(self):
        d = example()
        d["trees"][0]["branches"][0]["to"] = "NOPE"
        self.assertError(page(d), "branch to 'NOPE'")

    def test_unreachable_node(self):
        d = example()
        d["nodes"]["ORPHAN"] = {"type": "ok", "tree": "M", "label": "nobody leads here"}
        self.assertError(page(d), "node ORPHAN: unreachable")

    def test_node_reached_twice(self):
        d = example()
        d["nodes"]["B1"]["outs"][0]["to"] = "P_OK"
        self.assertError(page(d), "reached from more than one place")

    def test_rows_reference_an_unknown_tree(self):
        d = example()
        d["rows"].append(["X"])
        self.assertError(page(d), "unknown tree 'X'")

    def test_tree_missing_from_rows(self):
        d = example()
        d["rows"] = [["M"]]
        self.assertError(page(d), "'C' is missing from rows")

    def test_invalid_status(self):
        d = example()
        d["nodes"]["M1"]["status"] = "done"
        self.assertError(page(d), "status 'done'")

    def test_gate_without_a_continuing_out(self):
        d = example()
        d["nodes"]["M1"]["outs"] = [{"label": "nie", "stop": "x", "meaning": "y"}]
        d["nodes"]["M_OK"]["tree"] = "M"
        d["trees"][0]["branches"].append({"to": "M_OK"})
        self.assertError(page(d), "at least one out with to")

    def test_gate_without_an_ending_out(self):
        d = example()
        d["nodes"]["M2"] = {"type": "gate", "tree": "M", "status": "open", "q": "q2", "check": ["c"],
                            "outs": [{"label": "tak", "to": "M_OK"}, {"label": "nie", "stop": "x", "meaning": "m"}]}
        d["nodes"]["M1"]["outs"] = [{"label": "tak", "to": "M2"}]
        self.assertError(page(d), "at least one out that ends")

    def test_unknown_path(self):
        d = example()
        d["nodes"]["B1"]["path"] = "Z"
        self.assertError(page(d), "path 'Z' is not in paths")

    def test_out_with_both_to_and_stop(self):
        d = example()
        d["nodes"]["M1"]["outs"][1]["to"] = "M_OK"
        self.assertError(page(d), "exactly one of to or stop")

    def test_cycle(self):
        d = example()
        d["nodes"]["M2"] = {"type": "gate", "tree": "M", "status": "open", "q": "q", "check": ["c"],
                            "outs": [{"label": "tak", "to": "M3"}, {"label": "nie", "stop": "x", "meaning": "m"}]}
        d["nodes"]["M3"] = {"type": "gate", "tree": "M", "status": "open", "q": "q", "check": ["c"],
                            "outs": [{"label": "tak", "to": "M2"}, {"label": "nie", "stop": "x", "meaning": "m"}]}
        self.assertError(page(d), "unreachable")

    def test_warnings(self):
        d = example()
        d["nodes"]["M1"]["check"] = []
        del d["nodes"]["M1"]["outs"][1]["meaning"]
        errors, warns = tree.problems(page(d))
        self.assertEqual([], errors)
        self.assertTrue(any("no check items" in w for w in warns), warns)
        self.assertTrue(any("has no meaning" in w for w in warns), warns)

    def test_research_fields_are_accepted(self):
        d = example()
        d["nodes"]["M1"].update(status="yes", note="**Tak.**\n\nDetails.", checked="13.11.2026", caveat="c",
                                sources=[{"title": "GUS", "url": "https://stat.gov.pl"}], answer="tak")
        self.assertEqual(([], []), tree.problems(page(d)))
        d["nodes"]["M1"]["answer"] = "maybe"
        self.assertError(page(d), "answer 'maybe'")


class Commands(unittest.TestCase):
    def test_new_creates_a_page_that_passes_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            for lang in tree.LANGS:
                code, out = run("new", f"idea-{lang}", "--title", "Moje drzewo", "--lang", lang, "--root", tmp, "--date", "2026-11-13")
                self.assertEqual(0, code, out)
                path = Path(tmp) / f"2026-11-13-idea-{lang}.html"
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertIn("<title>Moje drzewo</title>", text)
                self.assertEqual(([], []), tree.problems(text))
                data = json.loads(tree.DATA_RE.search(text).group(2))
                self.assertEqual(lang, data["lang"])
                self.assertEqual("13.11.2026" if lang == "pl" else "2026-11-13", data["asOf"])
            self.assertNotEqual(0, run("new", "idea-pl", "--root", tmp, "--date", "2026-11-13")[0])
            self.assertNotEqual(0, run("new", "Bad Slug", "--root", tmp)[0])

    def test_refresh_keeps_the_data_and_swaps_the_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.html"
            old = page(FIXTURE).replace("const GW = 280", "const GW = 999").replace("<title>Drzewa", "<title>Old")
            path.write_text(old, encoding="utf-8")
            data_before = tree.DATA_RE.search(old).group(2).strip()
            self.assertEqual(0, run("refresh", str(path))[0])
            new = path.read_text(encoding="utf-8")
            self.assertEqual(data_before, tree.DATA_RE.search(new).group(2).strip())
            self.assertIn("const GW = 280", new)
            self.assertIn(f"<title>{FIXTURE['title']}</title>", new)
            self.assertEqual([], tree.problems(new)[0])

    def test_register_writes_and_updates_the_row_and_links_reads_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "tree"
            folder.mkdir()
            path = folder / "2026-11-13-idea.html"
            path.write_text(page(FIXTURE), encoding="utf-8")
            self.assertIn("not published yet", run("links", str(path))[1])
            self.assertEqual(0, run("register", str(path), "https://claude.ai/artifact/abc123")[0])
            reg = (folder / "claude-artifacts.md").read_text(encoding="utf-8")
            self.assertIn("# Claude artifacts: tree", reg)
            self.assertRegex(reg, r"\| Drzewa ścigania alimenciarzy \| \[2026-11-13-idea\.html\]\(2026-11-13-idea\.html\) \| "
                                  r"<https://claude\.ai/artifact/abc123> \| \d{4}-\d{2}-\d{2} \|")
            self.assertIn("abc123", run("links", str(path))[1])
            code, out = run("register", str(path), "https://claude.ai/artifact/def456/")
            self.assertEqual(0, code)
            self.assertIn("replaced https://claude.ai/artifact/abc123", out)
            reg = (folder / "claude-artifacts.md").read_text(encoding="utf-8")
            self.assertNotIn("abc123", reg)
            self.assertEqual(1, len([l for l in reg.splitlines() if "def456" in l]))
            self.assertNotEqual(0, run("register", str(path), "https://example.com/x")[0])

    def test_registry_rows_match_the_vdoc_format(self):
        line = "| Plugin suwagent | [2026-10-25-suwagent-plugin.html](2026-10-25-suwagent-plugin.html) | <https://claude.ai/artifact/161bU3trtsnAPpnAAtYJRm> | 2026-10-25 |"
        self.assertTrue(tree.ROW_RE.match(line))


class Template(unittest.TestCase):
    text = tree.TEMPLATE.read_text(encoding="utf-8")

    def test_self_contained_fragment(self):
        found = re.findall(r"<(!doctype|html|head|body)[\s>]", self.text, re.I)
        self.assertEqual([], found, "the artifact publisher wraps the page; it must not carry these tags")

    def test_known_regressions_stay_fixed(self):
        self.assertIn(".frame > span {", self.text)
        self.assertEqual([], re.findall(r"\.frame span\b", self.text), "frame label selector must be .frame > span")
        self.assertEqual([], re.findall(r'class="[^"]*\bsw\b[^"]*\bframe\b', self.text), "legend swatch must not reuse .frame")

    def test_storage_is_wrapped_in_try_catch(self):
        for call in re.findall(r"[^\n]*localStorage[^\n]*", self.text):
            self.assertIn("try", call)

    def test_both_languages_have_the_same_ui_keys(self):
        block = self.text[self.text.index("const UI = {"):self.text.index("function plural")]
        pl = block[block.index("pl: {"):block.index("en: {")]
        en = block[block.index("en: {"):]
        def keys(part):
            return set(re.findall(r"(?:^ {4}|, )(\w+):", part, re.M))
        self.assertGreater(len(keys(pl)), 30)
        self.assertEqual(keys(pl), keys(en))
        self.assertIn("Dopasuj", pl)
        self.assertIn("do sprawdzenia", pl)

    def test_theme_tokens(self):
        self.assertIn(':root:not([data-theme="light"])', self.text)
        self.assertIn(':root[data-theme="dark"]', self.text)


if __name__ == "__main__":
    unittest.main()
