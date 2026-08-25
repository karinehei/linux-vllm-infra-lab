# Security operator checklist

- [ ] API not exposed to the public internet by default
- [ ] Firewall allowlist reviewed
- [ ] SSH key-only auth
- [ ] Secrets via Vault / env files outside git — see [secrets.md](secrets.md)
- [ ] Image tags pinned for demos
- [ ] SELinux left enforcing unless a documented exception exists
- [ ] `nvidia_install_drivers` left false unless console access is available

Full threat model and lab-vs-production review: [`../security.md`](../security.md).
Architecture summary: [`../../architecture/security.md`](../../architecture/security.md).
NVIDIA flow: [`../nvidia.md`](../nvidia.md).
