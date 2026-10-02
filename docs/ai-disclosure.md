# AI disclosure

Frostfire Installer is developed **with generative AI under human supervision**.

- **AI-generated:** most of the source, tests, packaging and documentation (drafted
  with LLMs, then reviewed, corrected and tested by the maintainer) and all visual
  assets (banner, header, icon, concept art), selected and edited by the maintainer.
- **Human:** design, scope and direction. The maintainer (**Patrik Nordlund**,
  [@epatnor](https://github.com/epatnor)) reviews every change, runs the tool on real
  hardware, and is responsible for the
  released result — AI output is a first draft, and bugs are the maintainer's to fix.
- **Checks:** `ruff`, `mypy`, `pytest` in CI on every push, plus manual testing of the
  GUI and the Battle.net install path.

**Contributors:** AI-assisted contributions are welcome if you test them and
understand them, keep to the project's scope and style, disclose largely
AI-generated changes in the PR with how you verified them, and never paste secrets
or unlicensed material into a model. See [CONTRIBUTING.md](../CONTRIBUTING.md).
