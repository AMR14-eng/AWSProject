output "ec2_public_ip" {
  description = "Public IP of Flask EC2 instance"
  value       = aws_eip.flask_eip.public_ip
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${aws_eip.flask_eip.public_ip}"
}

output "health_check_url" {
  description = "Health check endpoint"
  value       = "http://${aws_eip.flask_eip.public_ip}/health"
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i ${var.project_name}-key.pem ubuntu@${aws_eip.flask_eip.public_ip}"
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.postgres.db_name
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.pool.id
}

output "cognito_client_id" {
  description = "Cognito App Client ID"
  value       = aws_cognito_user_pool_client.client.id
}

output "s3_bucket_name" {
  description = "S3 bucket for tenant data"
  value       = aws_s3_bucket.app_bucket.id
}

output "connection_info" {
  description = "Complete connection information"
  value       = <<-EOT
    
    ╔═══════════════════════════════════════════════════════════╗
    ║         LabCloud Platform - Connection Info               ║
    ╚═══════════════════════════════════════════════════════════╝
    
    🌐 Application URL: http://${aws_eip.flask_eip.public_ip}
    
    🔍 Health Check: http://${aws_eip.flask_eip.public_ip}/health
    
    🔑 SSH Access:
       ssh -i ${var.project_name}-key.pem ubuntu@${aws_eip.flask_eip.public_ip}
    
    📊 Database: ${aws_db_instance.postgres.endpoint}
    
    🪣 S3 Bucket: ${aws_s3_bucket.app_bucket.id}
    
    🔐 Cognito Pool: ${aws_cognito_user_pool.pool.id}
    
    📝 Logs on EC2:
       - Setup: /var/log/user-data.log
       - Flask: sudo journalctl -u labcloud -f
       - Nginx: sudo tail -f /var/log/nginx/access.log
    
    ⏱️  Wait 5-10 minutes for application to be fully ready
    
  EOT
}