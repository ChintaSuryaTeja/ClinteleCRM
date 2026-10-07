# Values come from terraform.tfvars (git-ignored; copy terraform.tfvars.example).
#
# The validation rules keep every setting inside Oracle's "Always Free" limits,
# so a typo can't create something that costs money.

variable "oci_profile" {
  description = "Profile name in ~/.oci/config."
  type        = string
  default     = "DEFAULT"
}

variable "region" {
  description = "Your Oracle home region, e.g. ap-mumbai-1. Always Free servers only exist there."
  type        = string
}

variable "compartment_ocid" {
  description = "Where to create things. The tenancy OCID (root compartment) is fine for a personal project."
  type        = string
}

variable "availability_domain_index" {
  description = "Which availability domain (data centre) to use: 0, 1 or 2. Try another if Oracle says it's out of capacity."
  type        = number
  default     = 0
}

variable "ocpus" {
  description = "CPU cores. Always Free allows up to 4 in total."
  type        = number
  default     = 2

  validation {
    condition     = var.ocpus >= 1 && var.ocpus <= 4
    error_message = "Always Free allows 1 to 4 OCPUs."
  }
}

variable "memory_gbs" {
  description = "Memory in GB. Always Free allows up to 24 in total."
  type        = number
  default     = 12

  validation {
    condition     = var.memory_gbs >= 6 && var.memory_gbs <= 24
    error_message = "Use 6 to 24 GB: the app needs about 6, Always Free allows up to 24."
  }
}

variable "boot_volume_gbs" {
  description = "Disk size in GB. Always Free includes 200 GB of block storage in total."
  type        = number
  default     = 100

  validation {
    condition     = var.boot_volume_gbs >= 50 && var.boot_volume_gbs <= 200
    error_message = "Use 50 to 200 GB (the Always Free total is 200)."
  }
}

variable "ssh_public_key_path" {
  description = "Your SSH public key (the .pub file, never the private key)."
  type        = string
  default     = "~/.ssh/clientele_ed25519.pub"

  validation {
    condition     = endswith(var.ssh_public_key_path, ".pub")
    error_message = "Point this at the public key, the file ending in .pub."
  }
}

variable "ssh_allowed_cidr" {
  description = "Who may connect over SSH: your own IP address followed by /32, e.g. 203.0.113.7/32."
  type        = string

  validation {
    condition     = var.ssh_allowed_cidr != "0.0.0.0/0" && can(cidrhost(var.ssh_allowed_cidr, 0))
    error_message = "Use your own IP/32. Opening SSH to the whole internet (0.0.0.0/0) invites constant break-in attempts."
  }
}

variable "repository_url" {
  description = "Public Git repository the server copies the deploy files from."
  type        = string
  default     = "https://github.com/ChintaSuryaTeja/ClinteleCRM.git"
}

variable "budget_alert_email" {
  description = "Optional: an email address warned if the account ever starts costing money. Empty = no alert."
  type        = string
  default     = ""
}

variable "tenancy_ocid" {
  description = "Needed only for the budget alert (budgets live at the tenancy level)."
  type        = string
  default     = ""
}
