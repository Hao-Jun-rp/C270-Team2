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
| Image (current) | `sparkle-app:local` — built on the server, **temporary** |
| Image (target) | `sparkleteam2/sparkle-app:<tag>` from Docker Hub, once Tristan's pipeline pushes |
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

**To deploy a new version (current, temporary process):**

```bash
# laptop: git pull && pytest && git archive && scp
# server:
cd ~/sparkle && unzip -o ~/sparkle-src.zip
docker build -t sparkle-app:local .
docker stop sparkle && docker rm sparkle
docker run -d --name sparkle --restart unless-stopped -p 8000:8000 \
  --env-file ~/sparkle/.env -v ~/sparkle/certs:/app/certs:ro sparkle-app:local
```

**To deploy a new version (target process, once CI pushes images):**

```bash
docker pull sparkleteam2/sparkle-app:<tag>
docker stop sparkle && docker rm sparkle
docker run -d --name sparkle --restart unless-stopped -p 8000:8000 \
  --env-file ~/sparkle/.env -v ~/sparkle/certs:/app/certs:ro \
  sparkleteam2/sparkle-app:<tag>
```

Pin an explicit tag for the demo rather than `:latest` — `latest` moves every
time anyone merges, and it should not move underneath a live demo.

---

## Phase 6 — Secrets to AWS SSM Parameter Store — NOT STARTED

This is my **Technical Initiative & Depth** item (beyond the core brief).

**The problem with the current setup:** `~/sparkle/.env` is a plaintext file on
disk containing the live database password. Anyone with server access or a
stray backup reads it. It cannot be rotated without editing the file by hand on
every host, there is no audit trail of who read it, and it is invisible to any
access-control system.

**The plan:**
1. Store `SECRET_KEY` and `DATABASE_URL` as **SecureString** parameters in SSM
   Parameter Store (encrypted with KMS).
2. Attach an **IAM role** to the instance granting read access to *only*
   `/sparkle/prod/*` — least privilege, no wildcards.
3. Fetch parameters at container start via the instance role, so no long-lived
   credentials exist anywhere on disk.
4. Delete `.env` from the server.

To be filled in when done — commands, the IAM policy JSON, and how it was
verified.

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
