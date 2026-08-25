# Security considerations

Threat model for a **lab / research** inference host. Defaults favor isolation and least surprise; production hardening is layered on deliberately.

## Assets

| Asset | Sensitivity |
|-------|-------------|
| Host root / sudo | Critical |
| SSH keys / Ansible vault passwords | Critical |
| Hugging Face / registry tokens | High |
| Model weights (disk) | Medium–High (license + IP) |
| Inference API (prompts/completions) | Medium (data confidentiality) |
| Metrics/logs | Low–Medium |

## Primary risks

1. **Exposed inference API** on an untrusted network → prompt injection into downstream systems, data exfiltration via completions, resource abuse (GPU DoS).
2. **Unpatched host / driver / container image** → privilege escalation or container escape paths.
3. **Over-privileged containers** (unnecessary `--privileged`, broad device access).
4. **Secrets in git or world-readable files** (API keys, vault files, `.env`).
5. **Model supply chain** (tampered image tags or weight archives).
6. **Shared-lab lateral movement** if the host is a jump point into research networks.

## Controls (v1 intent)

| Control | Approach |
|---------|----------|
| Network exposure | Bind API to localhost or private CIDR; firewalld/nftables allowlists; SSH tunnel for demos |
| Authn to API | Optional bearer token / reverse-proxy auth (document; implement when API is reachable beyond localhost) |
| SSH | Key-only; disable password auth; limited sudo where practical |
| Secrets | Ansible Vault or external secret store; never commit tokens or private keys |
| Containers | Non-root where feasible; drop capabilities; pin image digests when stabilizing |
| SELinux | Keep enforcing; use proper volume/context patterns instead of `setenforce 0` |
| Updates | Document patch cadence for OS, NVIDIA stack, and vLLM image |
| Logging | journald retention; avoid logging full prompts in shared logs if data is sensitive |
| Supply chain | Prefer official/base images; verify checksums for manually downloaded weights |

## Explicit non-controls (v1)

- Full WAF / API gateway product
- Formal mTLS between all clients
- Hardware root of trust / measured boot (nice-to-have for advanced demos)
- Multi-tenant isolation between research groups

## Interview framing

Be ready to discuss:

- Why an OpenAI-compatible endpoint on a GPU box is a **data plane** risk, not “just a model demo”
- How you’d put **nginx/Caddy + TLS + auth** in front without rewriting vLLM
- Difference between **lab-acceptable** exposure (VPN/SSH) and **production** (authz, rate limits, audit)
- Container GPU access vs. giving the workload host-root equivalence

See also: [`../docs/security.md`](../docs/security.md) for the full security review (threat model, risks, lab vs multi-user university controls). Operator checklists: [`../docs/security/`](../docs/security/).
