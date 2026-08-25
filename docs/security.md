# Security review — research AI infrastructure lab

**Scope:** Repository and intended Rocky Linux 9 / vLLM lab deployment, reviewed as infrastructure for a **university research** setting.

**Verdict:** This project implements **laboratory safeguards** suitable for a controlled demo or single-tenant research host. It is **not production-secure** and must not be treated as a multi-user university production platform without substantial additional controls.

Related operator notes: [`security/secrets.md`](security/secrets.md), [`security/checklist.md`](security/checklist.md), architecture summary: [`../architecture/security.md`](../architecture/security.md).

---

## Threat model

### Context

A GPU host serves an OpenAI-compatible LLM API (vLLM in a container), provisioned by Ansible. Operators and possibly researchers send prompts and receive completions. The host may sit on a campus research network, a VPN, or behind SSH tunnels.

### Adversaries (research-relevant)

| Adversary | Interest |
|-----------|----------|
| Curious peer on the same VLAN | Unauthenticated API use, GPU hogging, reading others’ prompts |
| Compromised student laptop | Pivot via SSH keys or tunnel to the inference host |
| Internet scanner (if mis-bound) | Abuse open inference ports; cryptomining / prompt spam |
| Supply-chain attacker | Malicious container tag, poisoned model weights, dependency trojan in CI tools |
| Insider with sudo | Full host control (accepted for lab admins; unacceptable as the only control in multi-tenant prod) |

### In-scope abuse cases

- Unauthorized inference (cost, GPU DoS, policy/license violations)
- Exfiltration of research prompts/completions (unpublished data, personal data in prompts)
- Theft of Hugging Face / registry tokens
- Host compromise via SSH, container escape, or privileged GPU device access
- Tampered models producing unreliable or malicious research outputs

### Out of scope for this lab design

- Formal accreditation (ISO, SOC2)
- Defending a nation-state APT on the HPC fabric
- Multi-tenant strong isolation between research groups on one GPU

---

## Assets

| Asset | Confidentiality | Integrity | Availability | Notes |
|-------|-----------------|-----------|--------------|-------|
| Host root / sudo | Critical | Critical | High | Ansible uses `become: true` |
| SSH private keys / Vault password | Critical | Critical | High | Operator workstation |
| Hugging Face / registry tokens | High | High | Medium | Gated models, pulls |
| Model weights & cache | Medium–High | High | Medium | License + research IP |
| Prompts & completions | High (context-dependent) | Medium | Medium | May contain unpublished or personal data |
| Inference API endpoint | — | Medium | High | Abuse = availability + data risk |
| Inventory / group_vars | Medium | High | Low | Topology + config |
| CI workflows / dev deps | Low | High | Low | Supply chain into maintainer machines |

---

## Trust boundaries

```
[Operator laptop] --SSH/Ansible--> [GPU host OS]
                                      |
                                      +-- firewalld / bind address
                                      |
                                      +-- systemd (root) --> podman/docker
                                                              |
                                                              +-- vLLM container (GPU devices)
                                                                    |
                                                                    +-- OpenAI-compatible HTTP API
                                                                          ^
                                                                          |
                                                               [Clients: curl, SDK, peers]
```

| Boundary | What crosses it | Lab assumption |
|----------|-----------------|----------------|
| Internet ↔ campus | Optional; should not publish vLLM publicly | Lab default: no public bind |
| Campus LAN ↔ host | SSH; optional private NIC for API | Trusted or VPN’d peers (weak for real multi-user) |
| Host OS ↔ container | Devices, mounts, env (incl. HF token) | Runtime trusted; SELinux often relaxed for GPU |
| API ↔ model weights | Read path / HF download | Operator chose the model |
| CI (GitHub) ↔ repo | No GPU secrets required for Static CI | Do not put Vault/HF tokens in Actions secrets unless vaulted carefully |

**Important distinction:** Lab trust often collapses to “people with SSH can do anything.” A real multi-user university service needs identity, authorization, and audit **inside** the API trust boundary—not only host SSH.

---

## Identified risks

Findings from repository review (code, Ansible, containers, scripts, CI). Severity is relative to a university research deployment.

### 1. Hardcoded credentials — Low (no live secrets found)

- No live passwords, private keys, or HF tokens committed.
- Placeholders only (`REPLACE_WITH_HUGGINGFACE_TOKEN`, empty `HUGGING_FACE_HUB_TOKEN=` in examples).
- `.gitignore` excludes `vault.yml`, `vllm.env`, `.env`, weight files.

**Residual:** Operators can still force-add secrets; examples must never be replaced with real values in git.

### 2. Hugging Face tokens — Medium

- Intended path: Ansible Vault → `vllm_hf_token` → `/etc/vllm/vllm.env` (mode `0640`, root:`vllm`).
- Token passed into the container via environment (`HUGGING_FACE_HUB_TOKEN` / `HF_TOKEN`).
- `diagnose.sh` redacts common token patterns; does not eliminate all leak paths (e.g. verbose upstream logs).

