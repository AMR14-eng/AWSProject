# Get latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# User data template
data "template_file" "user_data" {
  template = file("${path.module}/user_data.sh")

  vars = {
    db_host           = split(":", aws_db_instance.postgres.endpoint)[0]
    db_port           = "5432"
    db_name           = aws_db_instance.postgres.db_name
    db_user           = var.db_username
    db_password       = var.db_password
    s3_bucket         = aws_s3_bucket.app_bucket.id
    cognito_pool_id   = aws_cognito_user_pool.pool.id
    cognito_client_id = aws_cognito_user_pool_client.client.id
    aws_region        = var.aws_region
  }
}

# EC2 Instance
resource "aws_instance" "flask_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  subnet_id                   = aws_subnet.public_a.id
  vpc_security_group_ids      = [aws_security_group.ec2_sg.id]
  associate_public_ip_address = true

  key_name             = aws_key_pair.deployer.key_name
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  user_data = data.template_file.user_data.rendered

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-flask-server"
  }

  depends_on = [aws_db_instance.postgres]
}

# Elastic IP
resource "aws_eip" "flask_eip" {
  instance = aws_instance.flask_server.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-eip"
  }
}