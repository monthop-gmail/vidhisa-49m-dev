# =============================================
# vidhisa-49m GCP Instance - OpenTofu Config
# =============================================

terraform {
  required_version = ">= 1.11.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.0"

    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 7.0"
    }
  }

  # Backend สำหรับเก็บ state (ใช้ local ถ้ายังไม่มี GCS bucket)
  backend "local" {}
}

# =============================================
# Provider Configuration
# =============================================

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# =============================================
# Variable Definitions
# =============================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-southeast3" # Bangkok
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "asia-southeast3-a"
}

variable "instance_name" {
  description = "VM Instance Name"
  type        = string
  default     = "vidhisa-49m"
}

variable "machine_type" {
  description = "Machine Type"
  type        = string
  default     = "n4-standard-2"
}

variable "boot_disk_size" {
  description = "Boot Disk Size in GB"
  type        = number
  default     = 30
}

variable "source_image" {
  description = "Source Image Family"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
}

# =============================================
# Network Configuration
# =============================================

# Firewall Rules - Open Ports
resource "google_compute_firewall" "allow-ports" {
  name    = "${var.instance_name}-allow-ports"
  network = google_compute_network.vpc_self.name

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443", "8000", "8080", "8081"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = [var.instance_name]
}

# Firewall - Allow ICMP (ping)
resource "google_compute_firewall" "allow-icmp" {
  name    = "${var.instance_name}-allow-icmp"
  network = google_compute_network.vpc_self.name

  allow {
    protocol = "icmp"
  }

  source_ranges = ["0.0.0.0/0"]
}

# Firewall - Allow internal traffic
resource "google_compute_firewall" "allow-internal" {
  name    = "${var.instance_name}-allow-internal"
  network = google_compute_network.vpc_self.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}

# Custom VPC Network
resource "google_compute_network" "vpc_self" {
  name                    = "${var.instance_name}-vpc"
  auto_create_subnetworks = true
  description             = "VPC for vidhisa-49m"
}

# Static IP Address
resource "google_compute_address" "static-ip" {
  name         = "${var.instance_name}-ip"
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"

  # ขอ IP ล่วงหน้าเพื่อไม่ให้เปลี่ยนเมื่อ recreate
  lifecycle {
    create_before_destroy = true
  }
}

# =============================================
# VM Instance
# =============================================

resource "google_compute_instance" "vidhisa" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = [var.instance_name]

  # Boot Disk
  boot_disk {
    initialize_params {
      image = var.source_image
      size  = var.boot_disk_size
    }
  }

  # Network Interface
  network_interface {
    network = google_compute_network.vpc_self.name

    # Static IP from reserved address
    access_config {
      nat_ip = google_compute_address.static-ip.address
    }
  }

  # Scheduling
  scheduling {
    preemptible         = false
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
  }

  # Metadata - Startup Script
  metadata = {
    # Startup script สำหรับติดตั้ง Docker + Timezone
    startup-script = <<-EOF
      #!/bin/bash
      set -e

      echo "========== Starting Setup for vidhisa-49m =========="
      echo "Timestamp: $(date -u)"

      # -----------------------------------------
      # 1. Update & Upgrade System
      # -----------------------------------------
      echo "[1/4] Updating system packages..."
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get upgrade -y

      # -----------------------------------------
      # 2. Set Timezone to Bangkok (Thai)
      # -----------------------------------------
      echo "[2/4] Setting timezone to Asia/Bangkok..."
      timedatectl set-timezone Asia/Bangkok
      timedatectl set-ntp true
      echo "Current timezone: $(timedatectl)"
      echo "Current time: $(date)"

      # -----------------------------------------
      # 3. Install Prerequisites
      # -----------------------------------------
      echo "[3/4] Installing prerequisites..."
      apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        unzip \
        wget \
        git \
        htop \
        make \
        net-tools

      # -----------------------------------------
      # 4. Install Docker Engine
      # -----------------------------------------
      echo "[4/4] Installing Docker Engine..."

      # Add Docker's official GPG key
      install -m 0755 -d /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      chmod a+r /etc/apt/keyrings/docker.gpg

      # Add Docker repository
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

      # Install Docker
      apt-get update -y
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

      # Enable and start Docker
      systemctl enable docker
      systemctl start docker

      # Add ubuntu user to docker group
      usermod -aG docker ubuntu

    EOF
  }

  # Allow deletion protection (prevent accidental deletion)
  deletion_protection = false

  # Labels
  labels = {
    environment = "production"
    project     = "vidhisa-49m"
    managed_by  = "opentofu"
  }
}

# =============================================
# Outputs
# =============================================

output "instance_name" {
  description = "VM Instance Name"
  value       = google_compute_instance.vidhisa.name
}

output "instance_ip" {
  description = "VM External IP Address"
  value       = google_compute_instance.vidhisa.network_interface[0].access_config[0].nat_ip
}

output "instance_zone" {
  description = "VM Zone"
  value       = google_compute_instance.vidhisa.zone
}

output "instance_machine_type" {
  description = "VM Machine Type"
  value       = google_compute_instance.vidhisa.machine_type
}

output "boot_disk_size" {
  description = "Boot Disk Size (GB)"
  value       = google_compute_instance.vidhisa.boot_disk[0].initialize_params[0].size
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "gcloud compute ssh ${var.instance_name} --zone=${var.zone}"
}
