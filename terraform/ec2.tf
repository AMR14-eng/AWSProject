# Get latest Ubuntu 22.04 AMIIII
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

# EC2 Instance
resource "aws_instance" "flask_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  subnet_id                   = aws_subnet.public_a.id
  vpc_security_group_ids      = [aws_security_group.ec2_sg.id]
  associate_public_ip_address = true

  key_name             = aws_key_pair.deployer.key_name
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  # SIN user_data - solo la instancia básica
  # Puedes agregar la configuración de la aplicación manualmente después

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