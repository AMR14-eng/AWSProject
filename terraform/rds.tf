# DB Subnet Group
resource "aws_db_subnet_group" "db" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = [
    aws_subnet.public_a.id,
    aws_subnet.public_b.id
  ]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# RDS PostgreSQL Instance - FREE TIER COMPATIBLE
resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-db"
  allocated_storage      = 20
  max_allocated_storage  = 20    # Free Tier: máximo 20GB
  storage_type           = "gp2" # Free Tier: usar gp2 en lugar de gp3
  storage_encrypted      = false # Free Tier: sin encryption
  
  engine                 = "postgres"
  engine_version         = "16.11" # VERSIÓN DISPONIBLE EN us-east-2
  instance_class         = "db.t3.micro"
  
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  
  publicly_accessible    = false
  
  # Free Tier: máximo 1 día de backups
  backup_retention_period = 1
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  skip_final_snapshot    = true
  # final_snapshot_identifier = "${var.project_name}-final-snapshot" # Comentado para Free Tier
  
  # Free Tier: comentar logs de CloudWatch
  # enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  # Free Tier: deshabilitar Performance Insights
  performance_insights_enabled = false
  # performance_insights_retention_period = 7
  
  tags = {
    Name = "${var.project_name}-postgresql"
  }
}