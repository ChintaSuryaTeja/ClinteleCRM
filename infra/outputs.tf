output "public_ip" {
  description = "The server's public IP address. Point your domain (e.g. DuckDNS) at it."
  value       = oci_core_instance.app.public_ip
}

output "ssh_command" {
  description = "How to log in."
  value       = "ssh -i ~/.ssh/clientele_ed25519 ubuntu@${oci_core_instance.app.public_ip}"
}
