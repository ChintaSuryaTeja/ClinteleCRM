# Tests of the Terraform configuration, run with `terraform test`.
#
# They use a fake ("mock") Oracle provider, so they need no Oracle account and
# create nothing: they only check what `terraform plan` would do.
# (tests/test_key.pub is a throwaway public key whose private half was deleted.)

mock_provider "oci" {
  mock_data "oci_core_images" {
    defaults = {
      images = [{ id = "ocid1.image.oc1..ubuntu-test" }]
    }
  }
  mock_data "oci_identity_availability_domains" {
    defaults = {
      availability_domains = [{ name = "AD-1" }, { name = "AD-2" }]
    }
  }
}

variables {
  region              = "ap-mumbai-1"
  compartment_ocid    = "ocid1.tenancy.oc1..test"
  ssh_allowed_cidr    = "203.0.113.7/32"
  ssh_public_key_path = "tests/test_key.pub"
}

run "defaults_stay_within_always_free" {
  command = plan

  assert {
    condition     = oci_core_instance.app.shape == "VM.Standard.A1.Flex"
    error_message = "Only the A1 Flex shape is Always Free at this size."
  }
  assert {
    condition     = oci_core_instance.app.shape_config[0].ocpus <= 4 && oci_core_instance.app.shape_config[0].memory_in_gbs <= 24
    error_message = "CPU or memory is above the Always Free limit."
  }
  assert {
    condition     = oci_core_instance.app.source_details[0].boot_volume_size_in_gbs <= 200
    error_message = "Disk is above the Always Free limit."
  }
  assert {
    condition     = length(oci_budget_budget.free_tier_guard) == 0
    error_message = "No budget alert should be created without an email address."
  }
}

run "only_ssh_is_restricted_and_only_web_ports_are_public" {
  command = plan

  assert {
    condition = alltrue([
      for rule in oci_core_security_list.public.ingress_security_rules :
      rule.source == var.ssh_allowed_cidr
      if try(rule.tcp_options[0].min, 0) == 22
    ])
    error_message = "SSH must only be open to ssh_allowed_cidr."
  }
  assert {
    condition = toset([
      for rule in oci_core_security_list.public.ingress_security_rules :
      rule.tcp_options[0].min
      if rule.source == "0.0.0.0/0" && length(rule.tcp_options) > 0
    ]) == toset([80, 443])
    error_message = "Only ports 80 and 443 may be open to everyone."
  }
}

run "ssh_open_to_the_whole_internet_is_refused" {
  command = plan
  variables { ssh_allowed_cidr = "0.0.0.0/0" }
  expect_failures = [var.ssh_allowed_cidr]
}

run "too_many_cpus_is_refused" {
  command = plan
  variables { ocpus = 8 }
  expect_failures = [var.ocpus]
}

run "too_much_memory_is_refused" {
  command = plan
  variables { memory_gbs = 32 }
  expect_failures = [var.memory_gbs]
}

run "a_private_key_path_is_refused" {
  command = plan
  variables { ssh_public_key_path = "~/.ssh/clientele_ed25519" }
  expect_failures = [var.ssh_public_key_path]
}

run "budget_alert_is_created_when_an_email_is_given" {
  command = plan
  variables {
    budget_alert_email = "owner@example.com"
    tenancy_ocid       = "ocid1.tenancy.oc1..test"
  }

  assert {
    condition     = oci_budget_budget.free_tier_guard[0].amount == 1
    error_message = "The budget should alert on the first dollar."
  }
}
