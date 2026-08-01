# Sparkle — Production Deployment Log

**Owner:** Marcus (AWS deployment + security)
**Deployment date:** 31 July 2026
**Live URL:** https://sparkle-team2.duckdns.org

This file has three audiences:

1. **Matthew** — this is the spec for his Ansible playbook. Every command
   below that was run by hand is something the playbook must automate.
2. **The FA demo** — this is the script for explaining the deployment.
3. **Me, in three weeks** — when the server breaks and I've forgotten how it
   was built.

**No real secrets in this file.** Passwords and keys appear as `<PLACEHOLDER>`.
This file is committed to the repo.

---

## Environment facts

| Thing | Value |
|---|---|
| AWS region | ap-southeast-1 (Singapore) |
| AWS account ID | 891858635640 |
| Availability zone | ap-southeast-1a |
| EC2 instance ID | i-01cfeb68e8fa7700f |
| Instance type | t3.micro (2 vCPU, 1 GiB RAM) |
| AMI | ami-03acbba64aef9bf5c — Ubuntu Server 24.04 LTS, 64-bit x86 |
| OS (running) | Ubuntu 24.04.4 LTS |
| Kernel | 7.0.0-1009-aws |
| Root volume | 20 GiB gp3, **encrypted** (KMS key `aws/ebs`), delete-on-termination |
| Security group | `sparkle-web-sg` |
| Key pair | sparkle-prod-key (RSA, .pem) |
| Elastic IP | 52.74.34.114 (alloc `eipalloc-01895413e004450a1`) |
| Private IP | 172.31.44.164 |
| Domain | sparkle-team2.duckdns.org (DuckDNS, free) |
| Docker Engine | 29.7.0 |
| Docker Compose | v5.3.1 |
| Container port | 8000 (gunicorn) |
| Image (current) | `c270sparkleteam2/sparkle:latest` — built and pushed by GitHub Actions |
| Registry | Docker Hub, **public** repo — no `docker login` needed on the server |
| TLS certificate | Let's Encrypt, expires 2026-10-29, auto-renewing |

---

## Phase 0 — Account setup (console only, no commands)

- [x] AWS account created — personal, Basic (free) support plan
- [x] **MFA enabled on the root user** (authenticator app)
- [x] Region set to ap-southeast-1 (Singapore)
- [x] Free-tier usage alerts enabled
- [x] Budget created: US$10/month with email alert
- [x] DuckDNS subdomain claimed: sparkle-team2.duckdns.org

**Why a domain before a server:** Let's Encrypt cannot issue a certificate for
a bare IP address. No domain means no HTTPS. Claiming it first removes the
classic last-minute blocker.

**Note on MFA:** after enrolling, the console refused a second MFA change with
"You need permissions". That was misleading — the real cause is that the
*existing session* pre-dated the MFA enrolment, so it wasn't MFA-authenticated.
Signing out and back in resolved it. On AWS, "you need permissions" sometimes
means "you need to re-authenticate."

---

## Phase 1 — EC2 instance

### Choices made, and why

**Ubuntu 24.04 LTS, not 26.04.** Docker officially supports both, so this
wasn't a compatibility decision. 24.04 was chosen because (a) it has two years
of troubleshooting material behind it versus three months, (b) 26.04 changes
the container runtime defaults, and (c) **environment consistency** — Matthew
builds his Ansible playbook against a local Ubuntu VM, and the playbook, the
container host, and the server should all match. Support runs to 2029, well
past submission.

**t3.micro.** Free-tier eligible; adequate for a Flask app with demo-level
traffic. ~US$8-10/month if not free-tier.

**20 GiB, not the default 8 GiB.** Docker images accumulate — each pulled
version keeps its layers until pruned. 8 GiB runs out and produces confusing
"no space left on device" failures mid-deploy.

**Root volume encrypted at rest** (AWS-managed `aws/ebs` key). Free, no
performance cost. The server holds a `.env` with live database credentials, so
encrypting the disk is a cheap, real mitigation.

**Shutdown behaviour: Stop, not Terminate.** Terminate would permanently
destroy the instance on an accidental shutdown.

**IAM instance profile: intentionally empty for now.** This is where the SSM
Parameter Store work (Phase 6) attaches. Roles can be added to a running
instance, so nothing is lost by deferring it.

### Security group

Named `sparkle-web-sg` (renamed from the default `launch-wizard-1` — the name
cannot be changed after creation, and `launch-wizard-1` documents nothing).

