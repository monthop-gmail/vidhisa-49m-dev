# vidhisa-49m GCP Instance

OpenTofu configuration for creating a VM on Google Cloud Platform.

## Specifications

| Resource      | Details                            |
| ------------- | ---------------------------------- |
| Instance Name | `vidhisa-49m`                      |
| Machine Type  | `n4-standard-2` (2 vCPU, 8 GB RAM) |
| Boot Disk     | 30 GB SSD                          |
| OS            | Ubuntu 24.04 Noble                 |
| Static IP     | Reserved                           |

## Open Ports

| Port | Service   |
| ---- | --------- |
| 80   | HTTP      |
| 443  | HTTPS     |
| 8000 | API       |
| 8080 | Dashboard |
| 8081 | Adminer   |

## Quick Start

### 1. Install OpenTofu

```bash
# macOS (Homebrew)
brew install opentofu

# Linux
curl -LO "https://github.com/opentofu/opentofu/releases/download/v1.8.0/tofu_1.8.0_linux_amd64.zip"
unzip tofu_1.8.0_linux_amd64.zip
sudo mv tofu /usr/local/bin/

# Verify
tofu --version
```

### 2. Setup GCP Credentials

```bash
# Option A: Login with gcloud (recommended)
gcloud auth application-default login

# Option B: Service Account Key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 3. Enable GCP APIs

```bash
gcloud services enable \
  compute.googleapis.com \
  containerregistry.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 4. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id
```

```hcl
# terraform.tfvars
project_id = "your-gcp-project-id"
```

### 5. Initialize & Apply

```bash
# Initialize
cd server
tofu init

# Plan (preview resources)
tofu plan -var-file="terraform.tfvars"

# Apply (create resources)
tofu apply -var-file="terraform.tfvars"

# Type "yes" when prompted
```

## Resources Created

1. **Static IP Address** - `vidhisa-49m-ip`
2. **Firewall Rules**:
   - `vidhisa-49m-allow-ports` - opens ports 80,443,8000,8080,8081
   - `vidhisa-49m-allow-icmp` - allow ping
   - `vidhisa-49m-allow-internal` - allow internal traffic
3. **VM Instance** - `vidhisa-49m` (n4-standard-2, 30GB SSD)

## Startup Script

The script runs automatically when the instance is created:

1. Update system packages
2. **Set timezone to Asia/Bangkok (Thailand)**
3. Install prerequisites (curl, git, etc.)
4. **Install Docker Engine** (latest)
5. **Install Docker Compose** v2
6. Display system info when complete

## Outputs

After apply completes:

```
Outputs:

instance_ip = "xx.xx.xx.xx"        # Public IP
ssh_command = "gcloud compute ssh vidhisa-49m --zone=asia-southeast3-a"
```

## SSH to Instance

```bash
# Via gcloud (recommended)
gcloud compute ssh vidhisa-49m --zone=asia-southeast3-a

# Or use IP directly
ssh ubuntu@xx.xx.xx.xx
```

## Deploy vidhisa-49m

```bash
# SSH into instance
gcloud compute ssh vidhisa-49m --zone=asia-southeast3-a

# Clone repo
git clone https://github.com/monthop-gmail/vidhisa-49m.git
cd vidhisa-49m

# Copy env and start
cp .env.example .env
docker compose up -d

# Verify
docker compose ps
```

## Useful Commands

```bash
# View plan
tofu plan -var-file="terraform.tfvars"

# View state
tofu show

# List resources
tofu state list

# Destroy (delete everything)
tofu destroy -var-file="terraform.tfvars"

# Taint/untaint (recreate resource)
tofu taint google_compute_instance.vidhisa
tofu apply

# Import existing resource
tofu import google_compute_instance.vidhisa your-project/asia-southeast3-a/vidhisa-49m
```

## Cost Estimation

| Resource      | Estimated Cost |
| ------------- | -------------- |
| n4-standard-2 | ~$50/month     |
| 30GB SSD      | ~$5/month      |
| Static IP     | ~$7/month      |
| **Total**     | **~$62/month** |

> Stop the instance when not in use to save costs.

## Security Notes

- Firewall opens ports from `0.0.0.0/0` - adjust as needed for your use case
- Uses default service account - consider using a dedicated SA for production
- Consider using IAP (Identity-Aware Proxy) instead of direct SSH for production
- Consider enabling Shielded VM for additional security

## References

- [OpenTofu Docs](https://opentofu.org/docs/)
- [Google Cloud Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCP Compute Engine](https://cloud.google.com/compute/docs)
