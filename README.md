# Haj & Pierce Wedding Website

A dark cinematic editorial wedding website built with **Python/Flask**, **Azure OpenAI**, and deployed on **Azure App Service** with full Infrastructure-as-Code via **Terraform**.

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

## Admin Panel

After deploying, visit `/admin/` with an email in the `ADMIN_EMAILS` config to:
- View RSVP dashboard and guest list
- Export RSVPs to CSV
- Edit all website content (couple names, dates, venue, etc.)
- Upload and manage gallery photos
- Moderate guestbook messages

---

## Post-Deployment Checklist

- [ ] Run `python scripts/seed_db.py` to seed default config
- [ ] Visit `/admin/config` and fill in all `[EDIT THIS]` values
- [ ] Upload a hero image via the admin photos page
- [ ] Send a test OTP email to verify SendGrid integration
- [ ] Test AI chat widget end-to-end
- [ ] Set `rsvp_open = true` when ready to accept RSVPs
- [ ] Set `rsvp_open = false` after the RSVP deadline

---

## Security Notes

- All secrets are stored in **Azure Key Vault** and injected as App Service Key Vault references — no secrets are stored in code or environment variables directly.
- OTP codes are **SHA-256 hashed** before storage and compared with `secrets.compare_digest()`.
- Rate limiting is applied to all authentication endpoints.
- File uploads validate extension and content type whitelist.
- HTTPS enforced at Front Door and App Service level.
