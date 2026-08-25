# Research AI Infrastructure Lab — common operator / CI shortcuts.
# Requires GNU Make + tools on PATH (Ansible, yamllint, ansible-lint, ruff, shellcheck, pytest).
# GPU inference / live benchmarks are NOT covered here — run those on a lab host.

INVENTORY ?= ansible/inventory/hosts.yml
SITE      ?= ansible/playbooks/site.yml
AI        ?= ansible/playbooks/ai-server.yml
MONITOR   ?= ansible/playbooks/monitoring.yml
LIMIT     ?=

ANSIBLE_PLAYBOOK ?= ansible-playbook
ANSIBLE_FLAGS    ?=
ifneq ($(LIMIT),)
ANSIBLE_FLAGS += --limit $(LIMIT)
endif

SHELL_SCRIPTS := \
	scripts/health-check.sh \
	scripts/gpu-status.sh \
	scripts/service-status.sh \
	scripts/disk-status.sh \
	scripts/diagnose.sh \
	scripts/health/check_vllm_api.sh \
	tests/integration/run_on_gpu_host.sh

.PHONY: help install-dev lint yaml-lint ansible-syntax ansible-lint python-lint shell-lint test \
	deploy deploy-ai deploy-monitoring syntax check ci \
	health diagnose smoke-inference

.DEFAULT_GOAL := help

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make <target> [LIMIT=group_or_host]\n\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  %-22s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install-dev: ## Install Python CI/dev deps (requirements-dev.txt)
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements-dev.txt

yaml-lint: ## yamllint (same paths as Static CI)
	yamllint -c .yamllint.yml ansible containers .github/workflows .yamllint.yml .ansible-lint

ansible-syntax: ## ansible-playbook --syntax-check for site / ai / monitoring
	$(ANSIBLE_PLAYBOOK) --syntax-check -i $(INVENTORY) $(SITE)
	$(ANSIBLE_PLAYBOOK) --syntax-check -i $(INVENTORY) $(AI)
	$(ANSIBLE_PLAYBOOK) --syntax-check -i $(INVENTORY) $(MONITOR)

ansible-lint: ## ansible-lint playbooks + roles
	ansible-lint -c .ansible-lint ansible/playbooks ansible/roles

python-lint: ## ruff check scripts / benchmarks / tests
	ruff check scripts benchmarks tests

shell-lint: ## shellcheck ops + integration scripts
	shellcheck $(SHELL_SCRIPTS)

test: ## pytest unit + config validation
	pytest tests/unit -v

lint: yaml-lint ansible-syntax ansible-lint python-lint shell-lint ## All static linters (no pytest)
check: lint test ## Full local Static CI equivalent
ci: check ## Alias for check

syntax: ansible-syntax ## Alias for ansible-syntax

deploy: ## Converge site.yml (optional LIMIT=ai_nodes|monitoring_nodes|host)
	$(ANSIBLE_PLAYBOOK) -i $(INVENTORY) $(SITE) $(ANSIBLE_FLAGS)

deploy-ai: ## Converge site.yml limited to ai_nodes
	$(MAKE) deploy LIMIT=ai_nodes

deploy-monitoring: ## Converge site.yml limited to monitoring_nodes
	$(MAKE) deploy LIMIT=monitoring_nodes

health: ## Run scripts/health-check.sh (on inference host)
	./scripts/health-check.sh

diagnose: ## Run scripts/diagnose.sh (on inference host)
	./scripts/diagnose.sh

smoke-inference: ## Local API smoke test (default http://127.0.0.1:8000)
	python3 scripts/test-inference.py --base-url http://127.0.0.1:8000
