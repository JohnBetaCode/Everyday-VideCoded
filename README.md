# everyday2

> _Short description goes here._

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## About

_What is this project? What problem does it solve? Who is it for?_

---

## Features

- _Feature one_
- _Feature two_
- _Feature three_

---

## Requirements

- _e.g. Python 3.12+_
- _e.g. Docker_
- _e.g. Claude Code CLI_

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd everyday2
```

### 2. Install git hooks

```bash
bash scripts/install-hooks.sh
```

This points git to the tracked `.githooks/` directory. After every commit, the session log at `docs/session-log.md` is automatically updated using the Claude CLI.

> Requires the [Claude Code CLI](https://claude.ai/code) to be installed and authenticated. If it's not available, the hook skips silently and commits still work normally.

### 3. Open in dev container

In VS Code: `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**

---

## Usage

_How do you run or use this project? Include basic examples._

```bash
# example command
```

---

## Configuration

_Describe available settings, environment variables, or config files._

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV_VAR` | `value` | _What it does_ |

See `.env.example` for a full list of environment variables.

---

## Project Structure

```
everyday2/
├── .devcontainer/       # VS Code dev container config
├── .githooks/           # Tracked git hooks
├── docs/                # Project documentation and session log
├── scripts/             # Dev tooling scripts
├── src/                 # Source code
└── requirements.txt     # Python dependencies
```

---

## Contributing

_Guidelines for contributing to this project._

---

## License

_License info goes here._
