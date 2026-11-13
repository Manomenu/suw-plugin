# suw-plugin

Piotr Gugnowski's general Claude Code plugin (`suw`) for personal tools and skills.

## Install

```
/plugin marketplace add Manomenu/suw-plugin
/plugin install suw@suw-plugin
```

## Skills

- `/suw:business-plan-tree [idea, brief file or plan]`: draws interactive decision trees that answer the key
  questions of a business plan (does the business make sense, what blocks it, who pays) as one self-contained
  HTML page in `docs/visual/tree/`, publishes it as a private claude.ai artifact, and keeps editing it when you
  ask ("add a question about licences", "K1 came out yes, here are the sources"). Independent questions get
  their own must-pass tree; the choice of client gets a tree where one path is enough.

Setting `publish_mode` (`/config`): `artifact` (default) also publishes each page as a claude.ai artifact,
`local` keeps it on this machine only.

## Development

Helper scripts use the Python 3 standard library only.

```
python3 -m unittest discover -s tests -v
claude plugin validate .
claude --plugin-dir plugins/suw   # try the plugin without installing it
```

MIT licence.
