# AI disclosure

Frostfire Installer is developed **with generative AI under human supervision**.
This page says plainly what that means, so users and contributors know what they
are looking at.

## What is AI-generated

- **Most of the source code, tests, packaging and documentation** were drafted
  with AI assistance (large language models) and then reviewed, corrected and
  tested by the maintainer.
- **The visual assets** — the banner, the README/social header, the app icon and
  the concept art — are **AI-generated** images, selected and edited by the
  maintainer.
- The **design, scope and direction** come from the maintainer's own vision and
  experience running Battle.net and World of Warcraft: Forever on Linux.

## Human supervision and responsibility

- The maintainer (**Patrik Nordlund**, [@epatnor](https://github.com/epatnor))
  directs the work, reviews every change, and **runs the tool on real hardware**
  (Bazzite, RTX 3050 Ti laptop + AMD iGPU).
- Nothing is merged unreviewed: the same checks as any project apply — `ruff`,
  `mypy`, `pytest`, and manual testing of the GUI and the Battle.net install
  path. CI runs on every push.
- **The maintainer takes responsibility for the released result.** AI output is
  treated as a first draft, not as truth. Bugs are the maintainer's to fix, not
  "the AI's fault".

## Why disclose

AI-assisted work is still real work, but users have a right to know how a project
is made. Marking it:

- sets honest expectations about review depth and originality;
- makes the human accountability clear;
- avoids passing generated content off as fully hand-written.

## For contributors

AI-assisted contributions are welcome, **provided you**:

- test them and understand what they do before opening a pull request;
- keep them consistent with the project's scope and style;
- disclose in the PR if a change was largely AI-generated and how you verified it;
- never paste secrets, private data or unlicensed material into a model.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`docs/support.md`](support.md).
