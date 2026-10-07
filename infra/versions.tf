# Terraform describes the server and its network as code, so they can be
# created, changed or rebuilt with one command instead of clicking through
# the Oracle Cloud console.
#
#   terraform init      # downloads the Oracle provider (once)
#   terraform plan      # shows what would be created; changes nothing
#   terraform apply     # creates it (only when you're ready to host)

terraform {
  required_version = ">= 1.6"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 9.8"
    }
  }
}

# Logs in with the API key in ~/.oci/config (create it in the Oracle console:
# Profile -> API keys -> Add API key). Nothing secret is stored in this folder.
provider "oci" {
  config_file_profile = var.oci_profile
  region              = var.region
}
