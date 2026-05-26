# Getting Started — Step-by-Step Deployment Guide

Follow these steps in order to go from zero to a live wedding website.

---

## Step 1 — Bootstrap Terraform Remote State

Run these commands once before any `terraform` commands:

```bash
az login
az group create --name tfstate-rg --location southeastasia

# Replace <UNIQUE_SA_NAME> with a globally unique name (3-24 chars, lowercase+numbers)
az storage account create \
  --name <UNIQUE_SA_NAME> \
  --resource-group tfstate-rg \
  --location southeastasia \
  --sku Standard_LRS

az storage container create \
  --name tfstate \
  --account-name <UNIQUE_SA_NAME>
```

Edit `terraform/backend.tf` and set `storage_account_name` to your chosen name.

---

## Step 2 — Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Open `terraform.tfvars` and fill in:
- `owner_name` — your name / couple's name
- `db_password` — strong password (min 8 chars)
- `admin_emails` — comma-separated admin email addresses
- `sendgrid_api_key` — from your SendGrid account
- `custom_domain` — your domain, or leave as `null`

---

## Step 3 — Deploy Infrastructure

```bash
terraform init
terraform plan      # Review what will be created (~10 resources)
terraform apply     # Type 'yes' to confirm
```

This takes approximately **5–10 minutes**. Note the outputs:
- `app_service_default_hostname` — your app URL
- `key_vault_uri` — Key Vault URL

---

## Step 4 — Add Secrets to Key Vault

The `terraform apply` automatically stores most secrets. If you need to add or update any:

```bash
# Replace <kv-name> with your Key Vault name from Terraform output
az keyvault secret set --vault-name <kv-name> --name sendgrid-api-key --value "SG.xxx"
az keyvault secret set --vault-name <kv-name> --name admin-emails --value "you@email.com"
```

---

## Step 5 — Push Code to GitHub

```bash
cd ..  # Back to project root
git add -A
git commit -m "Initial commit: complete wedding website"
git branch -M main
git remote add origin https://github.com/ppmiralles0110/haj-pierce-wedding.git
git push -u origin main
# Enter your GitHub username and Personal Access Token when prompted
```

The GitHub Actions CI pipeline will run automatically. Once it passes, deployment to Azure begins.

---

## Step 6 — Seed the Database

After the app is deployed and running:

```bash
# Option A: via Azure CLI (runs on the App Service itself)
az webapp ssh --resource-group wedding-prod-rg --name wedding-prod-app \
  --command "python scripts/seed_db.py"

# Option B: locally (requires DATABASE_URL pointing to Azure PostgreSQL)
DATABASE_URL="postgresql://..." python scripts/seed_db.py
```

---

## Step 7 — Configure the Website Content

1. Visit `https://<your-app>.azurewebsites.net/login`
2. Enter your admin email address
3. Check your inbox for the OTP code
4. Go to **Admin → Configuration** (`/admin/config`)
5. Fill in all fields marked `[EDIT THIS]`:
   - Couple names, wedding date, time
   - Venue name, address, Google Maps URL
   - Dress code, theme, RSVP deadline
   - Wedding hashtag, custom message

---

## Step 8 — Upload Photos

1. In Admin → Photos (`/admin/photos`), upload your engagement or pre-wedding photos
2. Use the **"Generate Caption"** button for AI-written captions
3. Update `hero_image_url` in Admin → Config to your preferred hero photo

---

## Step 9 — Set Up Custom Domain (Optional)

If `custom_domain` was set in Terraform:

1. Log in to your DNS registrar
2. Add a `CNAME` record:
   - **Name**: `@` (apex) or `www`
   - **Value**: `<front-door-endpoint>` (from Terraform output `front_door_endpoint_hostname`)
3. Add the `TXT` record shown in Azure Portal → Front Door → Custom Domains
4. Wait 10–15 minutes for the managed certificate to provision

---

## Step 10 — Go Live!

1. Set `rsvp_open = true` in Admin → Config (or it defaults to `true` from the seed)
2. Share the website URL with your guests
3. Monitor RSVPs in Admin → Guests
4. Export to CSV anytime via Admin → Guests → Export CSV

---

## Useful Commands

```bash
# View live app logs
az webapp log tail --resource-group wedding-prod-rg --name wedding-prod-app

# Run database migrations after a code update
az webapp ssh --resource-group wedding-prod-rg --name wedding-prod-app \
  --command "flask db upgrade"

# Export RSVPs locally
python scripts/export_rsvp.py --output my_guests.csv

# Close RSVPs (via admin panel or directly)
az webapp ssh ... --command "python -c \"from app import create_app; from app.models.wedding_config import WeddingConfig; from app.extensions import db; app=create_app(); app.app_context().push(); WeddingConfig.set('rsvp_open','false'); db.session.commit()\""
```
