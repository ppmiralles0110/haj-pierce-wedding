# Haj & Pierce Wedding Website

A dark cinematic editorial wedding website built with **Python/Flask**, **Azure OpenAI**, and deployed on **Azure App Service** with full Infrastructure-as-Code via **Terraform**.

> **Live at:** `https://wedding-prod-app.azurewebsites.net` (served via Azure Front Door with WAF)

---

## Architecture

```
Browser
  │
  ▼
Azure Front Door (CDN + WAF + custom domain + managed TLS)
  │
  ▼
Azure App Service (Python 3.12, gunicorn, Linux)
  │  ├─ Flask application (OTP auth, RSVP, AI chat, gallery, guestbook)
  │  ├─ Key Vault references (secrets injected at runtime)
  │  └─ Managed Identity (no stored credentials)
  │
  ├─► Azure PostgreSQL Flexible Server (Southeast Asia)
  ├─► Azure Blob Storage — photo gallery
  ├─► Azure OpenAI (gpt-4o-mini — Sweden Central)
  ├─► Application Insights + Log Analytics
  └─► Azure Key Vault
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Terraform | >= 1.7.0 |
| Azure CLI | Latest |
| Docker & Docker Compose | Latest |
| SendGrid account | Free tier |

---

## Local Development

### 1. Clone & configure

```bash
git clone https://github.com/ppmiralles0110/haj-pierce-wedding.git
cd haj-pierce-wedding
cp .env.example .env
# Edit .env with your values
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

The app will be available at `http://localhost:8000`.

### 3. Run migrations and seed data

```bash
# In a separate terminal
docker compose exec web flask db upgrade
docker compose exec web python scripts/seed_db.py
```

### 4. Run without Docker (virtualenv)

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
python scripts/seed_db.py
flask run
```

---

## Running Tests

```bash
pytest tests/ -v --cov=app
```

---

## Terraform Infrastructure

### One-time state backend setup

```bash
az group create --name tfstate-rg --location southeastasia
az storage account create --name <UNIQUE_NAME> --resource-group tfstate-rg \
  --location southeastasia --sku Standard_LRS
az storage container create --name tfstate --account-name <UNIQUE_NAME>
```

Edit `terraform/backend.tf` with your storage account name.

### Deploy

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform plan
terraform apply
```

### Estimated Monthly Cost (Southeast Asia, B2 App Service)

| Resource | ~Cost/month |
|----------|------------|
| App Service Plan (B2) | $25 |
| PostgreSQL Flexible (B1ms) | $12 |
| Azure Front Door Standard | $22 |
| Blob Storage (10 GB) | $2 |
| Azure OpenAI (gpt-4o-mini, ~500k tokens) | $0.15 |
| Application Insights (5 GB) | $0 (free tier) |
| Key Vault | $0.03/10k ops |
| **Total** | **~$62–$72/month** |

---

## Custom Domain Setup

1. Set `custom_domain = "your-domain.com"` in `terraform.tfvars`
2. Run `terraform apply`
3. In your DNS registrar, add:
   - `CNAME` → `<front-door-endpoint>.z01.azurefd.net`
   - `TXT` record for validation (shown in Azure Portal → Front Door → Custom Domains)
4. Wait ~10 minutes for the managed certificate to provision

---

## GitHub Actions Setup

Add the following secrets to your GitHub repository (`Settings → Secrets → Actions`):

| Secret | Value |
|--------|-------|
| `AZURE_CREDENTIALS` | Output of `az ad sp create-for-rbac --sdk-auth` |
| `AZURE_APP_NAME` | Your App Service name (e.g. `wedding-prod-app`) |
| `AZURE_RESOURCE_GROUP` | Your resource group name |

CI runs on every push. Deployment only runs on push to `main`.

---

## Features

