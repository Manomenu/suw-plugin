"""Every skill has a valid frontmatter whose name matches its folder; the manifests agree with each other."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "suw"
SKILLS = PLUGIN / "skills"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def frontmatter(path):
    m = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert m, f"{path} has no frontmatter"
    fields = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        assert re.match(r"^[a-z][a-z0-9_-]*: \S", line), f"{path}: not a 'key: value' line: {line!r}"
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


class Skills(unittest.TestCase):
    def test_every_skill_names_itself_after_its_folder_and_says_when_to_use_it(self):
        folders = sorted(p for p in SKILLS.iterdir() if p.is_dir())
        self.assertTrue(folders)
        for folder in folders:
            with self.subTest(skill=folder.name):
                fields = frontmatter(folder / "SKILL.md")
                self.assertEqual(folder.name, fields.get("name"))
                for key in ("description", "when_to_use", "argument-hint"):
                    self.assertIn(key, fields)
                self.assertGreater(len(fields["description"]), 80)
                # Claude Code cuts description + when_to_use at 1,536 characters in the skill listing.
                self.assertLess(len(fields["description"]) + len(fields["when_to_use"]), 1536)
                self.assertLess(len((folder / "SKILL.md").read_text(encoding="utf-8").splitlines()), 500)

    def test_business_plan_tree_triggers_and_paths(self):
        path = SKILLS / "business-plan-tree" / "SKILL.md"
        fields = frontmatter(path)
        for phrase in ("drzewo decyzyjne", "drzewo planu biznesu", "rozrysuj drzewo"):
            self.assertIn(phrase, fields["when_to_use"])
        body = path.read_text(encoding="utf-8")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/business-plan-tree/scripts/tree.py", body)
        self.assertIn("${user_config.publish_mode}", body)
        for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", body):
            self.assertTrue((PLUGIN / ref).exists(), ref)


class Manifests(unittest.TestCase):
    def test_marketplace_and_plugin_names(self):
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("suw-plugin", market["name"])
        self.assertEqual([("suw", "./plugins/suw")], [(p["name"], p["source"]) for p in market["plugins"]])
        self.assertEqual("suw", plugin["name"])
        option = plugin["userConfig"]["publish_mode"]
        self.assertEqual(["artifact", "local"], option["options"])
        self.assertEqual("artifact", option["default"])

    def test_readme_install_lines(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/plugin marketplace add Manomenu/suw-plugin", readme)
        self.assertIn("/plugin install suw@suw-plugin", readme)


if __name__ == "__main__":
    unittest.main()