**Residual:** Any process that can read the env file or container inspect output obtains the token. No automatic rotation or short-lived credentials.

### 3. SSH configuration — Medium (lab-hardened, not campus-IdP grade)

Controls present:

- Drop-in hardening under `/etc/ssh/sshd_config.d/`
- `PasswordAuthentication no` by default, refused unless `authorized_keys` exists
- `PermitRootLogin prohibit-password` (root with keys still allowed)
- `AllowUsers` defaults to the Ansible connection user
- `sshd -t` validation before relying on the drop-in

Gaps vs multi-user university hosts:

- No integration with campus SSO / bastion / certificate SSH
- `AllowTcpForwarding yes` (useful for demos; widens pivot via tunnels)
- No fail2ban/crowdsec or central SSH audit shipping in-repo

### 4. Root execution — High (accepted lab trade-off)

- Playbook runs with `become: true`.
- systemd unit starts **rootful** Podman/Docker to attach GPUs.
- Application user `vllm` owns data dirs but does **not** run the engine rootless by default.

**Residual:** Compromise of the service unit or container runtime configuration is effectively host compromise. This is common for GPU labs and **insufficient** as the sole model for shared university production.

### 5. Linux capabilities / container privileges — Medium–High

- No `--privileged` flag in the unit/compose path.
- GPU passed through (`nvidia.com/gpu=all` / `--gpus all`) — broad device trust.
- Podman run uses `--security-opt label=disable` (weakens SELinux confinement for GPU convenience).
- No systematic `--cap-drop ALL` (CUDA/runtime compatibility); capabilities are therefore broader than a typical non-GPU web service.

### 6. Exposed ports & firewall — Medium (defaults sane; misconfig easy)

Defaults:

- Host publish: `vllm_host: 127.0.0.1`, `vllm_port: 8000`
- `vllm_firewall_allow_cidrs: []` → vLLM **not** opened in firewalld
- SSH service allowed (required for admin)

Risks:

- Setting `vllm_host: 0.0.0.0` without CIDR controls exposes the API on all interfaces (Ansible warns).
- Inside the container the process listens on `0.0.0.0`; safety depends entirely on the **host bind** and firewall.
- Optional SSH CIDR rich rules do not remove the zone-level `ssh` allow by default (lockout avoidance).

### 7. Filesystem permissions — Low–Medium (reasonable lab defaults)

- App dirs `0750` for `vllm:vllm`
- `/etc/vllm/vllm.env` and `vllm.json` `0640`
- Model volume mounted **read-only**; cache **read-write**
- Unit scripts under `/usr/local/sbin` are root-owned `0755`

**Residual:** Local users in group `vllm` can read config (and token if present). No separate encryption-at-rest for weights/cache.

### 8. API exposure & authentication — High for multi-user; Low if localhost-only

- vLLM OpenAI-compatible API has **no built-in auth** in this lab wiring.
- Acceptable for SSH-tunnel / localhost demos.
- **Not acceptable** as a shared campus endpoint without a reverse proxy (TLS + authn/authz), rate limits, and audit.

### 9. Supply-chain risk — Medium

| Component | Pinning today | Risk |
|-----------|---------------|------|
| Container image | Tag `vllm/vllm-openai:v0.6.3` | Tag can move; **digest not pinned** |
| `requirements-dev.txt` | Version **ranges** | Reproducible CI but not hash-pinned |
| Host packages | `dnf` `state: latest` when updates enabled | Unattended drift / surprise upgrades |
| NVIDIA / CUDA repos | Opt-in | Third-party trust when enabled |
| Model weights | Operator-chosen HF id / local path | No automated checksum gate in Ansible |

### 10. Model trust — Medium–High (process, not code)

- Default model is a public instruct checkpoint; licensing/compliance is operator-owned.
- No signature verification, SBOM for weights, or “approved model allow-list” enforcement.
- Malicious or replaced weights could alter research conclusions or run unexpected code paths in tokenizer/custom code (depending on load settings).

### 11. Logging of sensitive prompts — Medium

- Container stdout/stderr → journald (`SyslogIdentifier=vllm`).
- Upstream may log request fragments on errors; this lab does **not** add prompt redaction at the journal.
- `diagnose.sh` redacts tokens, **not** prompt/completion text in logs.
- Benchmarks record metrics; default result JSON does not dump full prompts (positive), but custom `--prompt` could still appear in shell history.

### 12. Secrets management — Medium (good pattern, incomplete operationalization)

- Documented Ansible Vault flow; examples only in git.
- No sealed-secrets/SOPS/campus vault integration.
- No forced `ansible-vault` in CI (correct—CI should not need prod secrets).

---

## Existing controls

Laboratory safeguards **present in this repository**:

