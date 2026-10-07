# One Always Free ARM server on its own private network, reachable on ports
# 80 and 443 by everyone and on port 22 (SSH) only from your IP address.

locals {
  # The only Always Free shape big enough for the app (Ampere ARM CPUs).
  shape = "VM.Standard.A1.Flex"
  name  = "clientele"
}

data "oci_identity_availability_domains" "all" {
  compartment_id = var.compartment_ocid
}

# The newest Ubuntu 24.04 image built for this shape.
data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = local.shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# --- Network ------------------------------------------------------------------

resource "oci_core_vcn" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-network"
  cidr_blocks    = ["10.0.0.0/16"]
  dns_label      = local.name
}

resource "oci_core_internet_gateway" "main" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${local.name}-internet"
  enabled        = true
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${local.name}-routes"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.main.id
  }
}

# The cloud firewall: what may reach the server from outside.
resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${local.name}-firewall"

  # The server may connect out anywhere (updates, Docker images, Let's Encrypt, AI API).
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    description = "SSH, only from your IP"
    protocol    = "6" # TCP
    source      = var.ssh_allowed_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    description = "HTTP (redirects to HTTPS; Let's Encrypt domain checks)"
    protocol    = "6"
    source      = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    description = "HTTPS"
    protocol    = "6"
    source      = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }

  ingress_security_rules {
    description = "Lets networks tell the server to send smaller packets (path MTU discovery)"
    protocol    = "1" # ICMP
    source      = "0.0.0.0/0"
    icmp_options {
      type = 3
      code = 4
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.main.id
  display_name      = "${local.name}-public"
  cidr_block        = "10.0.1.0/24"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_security_list.public.id]
}

# --- The server -----------------------------------------------------------------

resource "oci_core_instance" "app" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.all.availability_domains[var.availability_domain_index].name
  display_name        = local.name
  shape               = local.shape

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gbs
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = local.name
  }

  metadata = {
    ssh_authorized_keys = trimspace(file(pathexpand(var.ssh_public_key_path)))
    # First-boot setup: Docker, firewall rules, security updates, auto-deploy.
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      repository_url = var.repository_url
    }))
  }

  lifecycle {
    # A newer Ubuntu image appearing later must not rebuild (and wipe) the server.
    ignore_changes = [source_details[0].source_id, metadata["user_data"]]
  }
}

# --- Safety net: an email if the account ever starts costing money ----------------

resource "oci_budget_budget" "free_tier_guard" {
  count = var.budget_alert_email != "" ? 1 : 0

  compartment_id = var.tenancy_ocid
  display_name   = "${local.name}-should-be-free"
  amount         = 1
  reset_period   = "MONTHLY"
  target_type    = "COMPARTMENT"
  targets        = [var.compartment_ocid]
}

resource "oci_budget_alert_rule" "any_spend" {
  count = var.budget_alert_email != "" ? 1 : 0

  budget_id      = oci_budget_budget.free_tier_guard[0].id
  display_name   = "any-spend"
  type           = "ACTUAL"
  threshold      = 1
  threshold_type = "PERCENTAGE"
  recipients     = var.budget_alert_email
  message        = "The Clientele server account has started costing money. Check for anything outside Always Free."
}
