# RAPP-Network

> **The network layer on top of [`kody-w/RAPP`](https://github.com/kody-w/RAPP).** Project-anchored twins, ad-hoc on-device neighborhoods, fully managed through natural-language chat with your global brainstem. **One drop-in file** materializes the whole thing. **Offline-first** by default.

```
                 ┌─────────────────────────────────────────────┐
                 │  GLOBAL BRAINSTEM  ~/.brainstem/  :7071     │
                 │  (your operator-side AI — talks to you)     │
                 │                                             │
                 │  drop in:  agents/project_twin_agent.py     │
                 └─────────────────────┬───────────────────────┘
                                       │ natural language
                                       │ "hatch a twin for each
                                       │  of my projects, dispatch
                                       │  this question, await…"
                                       ▼
              ┌────────────────────────────────────────────┐
              │   ~/.rapp/twins/<hash>/   (canonical home) │
              │           │                                │
              │  symlink ──┴── <project>/.brainstem/...   │
              │             (project-resident anchor)      │
              └─┬──────────┬──────────┬──────────┬─────────┘
                ▼          ▼          ▼          ▼
              :7074      :7075      :7076      :7077       ...
            project A  project B  project C  project D
              (each its own brainstem on its own port —
               same kernel, project-scoped agents/soul/env)
```

## What's this for

You have N projects. Each project has its own code, its own people, its own context. You want to ask questions like *"scan recent changes in each of my projects and tell me which docs need updates"* — and have one assistant fan that out, let each project's own AI do the project-specific work in its own context, and watch the results stream in.

This repo defines the network protocol for doing that, and ships the single-file reference implementation.

## How it relates to `kody-w/RAPP`

This repo is **one of two sources of truth**:

- [`kody-w/RAPP`](https://github.com/kody-w/RAPP) — the canonical organism spec. Kernel, rappid format, egg lifecycle, neighborhood protocol, federation.
- **this repo** — the project-twin network layer on top. Lifecycle, transport, dispatch/jobs, the canonical drop-in.

Both repos publish schemas. When this repo references one, `kody-w/RAPP` is the authority. `scripts/cross_validate.py` mechanically checks that every schema this repo names is declared (or quoted) in the upstream — the same property the network itself relies on between operator estates: if my view and your view disagree, that's a signal one of us needs an update.

## The single drop-in

`project_twin_agent.py` is everything. ~1300 lines, stdlib-only, contains its companion `ProjectWorkspace` agent embedded as a string. Drop it into any RAPP brainstem's `agents/` folder and the whole network surface is alive.

```bash
# in a working RAPP brainstem install:
cp project_twin_agent.py ~/.brainstem/src/rapp_brainstem/agents/
# done — no other files, no pip installs, no config
```

Then ask your global brainstem in plain English:

```
"hatch a project twin for each subdir of /path/to/my/projects"
"list my project twins"
"dispatch this question to all my project twins: 'what's in your project?'"
"check status of that job"
"chat with bchydro — ask it what agents it has loaded"
```

The agent's verbs (`hatch`, `list`, `boot`, `chat`, `dispatch`, `job_status`, `await_job`, `stop`) are pure transport. The MESSAGE is always natural language. The global LLM composes; the twins' LLMs answer.

## Verbs at a glance

| Verb | What it does |
|---|---|
| `hatch` / `hatch_all` | Mint a project twin from your global brainstem kernel. |
| `list` / `status` | Enumerate every project twin on the device, with port + running state. |
| `boot` / `stop` | Lifecycle. |
| `chat` | Synchronous: send one message to one twin, get its reply. |
| `dispatch` | Async fan-out: send one message to many twins, return a `job_id`. |
| `job_status` | Read kanban from `~/.rapp/jobs/<job_id>/`. |
| `await_job` | Block until all twins are done. |

See [`SPEC.md`](./SPEC.md) for the full contract.

## Offline-first

The agent itself makes zero outbound HTTP calls. Identity, discovery, transport — all local. Pure string derivation for rappids. Pure filesystem scan for the neighborhood. Inter-twin chat is `127.0.0.1` only. The only network egress is whatever LLM each brainstem already talks to.

A device with a cached Copilot token (or whatever LLM your brainstem uses) can spin up the entire network, fan messages across it, and aggregate replies — fully offline as far as this spec is concerned.

## Cross-validation

```bash
python3 scripts/cross_validate.py
# Checks every schema string this repo names against kody-w/RAPP.
# Output: per-check match/drift. Drift is the signal — fix in whichever
# repo is wrong.
```

The script runs against a local clone of `kody-w/RAPP` if it exists, otherwise fetches the relevant spec files from `raw.githubusercontent.com`. Offline run requires the local clone.

## Status

This is **v0**, drafted from a working implementation that ships today as `~/.brainstem/src/rapp_brainstem/agents/project_twin_agent.py`. Iterations will sharpen the schema language and incorporate feedback from `kody-w/RAPP` updates.

## License

BSD-style (matches `kody-w/RAPP`).