### Guest Experience
- **Invite-code authentication** — guests log in with their name, email, and the unique 8-character code from their invitation
- **RSVP form** — name, email (validated), Philippine phone number, attendance status, and optional parking request
- **Dress code references** — up to 4 outfit photos each for him and for her on the Details page
- **AI wedding chat** — powered by Azure OpenAI gpt-4o-mini; answers questions about the event
- **Photo gallery** — guests can upload and browse photos stored in Azure Blob Storage
- **Guestbook** — leave a message for the couple, moderated by admins

### Admin Panel
After deploying, visit `/admin/` with an email in the `ADMIN_EMAILS` list — or one granted access from **Admin → Admin Access** — to reach:

| Section | Features |
|---------|---------|
| **Dashboard** | Total Guests, Attending, Declined, Pending, Need Parking, Photos, Guestbook, Chat logs |
| **Guest List** | RSVP table with name, email, status, phone, parking and table columns; "Needs Parking" filter; CSV export |
| **Login Logs** | Login history with IP address and geolocation (latitude/longitude + reverse-geocoded name) |
| **Invites** | Bulk-import a guest list (CSV upload or pasted text) to generate a unique code per person; single-invite form; copy-all and CSV export |
| **Admin Access** | Grant or revoke admin rights by email — no redeploy needed |
| **Config** | Edit couple names, wedding date, venue, RSVP open/close, AI chat system prompt, wedding hashtag, colour scheme, hero image (file upload), dress code photos — 4 for him and 4 for her (file upload) |
| **Photos** | Upload gallery photos; stored to Azure Blob Storage (local: `static/uploads/`) |
| **Guestbook** | Review and delete messages |

### Bulk Invite Import

To invite 100+ guests without creating codes one at a time, go to **Admin → Invites → Bulk Import Guest List**:

1. Download the CSV template, or prepare your own file with a `name` column and an optional `email` column.
2. Upload the CSV — or paste one guest per line into the text box (`Name, email@example.com`).
3. Leave **Skip names that already have a code** ticked to make repeat imports safe.
4. Every new code is generated, highlighted in the table, and can be copied individually, via **Copy All**, or downloaded with **Export CSV**.

Files without a header row are accepted too: the first column is treated as the name and the second, if present, as the email. Up to 1000 guests can be imported at once.

### Granting Admin Access

Admin rights come from two places:

* `ADMIN_EMAILS` — the comma-separated app setting. These are **owner** admins; they always have access and cannot be revoked from the UI.
* **Admin → Admin Access** — grant admin rights to any email address. The change takes effect on that person's next page load; they do not need to log out and back in. Owners and granted admins can both grant and revoke, but nobody can revoke their own access.


### Security Highlights
- All secrets stored in **Azure Key Vault**; injected into App Service via Key Vault references — zero secrets in code or environment variables
- System-assigned **Managed Identity** — no stored credentials anywhere
- Invite codes are validated server-side and can be deactivated at any time
- Admin access is re-checked on **every** admin request, so revocation takes effect immediately
- **Rate limiting** on all authentication endpoints (Flask-Limiter)
- File uploads validate extension and MIME content type whitelist
- **HTTPS enforced** at Front Door and App Service level; TLS 1.2 minimum
- Login geolocation captured for every successful sign-in (IP + Nominatim reverse geocode)

---

## Post-Deployment Checklist

- [ ] Run `flask db upgrade` via SSH or App Service console
- [ ] Run `python scripts/seed_db.py` to seed default config values
- [ ] Visit `/admin/config` and fill in all `[EDIT THIS]` values
- [ ] Upload a hero image and up to 4 dress code photos per group via Admin → Config
- [ ] Import your guest list via Admin → Invites → Bulk Import to generate everyone's code
- [ ] Add any co-hosts via Admin → Admin Access
- [ ] Send a test OTP email to verify SendGrid integration
- [ ] Test the AI chat widget end-to-end
- [ ] Set `rsvp_open = true` when ready to accept RSVPs
- [ ] Set `rsvp_open = false` after the RSVP deadline
