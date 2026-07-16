# RAPP Network Spec

> **Schema:** `rapp-network/1.0` · **Status:** Draft v0 · **Sibling spec:** [`kody-w/RAPP`](https://github.com/kody-w/RAPP) (the canonical organism spec). This document is one of **two sources of truth** for how project-anchored twins organize into ad-hoc on-device neighborhoods. Drift between this file and the relevant sections of the RAPP repo is a signal that one or both need to be updated until they match — the same property the network itself relies on between operator estates.

## 1. Premise

The RAPP organism spec at `kody-w/RAPP` defines the kernel, the rappid identity system, the egg/hatch lifecycle, the neighborhood protocol, and the federation primitives. This document layers on top — it defines how **project-anchored twins** organize into a **fully local, ad-hoc neighborhood** on a single device, managed entirely through **natural-language chat** with the operator's global brainstem.

Three load-bearing properties:

1. **One drop-in file.** The whole network is materialized by a single `project_twin_agent.py` dropped into any brainstem's `agents/` folder. The companion `ProjectWorkspace` agent is embedded inside that file as a string and written to disk per hatch. No second file is required.
2. **Pure transport at the surface.** The agent exposes only verbs — `hatch`, `list`, `boot`, `chat`, `dispatch`, `job_status`, `await_job`, `stop`. The MESSAGE field on every chat/dispatch is the **verbatim** natural-language string the global wants the twin to receive — the same shape as if the user typed it into the twin's own `/chat` UI on its port. No templating, no workflow gating, no presumed schemas. Chatting with a twin through the global is **indistinguishable** from chatting with it directly.
3. **Offline-first, network-optional.** Identity is pure string derivation. Discovery is pure filesystem scan. Inter-twin chat is `127.0.0.1` only. The agent itself makes zero outbound HTTP calls. The only network egress in the whole flow is whatever LLM the twin's brainstem talks to — the same egress that already existed before this network spec.

## 2. Two sources of truth

This repository and `kody-w/RAPP` are siblings. Each is authoritative for its own scope:

| Concern | Authoritative source |
|---|---|
| Kernel (`brainstem.py`), egg format, bond cycle, install path | `kody-w/RAPP` |
| Rappid format, ESTATE_SPEC, NEIGHBORHOOD_PROTOCOL, TWIN_LIFECYCLE_SPEC | `kody-w/RAPP/pages/docs/` |
| Project-twin lifecycle, manifest, transport, dispatch/job state | **this repo** |
| The single-drop-in canonical implementation | **this repo** (`project_twin_agent.py`) |

When this spec references a schema or contract that's defined in `kody-w/RAPP`, the upstream definition wins by quotation, not by transcription. `scripts/cross_validate.py` is the mechanical check that schemas referenced here actually exist there.

## 3. The single drop-in

```
project_twin_agent.py
  ├─ class ProjectTwinAgent(BasicAgent)         — the transport surface
  ├─ verb implementations (hatch, list, boot, chat, dispatch, ...)
  └─ _PROJECT_WORKSPACE_AGENT_SRC = r'''...'''  — embedded companion source
```

Hatching a project twin:
1. Writes the embedded `_PROJECT_WORKSPACE_AGENT_SRC` to `<target>/agents/project_workspace_agent.py`.
2. Copies the global brainstem's kernel files (`brainstem.py`, `local_storage.py`, `start.sh`, `index.html`, etc.) verbatim.
3. Mints / reuses the consolidated **Eternity** rappid `rappid:@<owner>/<slug>:<64hex>` (record schema `rapp/1`; `kind: "project"` lives in the record, not the string) per `kody-w/RAPP/pages/docs/ESTATE_SPEC.md` §1 — never a legacy `v2:` string.
4. Writes `manifest.json` (§6 below) with the chosen `port_hint`.
5. Symlinks `~/.rapp/twins/<rappid-hash>/` to the project anchor so any twin-aware tool finds it.

A device with N projects gets N project-twin workspaces under `~/.rapp/twins/`. Each has a brainstem identical in shape to the global one, scoped to its own project tree and its own port.

## 4. Disk layout (filesystem-as-source-of-truth)

Per [`TWIN_LIFECYCLE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/TWIN_LIFECYCLE_SPEC.md) §2, the filesystem is authoritative. This network introduces no parallel registry. Every fact about every twin can be reconstructed by walking the filesystem.

```
~/.brainstem/                              — operator's brainstem + identity
  rappid.json                              — rapp/1 (operator)
  estate.json                              — `rapp-estate/1.1` (door catalog)
  src/rapp_brainstem/                      — the global brainstem
    agents/project_twin_agent.py           — THIS agent (the network's one drop-in)
    agents/*_agent.py                      — other agents the operator has

~/.rapp/                                   — device-wide twin estate root
  twins/<rappid-hash>/                     — one dir per twin (symlink for project twins)
    rappid.json                            — rapp/1
    manifest.json                          — rapp-twin-manifest/1.0  (§6)
    HATCH_RECEIPT.json                     — provenance
    brainstem.py · soul.md · agents/...    — full brainstem layout
  jobs/<job_id>/                           — one dir per dispatch
    job.json                               — rapp-project-twin-job/1.0  (§8)
    <twin_hash>.json                       — per-twin status (running/complete/failed)

<project>/.brainstem/src/rapp_brainstem/   — the project anchor (symlink target)
```

The canonical twin path is `~/.rapp/twins/<hash>/`. For project twins, that path is a **symlink** to the project anchor. Tools that scan `~/.rapp/twins/` see project twins exactly like egg-hatched ones.

## 5. Identity (`rapp/1`, Eternity form)

Every project twin's rappid is the consolidated **Eternity** form (CONSTITUTION Art. XXXIV.1/XXXVI.1, locked 2026-06-03; identity standard subsumed by `rapp/1` (formerly styled `rapp-eternity/1.0` / `rapp-rappid/2.0`)), verbatim from upstream [`ESTATE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/ESTATE_SPEC.md) §1:

```
rappid:@<owner>/<slug>:<64hex>
```

- `<owner>` is derived from `git remote get-url origin` when available; falls back to the operator's `github` field in `~/.brainstem/rappid.json`; falls back to the literal string `local`.
- `<slug>` (the repo) is derived from the same remote; falls back to `<project-slug>-brainstem`.
- `<64hex>` is a **keyless identity hash** — `Hb("rapp/1:rappid", uuid4)` = `sha256(b"rapp/1:rappid\n"+uuid4)` (§6.2 keyless, domain-separated), computed **independent of the slug**; it is **never** `sha256("<owner>/<slug>")`. The `@<owner>/<slug>` is location sugar; the hash is the sole join key, and `kind` (`"project"`) lives in the `rappid.json` RECORD, **not** the string. Re-hatch is idempotent because it **reuses the stored `rappid.json`** (the hash is preserved, legacy v2 canonicalized on read) — not because the hash is a function of the location.
- `parent_rappid` is the operator's rappid from `~/.brainstem/rappid.json::rappid`.

**Legacy v2 is read-only.** A pre-existing `rappid:v2:project:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>` string is READ forever and **canonicalized on read** to the Eternity form above (hash preserved) — **never emitted**. `project_twin_agent.py` canonicalizes any legacy rappid it re-hatches; `door_address.py::canonicalize_rappid` is the reference.

The rappid IS the global address per [`ESTATE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/ESTATE_SPEC.md) §1. No URL has to resolve for the rappid to be valid. **This is the load-bearing offline guarantee.**

`kind: "project"` is a **ratified** `front_door` kind (ESTATE_SPEC §1, amended 2026-06-02 per CONSTITUTION Art. XLVI.2 to ratify the single-presence kinds already shipped across the kernel, RAR, and this network); the AIBAST twin and others ship with it. The constitutionally-frozen list of valid kinds is in [`ESTATE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/ESTATE_SPEC.md) §1.

## 6. Manifest contract (`rapp-twin-manifest/1.0`)

Every project twin's workspace MUST contain `manifest.json`:

```json
{
  "schema": "rapp-twin-manifest/1.0",
  "rappid": "rappid:@kody-w/bchydro-brainstem:689266b7f523c61c6e9a331c02c745e4bef08a97c6a3f8c4db019edd582a42f0",
  "hash": "689266b7f523c61c6e9a331c02c745e4bef08a97c6a3f8c4db019edd582a42f0",
  "name": "bchydro",
  "kind": "project",
  "port_hint": 7074,
  "anchor_path": "/Users/.../rapp_projects/bchydro/.brainstem/src/rapp_brainstem",
  "url": "http://localhost:7074",
  "updated_at": "2026-05-21T15:58:41Z"
}
```

`port_hint` is how the canonical Twin agent boots the twin. The auto-port-pick algorithm is owned by this repo (this §6 / `project_twin_agent.py::_pick_port`): it scans every `~/.rapp/twins/*/manifest.json::port_hint` and picks the next free port starting at `7073` — no parallel port registry. (Upstream `NEIGHBORHOOD_PROTOCOL.md` §6 covers twin-chat, the social layer — not port allocation.)

## 7. Transport (`rapp-twin-transport/1.0`)

The agent's surface, by verb:

| Verb | Inputs | Effect |
|---|---|---|
| `list` / `status` | — | Returns every project-kind twin in `~/.rapp/twins/`, with running status (via `127.0.0.1:<port>` connect-test). |
| `hatch` | `project_path` | Creates a project twin at `<project_path>/.brainstem/src/rapp_brainstem/`. Idempotent. |
| `hatch_all` | `parent_dir` | Hatches a twin for each non-dotfile subdir. |
| `boot` | `name` | Spawns `./start.sh` in the twin's workspace. Idempotent — returns existing pid if already running. |
| `stop` | `name` | SIGTERM the process bound to the twin's `port_hint`. |
| `chat` | `name`, `message` | POST `message` verbatim to `127.0.0.1:<port>/chat`. Auto-boots if not running. Returns the twin's reply plus its own `agent_logs`. |
| `dispatch` | `message`, `include_twins?` | Spawn one thread per twin, each sends `message` to that twin's `/chat`. Returns `job_id` **immediately**. |
| `job_status` | `job_id?` | Returns kanban: per-twin status from `~/.rapp/jobs/<job_id>/<twin_hash>.json`. Empty `job_id` → latest job. |
| `await_job` | `job_id?`, `timeout?` | Blocks until `complete + failed == total` or `timeout`. |

**`message` is never templated or inspected.** A user (or the global LLM) types whatever they want to ask the twin; the agent relays it verbatim. The twin's own LLM + the twin's own agents decide what to do.

This transport is itself an instance of **Chat Is The Only Wire** (`kody-w/RAPP` [`CONSTITUTION.md`](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md) Article XXV): each twin's `127.0.0.1:<port>/chat` is the universal interface, and every verb above is just a Layer-2 caller relaying the same verbatim chat envelope. The global brainstem's `ProjectTwin` verbs are therefore **not** a new unit or taxonomy — they are a relay, exactly like an MCP host. An MCP client over stdio (via [`kody-w/rapp-mcp`](https://github.com/kody-w/rapp-mcp)'s `rapp_brainstem_mcp.py`, `rapp-mcp-spec/1.0`; or the content-addressed static profile `rapp-static-mcp/1.0`) is a peer Layer-2 caller of the same `/chat` — MCP is transport realizing this wire, not a parallel abstraction. See `kody-w/RAPP` [`ECOSYSTEM.md`](https://github.com/kody-w/RAPP/blob/main/ECOSYSTEM.md) for the ecosystem framing.

## 8. Job state (`rapp-project-twin-job/1.0`)

```
~/.rapp/jobs/<job_id>/
  job.json              { schema, job_id, message, dispatched_at, twins: [{hash, name, port}, ...] }
  <twin_hash>.json      { twin, twin_hash, port, status, started_at, completed_at?, reply?, twin_agent_logs?, error? }
```

`status` ∈ `running | complete | failed`. Twins that haven't started yet have no file (counted as `not_started`).

Job state is on disk. A different process — or a future invocation of the same agent — can read job progress with no shared memory. The kanban is just `os.scandir`.

## 9. Capability discovery

The global brainstem does **not** maintain a registry of twin capabilities. To learn what a twin can do, it chats: *"what can you do?"* The twin's LLM replies based on its loaded agents (which it sees in its own tool schema). The reply is the answer.

This means a twin can grow new agents at any time and the global automatically benefits — its next dispatch carries the same natural-language message, and the twin's LLM composes with whatever agents are currently loaded.

## 10. `ProjectWorkspace` contract (`rapp-twin-workspace/1.0`)

Every project twin gets a `ProjectWorkspace` agent (embedded inside `project_twin_agent.py`). It exposes scoped file + git ops over the **parent project root** (`Path(__file__).resolve().parents[4]`).

| Action | Effect |
|---|---|
| `scan_changes` (`since`) | `git log` scoped to the twin's subdir of the git toplevel. |
| `find_docs` | Markdown enumeration with sensible exclusions (`.git`, `node_modules`, `.brainstem`, etc.). |
| `list_files` (`pattern`) | Glob in the project root with the same exclusions. |
| `read_file` (`path`) | Read one file; refuses paths outside project root; size-capped at 200 KB. |
| `write_file` (`path`, `content`, `apply`) | Write one file. Refuses paths outside project root. **Refuses writes inside `.brainstem/`**. Default `apply=false` returns a dry-run preview only. With `apply=true`, backs up prior content as `<file>.bak.<unix-ts>` and audit-logs to `<brainstem>/workspace_audit.log`. |

## 11. Offline guarantees

The network is functionally offline-clean:

| Operation | Network egress? |
|---|---|
| `list`, `boot`, `stop`, `job_status`, `await_job` | None. Pure filesystem + subprocess. |
| `hatch`, `hatch_all` | None. File copies + uuid mint. No GitHub fetch. |
| `chat`, `dispatch` (the transport itself) | `127.0.0.1` only. |
| Twin's own LLM call (during chat) | Whatever LLM provider that twin's brainstem talks to — outside this spec's scope; same egress that existed before. |
| Twin's `WorkIQ` agent (if it uses it) | Microsoft Graph — feature-network, fails gracefully when offline. |

A device that has the operator's `~/.brainstem/rappid.json` and the global brainstem installed (with cached Copilot token if using Copilot) can use this entire network spec end-to-end with no other network egress.

## 12. Cross-validation rules

`scripts/cross_validate.py` mechanically checks alignment between this repo and `kody-w/RAPP`:

1. Every schema string referenced in this SPEC (`rapp/1`, `rapp-twin-manifest/1.0`, `rapp-project-twin-job/1.0`, etc.) MUST appear at least once in `kody-w/RAPP` source — either declared there or quoted there.
2. The valid-kinds list in `ESTATE_SPEC.md` §1 SHOULD include every `kind` value this spec emits (currently: `project`).
3. The rappid format string in §5 of this spec MUST match the format declared in `ESTATE_SPEC.md` §1 verbatim.
4. File paths this spec references inside `kody-w/RAPP` MUST exist there.

The script outputs `match` / `drift` per check. Drift is the signal that one or both repos need an update; the script doesn't auto-fix.

## 13. Glossary

- **Project twin** — a brainstem instance scoped to one project tree; lives at `<project>/.brainstem/src/rapp_brainstem/` with a symlink at `~/.rapp/twins/<hash>/`.
- **Anchor** — the project-resident path where the twin's files live (`<project>/.brainstem/src/rapp_brainstem/`).
- **The neighborhood** — the set of project twins on one device, discoverable by scanning `~/.rapp/twins/`.
- **Transport** — the agent's verb surface; not a protocol layer, just a relay.
- **Dispatch** — fire-and-track parallel send to many twins; state lands in `~/.rapp/jobs/`.
- **Capability discovery** — asking a twin in plain English what it can do; no registry.
- **Two sources of truth** — this repo and `kody-w/RAPP`; alignment is checked, not assumed.