| Port | Source | Why |
|---|---|---|
| 22 | 203.127.180.162/32 (my IP only) | SSH admin access. Restricting to a single address blocks the constant automated scanning that hits port 22 on any public host within minutes of it existing. |
| 80 | 0.0.0.0/0 | HTTP — required publicly; redirects to HTTPS. |
| 443 | 0.0.0.0/0 | HTTPS — the application itself. |

AWS warns about `0.0.0.0/0`. That warning is correct in general but expected
here: a public booking site that only my laptop can reach is not a deployment.
SSH is the port that matters, and it is locked to one address.

*Caveat:* if my home/campus IP changes, SSH will stop working until the rule is
updated. That is the intended trade-off.

### Elastic IP

Allocated and associated with the instance.

**Why:** a default EC2 public IP is released when the instance stops, and a
different one is assigned on start. The DNS record, the TLS certificate, and
(later) UptimeRobot monitoring all point at an address — if it silently changes,
everything breaks with no obvious cause. An Elastic IP pins it.

*Billing note:* AWS charges for Elastic IPs, including unassociated ones
(~US$3.60/month for an address reserved and doing nothing). Covered by the $10
budget alarm.

### DuckDNS

`sparkle-team2.duckdns.org` → 52.74.34.114 (IPv4 only; IPv6 left blank).

### First SSH connection (from Windows PowerShell)

```powershell
# Move the key out of Downloads
mkdir -Force $env:USERPROFILE\.ssh
move "$env:USERPROFILE\Downloads\sparkle-prod-key.pem" "$env:USERPROFILE\.ssh\"

# Lock down permissions — SSH refuses a private key other accounts can read
icacls.exe "$env:USERPROFILE\.ssh\sparkle-prod-key.pem" /inheritance:r
icacls.exe "$env:USERPROFILE\.ssh\sparkle-prod-key.pem" /grant:r "$($env:USERNAME):(R)"

# Connect (username is 'ubuntu' for Ubuntu AMIs; Amazon Linux uses 'ec2-user')
ssh -i "$env:USERPROFILE\.ssh\sparkle-prod-key.pem" ubuntu@sparkle-team2.duckdns.org
```

On Linux/macOS the permissions step is simply `chmod 400 <keyfile>`.

Connecting by domain name rather than IP also confirms DNS resolves correctly.

---

## Phase 2 — Docker on the server

```bash
# 1. Patch first — fresh AMIs are weeks behind on security updates
sudo apt update && sudo apt upgrade -y

# 2. Add Docker's official APT repository
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update

# 3. Install Engine, CLI, containerd, Buildx, Compose v2
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Run docker without sudo (requires logout/login to take effect)
sudo usermod -aG docker ubuntu
exit
# ...reconnect...

# 5. Verify
docker --version          # 29.7.0
docker compose version    # v5.3.1
docker run hello-world
```

**Why Docker's own repository rather than Ubuntu's `docker.io` package:**
the distro package lags well behind upstream. Docker's repo gives current
Engine, Compose v2 (`docker compose`, two words) and Buildx — which is what our
compose file and CI expect. The GPG key lets apt verify the packages genuinely
came from Docker.

**Security note on the `docker` group:** membership is effectively root access
— anyone in it can mount the host filesystem into a container and read or write
anything. Standard on a single-admin server, but a deliberate trade-off, not a
freebie.

---

## Phase 3 — Application source and config

Tristan's CI pipeline is not yet pushing images to Docker Hub, so the image is
**built on the server as a temporary bootstrap**. This is *not* the target
architecture — a production host should only ever pull a built image, never
hold source code or a build toolchain. It exists so the Nginx/TLS work (the
genuinely risky part) could proceed without waiting.

**When the pipeline lands, Phase 3 and the `docker build` in Phase 4 are
replaced by a single `docker pull`. Nothing else changes.**

```powershell
# On my laptop — export ONLY git-tracked files (no venv, no .env, no caches)
git checkout main
git pull origin main
venv\Scripts\activate
python -m pytest                       # never deploy a failing tree
git archive --format=zip HEAD -o $env:USERPROFILE\sparkle-src.zip

scp -i "$env:USERPROFILE\.ssh\sparkle-prod-key.pem" `
    "$env:USERPROFILE\sparkle-src.zip" ubuntu@sparkle-team2.duckdns.org:~/
```

```bash
# On the server
sudo apt install -y unzip
mkdir -p ~/sparkle && cd ~/sparkle
unzip -o ~/sparkle-src.zip
```

The archive deliberately contains **no `.env`** — it is gitignored. Production
config is created directly on the server:

```bash
# Generate a production-only secret key (never reuse the development one)
python3 -c 'import secrets; print(secrets.token_hex(32))'

