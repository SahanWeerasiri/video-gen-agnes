# Base Project Template

A clean, standardized starter template pre-configured for modern AI-assisted software engineering (Antigravity, Claude Code, Codex, Cursor).

It includes curated **rules**, **workflows**, **skills**, and **security guardrails** to enforce disciplined development:
```text
plan ➔ test (TDD) ➔ implement ➔ review ➔ verify
```

---

## 🚀 How to Use This Template for a New Project

### Step 1: Duplicate this template
Copy the entire folder into your new project directory:
```bash
cp -r /path/to/base-project /path/to/my-new-project
cd /path/to/my-new-project
```

### Step 2: Select your tech stack rules
In `.agents/rules/`:
1. **Always keep `common/`** (core security, development workflow, testing, and code quality).
2. **Keep only the language/framework folder you are using** (e.g., `typescript`, `python`, `golang`, `react`, etc.).
3. **Delete the unused language folders** to keep your AI context lean and fast.

*Example for a TypeScript project:*
```bash
cd .agents/rules
# Keep common and typescript, delete the rest:
rm -rf angular arkts cpp csharp dart fsharp golang java kotlin nuxt perl php python react-native ruby rust swift vue web
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and fill in any secrets or configuration:
```bash
cp .env.example .env
```
*(Never commit `.env` files to git. `.gitignore` is already pre-configured to block them).*

### Step 4: Enable Pre-Commit Security Hook
Tell Git to use the tracked pre-commit hook:
```bash
git config core.hooksPath .githooks
```
*(This automatically runs Gitleaks to scan for leaked secrets, keys, and accidental `.env` commits before every `git commit`).*

### Step 5: Update Project Information
Replace this `README.md` with your actual project's purpose, architecture, and setup instructions.

---

## 📁 Project Structure

```
.
├── .agents/                      # AI assistant customizations & playbooks
│   ├── rules/                    # Workspace guidelines (common + your tech stack)
│   │   ├── common/               # Security, testing, workflow, and code style
│   │   └── <your-language>/      # Language-specific idiomatic practices
│   ├── skills/                   # High-value on-demand engineering skills
│   │   ├── tdd-workflow/         # Test-driven development enforcement
│   │   ├── security-scan/        # Vulnerability & secret audits
│   │   ├── api-design/           # Clean REST / API contract design
│   │   ├── docker-patterns/      # Production containerization
│   │   └── ...                   # Curated universal software skills
├── .github/                      # CI/CD pipelines & Pull Request templates
│   ├── workflows/                # Security SAST & DAST workflows
│   └── pull_request_template.md  # Enforced PR review checklist
├── .githooks/                    # Tracked git hooks (pre-commit, commit-msg, pre-push)
├── .editorconfig                 # Cross-IDE code formatting & line-ending standards
├── .env.example                  # Clean environment variable starter template
├── .gitignore                    # Universal multi-language gitignore
├── .gitleaksignore               # Secret scanning baseline exclusions
├── docs/                         # Architecture documentation
│   └── adr/                      # Architecture Decision Records (ADRs)
├── AGENTS.md                     # Universal AI pairing guidelines
└── README.md                     # Project documentation & onboarding
```

---

## 🛡️ Core Engineering Principles

* **Security First:** No hardcoded secrets, validate all boundary inputs, parameterize all queries.
* **Plan Before Code:** Formulate an architectural plan and confirm requirements before making large code edits.
* **Test-Driven (TDD):** Reproduce bugs with failing tests before fixing; write unit tests before implementation.
* **Immutability:** Avoid unintended side-effects and in-place mutations.
* **Defensive Verification:** Always run local test suites and linters before marking a task complete.
