# Cognito User Pool
resource "aws_cognito_user_pool" "pool" {
  name = "${var.project_name}-user-pool"

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # Auto-verified attributes
  auto_verified_attributes = ["email"]

  # User attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                = "tenant_id"
    attribute_data_type = "String"
    required            = false
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 64
    }
  }

  # MFA configuration - CORREGIDOoO0
  mfa_configuration = "OFF"  # ← CAMBIO AQUÍ

  tags = {
    Name = "${var.project_name}-user-pool"
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.pool.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Token validity
  refresh_token_validity = 30
  access_token_validity  = 1
  id_token_validity      = 1

  token_validity_units {
    refresh_token = "days"
    access_token  = "hours"
    id_token      = "hours"
  }
}