nano ~/sparkle/.env
```

```
SECRET_KEY=<64-char-random-hex>
DATABASE_URL=mysql+pymysql://avnadmin:<DB_PASSWORD>@<AIVEN_HOST>:<PORT>/defaultdb
MYSQL_SSL_CA=/app/certs/aiven-ca.pem
```

```bash
chmod 600 ~/sparkle/.env      # owner read/write only
```

Notes:
- `MYSQL_SSL_CA` is the path **inside the container**, not on the host.
- `certs/aiven-ca.pem` is committed to the repo on purpose: it is Aiven's
  *public* CA certificate used to verify TLS, not a credential. The password
  lives only in `.env`.
- The database password was **rotated** before going to production, since the
  old one had left local machines more than once.

---

## Phase 4 — Build and run the container

```bash
cd ~/sparkle
docker build -t sparkle-app:local .

docker run -d --name sparkle \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file ~/sparkle/.env \
  -v ~/sparkle/certs:/app/certs:ro \
  sparkle-app:local
```

Flag by flag:

| Flag | Why |
|---|---|
| `-d` | detached — survives the SSH session ending |
| `--restart unless-stopped` | comes back automatically after a reboot or crash |
| `-p 8000:8000` | host 8000 → container 8000 (Nginx will front this) |
| `--env-file` | config injected at runtime, never baked into the image |
| `-v ...:/app/certs:ro` | CA cert mounted read-only so it never enters a pushed image layer |

This mirrors `docker-compose.yml` exactly, which is what Ashish's local stack
and the eventual CI deployment use.

### Verification

```bash
docker ps
curl -I http://localhost:8000/                                            # 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/listings   # 200
curl -s http://localhost:8000/listings | grep -o "<title>.*</title>"
```

`/listings` was used deliberately rather than `/`: it queries the Service
table, so a 200 proves the **whole chain** — gunicorn, Flask, SQLAlchemy, TLS
to Aiven, and Jinja rendering — not merely that Flask started.

Port 8000 is **not** open in the security group, and should not be. It is
reachable only from inside the server; Nginx is the only public entry point.

---

## Phase 5 — Nginx reverse proxy + HTTPS

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/sparkle
```

```nginx
server {
    listen 80;
    server_name sparkle-team2.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/sparkle /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t                  # validate BEFORE reloading
sudo systemctl reload nginx
```

**Why a reverse proxy rather than exposing gunicorn directly:** it terminates
TLS in one place, serves on the standard ports 80/443 without running the app
as root, and keeps the application process off the public internet. The four
`proxy_set_header` lines preserve the real client IP and original protocol —
without them the app sees every request as coming from 127.0.0.1 over plain
HTTP, which breaks logging and can break redirects.

`nginx -t` before every reload: a bad config plus a reload takes the site down.

### TLS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d sparkle-team2.duckdns.org
# ...answered: email, agree to ToS, YES to HTTP->HTTPS redirect