| Control | Where |
|---------|--------|
| No public API bind by default | `vllm_host: 127.0.0.1` |
| Firewall closed for vLLM unless CIDRs set | `vllm_firewall_allow_cidrs: []` |
| SSH key preference + password-off guard | `roles/security` |
| Secrets excluded from git | `.gitignore`, Vault docs |
| Env file mode `0640` | `roles/vllm` |
| No `--privileged` | systemd / compose |
| Limited systemd restart burst (failures stay visible) | `vllm.service` |
| Driver install opt-in | `nvidia_install_drivers: false` |
| Diagnose redaction for common secret keys | `scripts/diagnose.sh` |
| Static CI without GPU secrets | `.github/workflows/static-ci.yml` |
| Image **tag** pin (not `latest`) | group_vars / defaults |
| Warning on `0.0.0.0` bind | `roles/vllm` tasks |

These reduce foot-guns for a **single-tenant lab**. They do **not** equal a production control set.

---

## Remaining risks

Even when defaults are kept:

1. **Unauthenticated API** as soon as the bind moves off localhost or a peer can reach a private NIC.
2. **Rootful GPU containers** with weakened SELinux labeling — escape or runtime bugs are high impact.
3. **Token and prompt exposure** via journal, backups, and group-readable files.
4. **Supply chain** on floating image tags and unpinned Python CI deps / `dnf latest`.
5. **Shared-lab social/technical gap:** SSH access ≈ full power; no per-user API quotas or project isolation.
6. **Model/legal compliance** not enforced by automation.
7. **No TLS** on the inference port in the default design (relies on SSH tunnel or trusted network).

**This lab is not production-secure.**

---

## Laboratory safeguards vs multi-user university controls

| Topic | Lab (this project) | Real multi-user university environment |
|-------|--------------------|----------------------------------------|
| Who may call the API | Anyone who can reach the bind (often only localhost/SSH) | Authenticated identities (SSO/OIDC), per-project authz |
| Network | Localhost or allowlisted lab VLAN | Private service network, WAF/API gateway, no raw host publish |
| TLS | Optional / via SSH tunnel | Required end-to-end or gateway-terminated with cert management |
| Tenancy | Single trusted operator group | Hard isolation or strong logical isolation + quotas |
| Secrets | Ansible Vault on operator machine | Central secret store, rotation, short-lived tokens |
| Audit | journalctl on the box | Central SIEM, prompt/completion retention policy, DPIA if personal data |
| Images/models | Tag pin + operator judgment | Digest pins, allow-listed models, malware/scan pipeline |
| Patching | Manual / documented | Defined SLAs, change windows, SBOM |
| SSH | Hardened sshd drop-in | Bastion + MFA + certificates; no direct internet SSH to GPU nodes |

---

## Recommended production improvements

Prioritized for a university moving from lab → shared research service:

1. **Put an authenticating reverse proxy** (e.g. nginx/Caddy/Envoy) in front of vLLM: TLS, OIDC/SAML to campus IdP, optional mTLS for services.
2. **Keep inference off the public internet**; prefer private subnets + VPN or campus zero-trust access.
3. **Pin container digests** (`image@sha256:…`) and verify model checksums in automation before serve.
4. **Hash-pin** Python/CI dependencies (`pip-tools`/`uv lock`) and reduce `dnf: latest` to controlled patch windows.
5. **Eliminate HF tokens on disk in plaintext** where possible (pull-through cache with managed identity; or Vault agent rendering short-lived files).
6. **Rootless or dedicated inference user** with minimal device access; revisit SELinux/`label=disable` with proper GPU container policy.
7. **Prompt/completion logging policy**: disable verbose request logging; redact; separate audit store with retention limits; DPA/ethics review if human-subject data appears in prompts.
8. **Rate limits and fair-share** (per user/project) to stop GPU DoS by a single caller.
9. **Central secrets + SSH bastion**; disable direct root login entirely (`PermitRootLogin no`).
10. **Threat detection**: fail2ban/crowdsec on SSH, host IDS, image vulnerability scanning in CI/CD before deploy.
11. **Backup & IR runbooks** that assume token and model theft scenarios, not only “service down.”
12. **Multi-tenant architecture** if multiple groups share GPUs (Kubernetes+DRA/MIG, or separate hosts per trust domain)—do not fake tenancy with a naked OpenAI port.

---

## Review checklist (quick)

| Check | Lab status |
|-------|------------|
| Hardcoded credentials in git | Not found |
| HF token handling | Vault pattern; env `0640`; still plaintext at rest on host |
| SSH hardening | Present; not IdP-grade |
| Root execution | Yes (Ansible + rootful containers) |
| Unnecessary capabilities / privileged | No `--privileged`; GPU + `label=disable` remain powerful |
| Exposed ports | Default localhost only |
| Firewall rules | SSH open; vLLM closed unless CIDRs set |
| Filesystem permissions | Generally least-privilege for a lab |
| API auth | None (lab) |
| Image pin | Tag yes; digest no |
| Dependency pin | Ranges in `requirements-dev.txt` |
| Model trust | Operator-managed |
| Prompt logging | Possible via journal; not fully controlled |
| Secrets management | Documented Vault; not enterprise IAM |

---

*Last reviewed against the repository contents of this lab. Re-review after any change that opens `vllm_host`, adds auth, or introduces new secret channels.*
