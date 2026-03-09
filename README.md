# dotclaude

A curated collection of [Claude Code](https://code.claude.com) plugins, distributed as a [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).

## Plugins

| Plugin | Description |
|--------|-------------|
| **[gh-sdlc](plugins/gh-sdlc/)** | Slightly overkilled GitHub SDLC workflow: issue, project, branch, commit, PR, merge, track |
| **[ccgraft](plugins/ccgraft/)** | Export, import, and restore Claude Code sessions |
| **[hypersaint](plugins/hypersaint/)** | LLM-native repository architecture: hypermodular atoms, progressive disclosure, integrity hashes |

## Installation

Add the marketplace and install individual plugins:

```
/plugin marketplace add Achxy/dotclaude
/plugin install gh-sdlc@dotclaude
/plugin install ccgraft@dotclaude
/plugin install hypersaint@dotclaude
```

## Development

Load a plugin directly for testing:

```bash
claude --plugin-dir ./plugins/gh-sdlc
claude --plugin-dir ./plugins/ccgraft
claude --plugin-dir ./plugins/hypersaint
```

Validate the marketplace:

```bash
claude plugin validate .
```

## Structure

```
dotclaude/
├── .claude-plugin/
│   └── marketplace.json
├── .github/
│   ├── CODEOWNERS
│   └── workflows/
│       └── test.yml
├── plugins/
│   ├── gh-sdlc/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/
│   │   │   ├── gh-sdlc/
│   │   │   ├── commit-policy/
│   │   │   ├── issue-policy/
│   │   │   ├── pr-policy/
│   │   │   └── gh-projects/
│   │   └── agents/
│   │       └── sdlc-shipper.md
│   ├── ccgraft/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/
│   │   │   ├── export-session/
│   │   │   ├── import-session/
│   │   │   └── restore-backup/
│   │   ├── hooks/hooks.json
│   │   ├── scripts/
│   │   └── tests/
│   └── hypersaint/
│       ├── .claude-plugin/plugin.json
│       └── skills/
│           └── hypersaint/
│               ├── references/
│               ├── scripts/
│               └── assets/
├── LICENSE
└── README.md
```

## License

MIT