sudo certbot renew --dry-run   # all simulated renewals succeeded
```

Certificate issued by Let's Encrypt, expires **2026-10-29**. Certbot installed
a systemd timer for automatic renewal; the dry run confirms renewal will work
rather than waiting 90 days to find out.

Certbot proves domain control by serving a challenge file over port 80 — which
is exactly why the domain had to exist first and why a bare IP could never
have worked.

---

## Reboot / resilience test

Run deliberately after a pending kernel upgrade was flagged:

```bash
sudo reboot
# wait ~60s, reconnect
docker ps      # sparkle came back on its own — NOT started manually
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/listings   # 200
uname -r       # 7.0.0-1009-aws
```

**Result: passed.** The container restarted automatically via
`--restart unless-stopped`, Nginx restarted via systemd, the Elastic IP
survived, and the app served real data on the new kernel.

"Supposed to restart" and "verified to restart" are different claims. This is
the second.

---

## Known trade-offs (deliberate, not oversights)

| Decision | Trade-off accepted | What production would do |
|---|---|---|
| Aiven IP allowlist left open to all | Anyone can *attempt* to connect; only the password and TLS stop them | Restrict to the app server's Elastic IP, developers behind a VPN. Not done because six teammates connect from changing home/campus networks. |
| `ubuntu` user in the `docker` group | Effectively root on the host | Separate deploy user with a narrower path, or rootless Docker |
| Image built on the production server | Build toolchain and source present on a public host | Pull a signed, scanned image from a registry — this is exactly what Tristan's pipeline replaces it with |
| Demo customer account keeps a simple password | Anyone can log in as a customer | Real accounts only. Kept for demo flow; the **admin** password is not weak. |
| SSH restricted to a single home IP | Breaks when my ISP changes my address | Bastion host or SSM Session Manager |
| `unsafe-inline` allowed in CSP | Injected inline script is not blocked (-20 on Observatory) | Nonce-based CSP; requires refactoring 9 templates owned by 4 people |
| `db.create_all()` instead of migrations | Schema changes need manual coordination on the shared database — a new model column will NOT be added to an existing table, and the live site breaks | Alembic / Flask-Migrate with versioned migrations |
| Deprecation warnings (`datetime.utcnow()`, legacy `Query.get()`) | 80 warnings in the test output; both still function | Migrate to timezone-aware datetimes and `db.session.get()`. Deliberately deferred — churn in shared working code before FA is a functionality-gate risk. |

---

## Things that broke, and the fixes

| Symptom | Cause | Fix |
|---|---|---|
| IAM "Root access management" page errored with "Organization is not in use" | Wrong page — that feature is for AWS Organizations, unrelated to enabling MFA on your own root user | Account menu → Security credentials → Assign MFA device |
| "You need permissions" when re-running MFA setup | First attempt had already succeeded; the session pre-dated enrolment so wasn't MFA-authenticated | Sign out, sign back in |
| Security group rules and storage config reset themselves | Changing the AMI in the launch wizard resets dependent settings | Re-enter them after any AMI change |
| `ssh: Identity file ... not accessible`, then `Permission denied (publickey)` | Key still in Downloads; SSH had no key to authenticate with | Move to `~/.ssh`, apply `icacls` permissions |
| `ssh: connect to host ... port 22: Connection timed out` | My ISP handed me a new IP, so the security group's port-22 rule no longer matched. A *timeout* (rather than "refused" or "permission denied") is the signature of a firewall silently dropping packets. | Security group → Edit inbound rules → re-select **My IP** on the SSH row. Confirm first that the site still loads over HTTPS — if it does, the server is fine and it is only the SSH rule. |

---

## Pre-demo checklist

Run through this the day before the FA demo, not on the morning of.

```bash
# 1. Disk — the most likely slow-burn failure
df -h                       # want well under 80% on /
docker image prune -a       # if tight

# 2. Everything running and answering
docker ps
curl -s -o /dev/null -w "%{http_code}\n" https://sparkle-team2.duckdns.org/listings

# 3. Certificate not close to expiry
sudo certbot certificates   # expires 2026-10-29

# 4. Survives a restart (do this EARLY in the day, not last thing)
sudo reboot
# ...wait, reconnect, re-run checks 2 and 3
```

Also, off the server:

- [ ] SSH still works from **the network I'll demo on** — a campus IP differs
      from my home IP, so update the security group rule *in advance*
- [ ] AWS billing not in arrears; card still valid; budget alarm not firing
- [ ] The image tag pinned for the demo is an explicit version, **not `:latest`**
- [ ] Aiven database password unchanged since the server's `.env` was written
- [ ] DuckDNS record still points at 52.74.34.114

---

## Restart / recovery runbook

Everything is configured to recover automatically. If it does not:

```bash
# 1. Is the container running?
docker ps -a

# 2. If stopped, start it and check why it stopped
docker start sparkle
docker logs sparkle --tail 50

# 3. Is Nginx up?
sudo systemctl status nginx
sudo nginx -t && sudo systemctl reload nginx

# 4. Is the app answering behind the proxy?
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/listings

# 5. Certificate state
sudo certbot certificates

# 6. Disk full? (the most likely slow-burn failure — image layers accumulate)
df -h
docker image prune -a        # removes images not used by a running container
```

**To deploy a new version (current process):**

Wait for the GitHub Actions run on `main` to go green, then:

```bash
docker pull c270sparkleteam2/sparkle:latest
docker stop sparkle && docker rm sparkle
docker run -d --name sparkle --restart unless-stopped -p 8000:8000 \
  --env-file ~/sparkle/.env -v ~/sparkle/certs:/app/certs:ro \
  c270sparkleteam2/sparkle:latest

sleep 5     # gunicorn needs a moment; curling immediately returns 502
curl -s -o /dev/null -w "%{http_code}\n" https://sparkle-team2.duckdns.org/listings
```

To test a candidate image without risking the live site, run it on port 8001
first (see Phase 8) and only swap once it returns 200.

Pin an explicit tag for the demo rather than `:latest` — `latest` moves every
time anyone merges, and it should not move underneath a live demo.

---

## Phase 8 — Switched to the CI-built image (31 Jul 2026)

Until now the server built its own image from source — a temporary bootstrap so
the Nginx/TLS work could proceed before the pipeline existed. Tristan's GitHub
Actions workflow now builds and pushes `c270sparkleteam2/sparkle:latest` to a
**public** Docker Hub repo on every push to `main`, so the server pulls instead
of builds.

**This is the point where the pipeline and the deployment became one system**
rather than two things that happened to exist.

### Tested on a spare port before touching the live site

```bash
docker pull c270sparkleteam2/sparkle:latest

