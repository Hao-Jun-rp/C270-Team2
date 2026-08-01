# Sparkle — Ansible provisioning

Takes a **blank Ubuntu 24.04 machine** to a running Sparkle application
behind an Nginx reverse proxy.

This automates the manual build recorded in `docs/DEPLOYMENT_LOG.md`.
That log is the spec; this playbook is the executable version of it.

## Files

| File | Purpose |
|---|---|
| `playbook.yml` | The playbook |
| `inventory.ini` | Which machine to target |
| `vault.yml` | Encrypted secrets (Ansible Vault) |
| `app_env.j2` | Template that writes the app's `.env` from Vault |
| `nginx_sparkle.j2` | Nginx reverse-proxy site config |

## Running it

```bash
ansible-playbook -i inventory.ini playbook.yml --ask-vault-pass
```

## Proving idempotency

Run it **twice**. The second run must report `changed=0`:

```bash
ansible-playbook -i inventory.ini playbook.yml --ask-vault-pass   # changed=N
ansible-playbook -i inventory.ini playbook.yml --ask-vault-pass   # changed=0
```

That is the difference between infrastructure-as-code and a shell script
written in YAML. A shell script does the work again every time; a
playbook describes a desired state and only acts when reality differs.

Two tasks were written specifically to make this true:

- **Docker Compose runs without `--build`.** Rebuilding the image every
  run would always report "changed".
- **The SSM snap is checked before installing**, rather than installed
  blindly with errors suppressed.

## Editing the vault

```bash
ansible-vault edit vault.yml
```

It holds `website_secret_key` and `website_database_url`.

**Use throwaway values for the VM — never the production Aiven
credentials.** Generate a key with:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

For `website_database_url`, the correct throwaway value is:

```
sqlite:///sparkle.db
```

That makes the app fall back to a SQLite file **inside the container** —
no external database needed, and `/health` and `/listings` still prove
the whole chain. Do **not** invent a fake `mysql+pymysql://...` URL: the
app connects to the database at startup, so a fake MySQL URL crashes
gunicorn on boot and the playbook's health check fails with a confusing
timeout.

Note on logging in to the VM app: the `.env` template sets
`SESSION_COOKIE_SECURE=1` **only when** `certbot_domain` is set (i.e.
real HTTPS exists). On a plain-HTTP VM it stays `0`, otherwise the
browser would refuse to keep the session cookie and login would appear
broken.

## Why this targets a local VM, not production

1. A playbook only proves something if it runs on a **blank** machine.
   Running it against an already-configured server proves nothing.
2. Production is deployed to automatically by the CI pipeline via AWS
   SSM. A playbook writing to it by hand would fight the pipeline.

## Secrets: Vault here, Parameter Store in production

The production server holds **no `.env` file at all** — secrets live in
AWS SSM Parameter Store and are fetched at deploy time using the EC2
instance's IAM role.

A local VM has no IAM role, so it cannot do that. Ansible Vault is the
equivalent mechanism for this environment: secrets encrypted at rest in
the repository, decrypted only on the target machine, written to a file
readable by root alone (`mode: '0600'`).

The application itself is unchanged — it reads environment variables and
doesn't care where they came from. That is what makes the same image run
on a laptop, a VM, and production.

## HTTPS

Skipped unless `certbot_domain` is set in the inventory. Let's Encrypt
proves control of a **domain**, so it cannot issue a certificate for a
bare IP — which a local VM normally is. Production HTTPS was issued with
certbot; see `DEPLOYMENT_LOG.md` Phase 5.
