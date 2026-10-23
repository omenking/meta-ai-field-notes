# Questions Front Matter Format

Questions asked must contain front-matter.

```sh
---
question:  Is it possible to use Meta Wonder Full Programmatically?
date: 2026-10-23
status: inferred
scope:
  - meta-wonder-full-1.0
  - muse-code-headless-mode
  - muse-sdk
---
```

### Fields Descriptions

**question**: Pose the question you are seeking, keep it concise.

**date**: The date when you opened this question.

**status**: you need to set it only one of the following:

- official	- Explicitly confirmed by Meta through documentation or direct communication.
- verified	- Independently proven through your own reproducible testing.
- inferred	- You have a likely answer supported by evidence, but cannot conclusively prove it.
- unresolved - 	You don't have enough evidence to establish an answer.
- unexplored - Have not attempted to anwser the question.

**scope**: a list that scopes what specific Meta API developer tools, specific model versions, or features.