docker run -d --name sparkle-test -p 8001:8000 \
  --env-file ~/sparkle/.env -v ~/sparkle/certs:/app/certs:ro \
  c270sparkleteam2/sparkle:latest

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/listings
```

Running the candidate on 8001 while 8000 stayed live meant a broken image would
have been discovered with the site still up.

### Confirming the image actually contained my change

My cookie hardening was merged to `main` shortly before. Rather than assume CI
had rebuilt, I read the file **inside the image**:

```bash
docker run --rm c270sparkleteam2/sparkle:latest grep -A1 SESSION_COOKIE_SECURE app/config.py
```

An earlier attempt to infer this from `curl -sI /login | grep set-cookie`
returned nothing and proved nothing — a plain GET of the login page doesn't
modify the session, so Flask never sets a cookie. `/dashboard` does (it
redirects with a flash message). Checking the artifact directly is the reliable
test; inferring from a side effect is not.

### The swap

```bash
docker stop sparkle-test && docker rm sparkle-test
docker stop sparkle && docker rm sparkle
docker run -d --name sparkle --restart unless-stopped -p 8000:8000 \
  --env-file ~/sparkle/.env -v ~/sparkle/certs:/app/certs:ro \
  c270sparkleteam2/sparkle:latest
```

Verified:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://sparkle-team2.duckdns.org/listings
# 200
curl -sI https://sparkle-team2.duckdns.org/dashboard | grep -i set-cookie
# Set-Cookie: session=...; Secure; HttpOnly; Path=/; SameSite=Lax
```

### Observed: brief 502 during the swap

The first curl immediately after `docker run` returned **502**. The container
showed `Up Less than a second` — Nginx had nothing to proxy to while gunicorn
was still starting. It returned 200 moments later.

This is a real (small) downtime window in the current deploy process:
stop-then-start means a few seconds where the site is down. The production
answer is a health-checked rolling deploy — start the new container, wait until
it reports healthy, *then* switch traffic — which is where Hao Jun's `/health`
endpoint becomes useful beyond monitoring.

Acceptable for this project; worth naming as a known limitation rather than
pretending the deploy is seamless.

### Interface contract with the pipeline

These values must match across Tristan's Dockerfile/workflow and this server.
Changing any of them without telling the other person breaks production with no
error in the application logs:

| Item | Value |
|---|---|
| Image | `c270sparkleteam2/sparkle` (**not** `sparkle-app`) |
| Tag consumed | `latest` (an immutable `${{ github.sha }}` tag has been requested for demo pinning) |
| Container port | 8000 |
| Entrypoint | gunicorn → `app:create_app()` |
| Env vars | `SECRET_KEY`, `DATABASE_URL`, `MYSQL_SSL_CA`, `SESSION_COOKIE_SECURE` |
| Cert mount | host `~/sparkle/certs` → container `/app/certs` (read-only) |

### Still manual

The pipeline stops at pushing the image. Pulling and restarting on the server is
done by hand. Automating that step (`build → test → deploy`) is the remaining
gap between a Good and a Complete pipeline, and requires either an SSH key in
GitHub secrets or AWS SSM Run Command. To be designed jointly with Tristan,
since it needs credentials for this server.

---

## Phase 6 — Secrets in AWS SSM Parameter Store — DONE (31 Jul 2026)

My **Technical Initiative & Depth** item. The server now holds **no secrets
file at all**; `~/sparkle/.env` has been deleted.

### The problem being solved

`.env` on disk was a permanent plaintext copy of the live database password.
Anyone with server access, a stray backup, or a snapshot could read it. Rotating
it meant hand-editing a file on every host, and there was no record of who read
it or when.

### What was built

**1. A least-privilege IAM policy** (`SparkleProdParameterRead`) — read-only,
scoped to one parameter path:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadSparkleProdParameters",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
      "Resource": "arn:aws:ssm:ap-southeast-1:891858635640:parameter/sparkle/prod/*"
    },
    {
      "Sid": "DecryptWithDefaultSsmKey",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "*",
      "Condition": {
        "StringEquals": { "kms:ViaService": "ssm.ap-southeast-1.amazonaws.com" }
      }
    }
  ]
}
```

No write actions. No `*` on the resource. The `kms:Decrypt` statement is needed
because SecureString values are encrypted — and the `kms:ViaService` condition
restricts that decrypt power to requests arriving *through SSM*, so it cannot be
used against anything else in the account.

**2. An IAM role** (`SparkleProdInstanceRole`) trusting the EC2 service, with
that policy attached, assigned to instance `i-01cfeb68e8fa7700f`.

**3. Two SecureString parameters**, created **from the console** (see below):
`/sparkle/prod/SECRET_KEY` and `/sparkle/prod/DATABASE_URL`.

**4. `deploy.sh`** on the server — fetches both parameters at deploy time,
pulls the image, replaces the container, and polls until the app returns 200
before reporting success.

### Verification

```bash
aws sts get-caller-identity --region ap-southeast-1
# Arn: arn:aws:sts::891858635640:assumed-role/SparkleProdInstanceRole/i-01cfeb68e8fa7700f
```

No `aws configure` was ever run. No access key exists on the machine. The
instance asks the metadata service who it is and receives **temporary,
auto-rotating credentials**. That is the substantive difference from a file on
disk: there is no static secret to steal, and every call is recorded in
CloudTrail against the instance ID.

Negative test — proving the policy actually restricts:

```bash
aws ssm get-parameter --name "/some/other/thing" --region ap-southeast-1
# AccessDeniedException: not authorized to perform ssm:GetParameter
```

### Read-only proved itself in practice

The first attempt at creating the parameters ran `aws ssm put-parameter` **from
the server** and was refused:

```
AccessDeniedException: ... not authorized to perform: ssm:PutParameter
```

That is the policy working as designed, not a fault. **Writing a secret is an
administrator action; reading one is the application's action.** They belong to
different identities, and the web server only has the second. If this server
were compromised, an attacker could read these two values and could *not*
overwrite production credentials or read anything else in the account.

Parameters are therefore created and rotated **from the console by an
administrator**. Granting `ssm:PutParameter` to the instance to make one command
convenient would have quietly destroyed the property this whole item claims.

### Rotation, demonstrated

`SECRET_KEY` was rotated during setup (the stored value was found to be 28
characters rather than the expected 64 — a bad paste). The fix was: edit the
value in the console, re-run `./deploy.sh`. One console edit, one command, no
files touched, no image rebuilt. Under the old `.env` model the same change
meant hand-editing a file on every host.

Rotating the session key logs everyone out, since it signs session cookies —
expected, and harmless here.

### Final proof

```bash
rm ~/sparkle/.env
./deploy.sh          # -> got SECRET_KEY (64 chars) and DATABASE_URL (109 chars)
                     # -> healthy after 3s (HTTP 200)
ls -la ~/sparkle/    # no .env present
```

The application runs with no secrets file anywhere on the server.

### Honest limitation

`docker inspect sparkle` still shows these values, because that is how Docker
environment variables work — `--env-file` had exactly the same property. What
changed is that secrets **no longer persist on disk**: they are fetched at
deploy time, live only in the container's environment, and vanish when it stops.
Rotation is centralised and reads are audited.

Eliminating the `docker inspect` exposure too would mean fetching parameters
inside the container at startup (an entrypoint change to the Dockerfile, which
is Ashish's file) or using a secrets-injection sidecar. Out of scope here, and
the Dockerfile is deliberately not being changed mid-project.

---

## Phase 6b — SSM Run Command (foundation for automated deploys)

Parameter Store lets the instance *read secrets*. Run Command lets AWS *execute
commands on the instance*. Same service family, separate permission — so the
AWS-managed policy `AmazonSSMManagedInstanceCore` was attached to the same role.

The SSM Agent ships on the Ubuntu AMI as a **snap**, not a deb, so the service
is `snap.amazon-ssm-agent.amazon-ssm-agent.service` — not
`amazon-ssm-agent.service`, and its log is not in `/var/log/amazon-ssm-agent/`.
Restarting it after attaching the policy made it register.

Verified in Fleet Manager: instance Online, agent 3.3.4793.0. Then end-to-end
via Run Command with document `AWS-RunShellScript`:

```
sudo -u ubuntu /home/ubuntu/deploy.sh
```

Result: **Success, 0 errors, 7 seconds.**

`sudo -u ubuntu` matters: Run Command executes as **root**, so `$HOME` would
resolve to `/root` and the script would not find the Aiven certificate at
`~/sparkle/certs` — the container would start and then fail to reach the
database.

**Why this route rather than SSH-based deployment:** for GitHub Actions to SSH
in, port 22 would have to be opened to GitHub's runner IP ranges (broad, and
they change) or to the world — undoing the security-group hardening documented
in Phase 1, and requiring a production SSH private key to be stored in GitHub.
With SSM the agent polls **outbound**, so no inbound port opens at all and no
SSH key leaves this machine.

**Remaining piece (with Tristan):** GitHub needs permission to call
`ssm:SendCommand`. Either an IAM user with access keys stored in GitHub secrets,
or GitHub OIDC federation — where GitHub proves its identity to AWS and receives
temporary credentials, so no long-lived AWS keys are stored anywhere. OIDC is
the stronger option and matches the no-static-credentials pattern already used
on the instance.

---

## Phase 9 — Automated deployment via GitHub OIDC + SSM (1 Aug 2026)

The pipeline previously stopped at pushing an image; deploying was manual. It
now runs end to end. **This completes `build -> test -> deploy`.**

```
commit to main
   -> GitHub Actions: pytest -> build image -> push to Docker Hub
   -> GitHub requests an OIDC token
   -> AWS STS returns temporary credentials (no stored keys)
   -> ssm:SendCommand -> SSM Agent on the instance
   -> deploy.sh: fetch secrets from Parameter Store -> pull -> restart -> health check
   -> live site updated
```

**There are no long-lived credentials anywhere in this chain** — not on the
server, not in GitHub.

### Why not SSH from GitHub Actions?

The common approach is an SSH private key in GitHub secrets. Rejected because:

1. GitHub's runners would need inbound access to port 22, meaning opening it to
   GitHub's IP ranges (broad, and they change) or to the world — **undoing the
   security-group hardening in Phase 1**.
2. A production SSH key would have to be stored in GitHub, where anyone with
   repo admin could potentially extract it.

With SSM the agent polls **outbound**. No inbound port opens at all, and port 22
stays restricted to a single IP.

### 1. OIDC identity provider

IAM -> Identity providers -> OpenID Connect:

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

**No thumbprint was required.** AWS now secures OIDC providers by trusting the
root CA anchoring the provider's TLS certificate rather than a pinned
thumbprint, and retrieves it automatically. Many guides still instruct pasting a
thumbprint value; that is out of date.

### 2. Permission policy — `SparkleGitHubDeploy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SendCommandToSparkleInstance",
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ec2:ap-southeast-1:891858635640:instance/i-01cfeb68e8fa7700f",
        "arn:aws:ssm:ap-southeast-1::document/AWS-RunShellScript"
      ]
    },
    {
      "Sid": "ReadCommandResult",
      "Effect": "Allow",
      "Action": ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"],
      "Resource": "*"
    }
  ]
}
```

GitHub can send **one document** to **one instance** and read the result. It
cannot start or stop instances, cannot read Parameter Store secrets, cannot
touch anything else in the account.

### 3. Role — `SparkleGitHubActionsRole`

Trust policy scoped to a single repository **and branch**:

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:Hao-Jun-rp/C270-Team2:ref:refs/heads/main"
  }
}
```

**The `sub` condition is the most important line in the entire setup.** Without
it — or with a wildcard — any GitHub Actions workflow, in any repository
anywhere, could assume this role. Scoping it to `refs/heads/main` also means
pull requests and forks cannot deploy.

### 4. Workflow side (Tristan)

Requires `id-token: write` permission so the runner may request an OIDC token,
then `aws-actions/configure-aws-credentials` to exchange it, then
`aws ssm send-command`.

Importantly, the workflow **polls for completion** rather than firing and
forgetting: `send-command` returns as soon as AWS *accepts* the command, so
without polling a failed deployment would still show as a green pipeline — a
passing build sitting on top of a dead site. The workflow now waits, prints the
script's output into the Actions log, and fails the job if the final status is
not `Success`.

### Verified end to end (1 Aug 2026, 07:05:44 GMT)

Tristan pushed a test commit. On the server, with no action from me:

| Evidence | Value |
|---|---|
| Container created | ~1 minute after his push |
| Image ID | `a6c3036a6571` (new — previous was `08025b5c`) |
| SSM command history | Entry at 07:05:44 GMT that I did not create |
| Command output | ends `==> Deploy OK: c270sparkleteam2/sparkle:latest` |
| Container ID in that output | `88c4946ab157...` — matches `docker ps` |
| Duration | 16 seconds |
| Site | HTTP 200 |

**Why the command history is the decisive evidence:** running `deploy.sh`
directly over SSH does *not* appear in SSM command history — AWS isn't involved.
Only commands sent through `ssm:SendCommand` are logged. My own manual runs are
timestamped the previous day (31 Jul, 16:22 and 16:26); the 1 Aug entry can only
have come from the pipeline.

### Consequence for how deployment now works

Manual `deploy.sh` is now a **fallback for when the pipeline is broken**, not
the normal path. Keeping all deployments flowing through SSM means the command
history is a complete audit record of every production change.

---

## Phase 7 — Security headers + cookie hardening — DONE (31 Jul 2026)

Part of my **Technical Initiative & Depth** item. Two layers: HTTP response
headers at the Nginx level, and session-cookie flags at the application level.

### Measured result

| Scanner | Before | After |
|---|---|---|
| securityheaders.com | All 5 headers absent | **A** (all 6 present) |
| Mozilla HTTP Observatory | 70/100, grade B, 8/10 passed | **80/100, grade B+, 9/10 passed** |

Not an assertion — both scans are external, repeatable, and screenshotted.

### Layer 1 — Nginx response headers

Added inside the `listen 443` server block in
`/etc/nginx/sites-available/sparkle`:

```nginx
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'self';" always;
```

| Header | What it prevents |
|---|---|
| `Strict-Transport-Security` | Browser refuses plain HTTP for this host for a year — blocks downgrade attacks |
| `X-Content-Type-Options: nosniff` | Browser won't guess content types in ways attackers exploit |
| `X-Frame-Options: DENY` | Site cannot be embedded in an iframe — blocks clickjacking |
| `Referrer-Policy` | Internal URLs don't leak to third parties via the Referer header |
| `Permissions-Policy` | Explicitly disables browser APIs the app never uses |
| `Content-Security-Policy` | Restricts which origins may supply scripts, styles, images, fonts |

`always` on every line matters: without it, headers attach only to 2xx
responses, so error pages (404/500) would ship unprotected.

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -sI https://sparkle-team2.duckdns.org/ | grep -Ei "strict-transport|x-content-type|x-frame|referrer-policy|permissions-policy|content-security"
```

### Layer 2 — Session cookie flags (`app/config.py`)

Observatory's remaining real finding was a session cookie with no `Secure`
flag. Fixed in application config rather than Nginx, since Flask owns the
cookie:

```python
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
```

| Flag | What it prevents |
|---|---|
| `Secure` | Cookie is never transmitted over plain HTTP |
| `HttpOnly` | JavaScript cannot read the cookie — the main defence against session theft via XSS |
| `SameSite=Lax` | Cookie not sent on cross-site POSTs, which blunts CSRF while leaving normal navigation working |

**Why `Secure` is env-driven rather than hardcoded `True`:** it would break
every teammate's local development over `http://localhost`. A security control
that breaks the team gets reverted; making it environment-aware is what lets it
survive. Enabled in production only, via `SESSION_COOKIE_SECURE=1` in the
server's `.env`.

Because this is application code (not config), it required a rebuilt image —
`.env` alone was not enough. Verified with:

```bash
curl -sI https://sparkle-team2.duckdns.org/login | grep -i set-cookie
```

### Incident during this work: CSP broke the site's fonts

The first CSP was written from a scan of the HTML templates, which found only
one external script (`cdn.jsdelivr.net`, FullCalendar). It missed that
`app/static/theme.css` line 12 pulls Outfit and Work Sans from Google Fonts via
an `@import` inside the CSS. The stricter policy silently blocked it and the
site fell back to system fonts — no error page, nothing in the server logs,
only a browser-console violation.

Fixed by allowing `https://fonts.googleapis.com` in `style-src` (the
stylesheet) and `https://fonts.gstatic.com` in `font-src` (the font files) —
Google splits these across two domains.

**Lesson: a security header that breaks the site is a bug, not a win.** Caught
only because the browser console was checked after deploying, not just the
scanner grade. Scanner score and working application are two separate tests and
both have to pass.

### Deliberate trade-off: `unsafe-inline` in the CSP (-20 on Observatory)

This is the only remaining Observatory deduction, and it is a conscious choice.

Nine templates contain genuine inline `<script>` blocks (dashboard calendar,
booking form JSON payload, reviews, listings, notifications, base). A strict
CSP would require replacing every one with a per-request nonce, which is real
refactoring work across features owned by four different people, with a real
chance of breaking the demo.

`'unsafe-inline'` still blocks a large class of attacks — an attacker cannot
load script from an external origin they control. It does not stop *injected
inline* script. That residual risk is accepted for a student project of this
scope and timeline.

**A scanner deduction I can explain is worth more than a perfect score I
cannot.** The correct production fix is nonce-based CSP.

### Not pursued (and why)

- **HSTS preload** — requires submitting the domain to a browser-maintained
  list. Irreversible on a short timescale and inappropriate for a DuckDNS
  subdomain we don't own long-term.
- **Subresource Integrity (SRI)** on the FullCalendar CDN script — worth doing,
  small; deferred behind higher-value work.
- **Cross-Origin-Resource-Policy / COEP / COOP** — flagged by scanners as
  "upcoming"; no practical benefit for this app's threat model.
