import json, requests, os
from jose import jwk, jwt
from jose.utils import base64url_decode
from flask import request, g
from functools import wraps

COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
AWS_REGION = os.getenv("COGNITO_REGION") or os.getenv("AWS_REGION", "us-east-2")
JWKS_URL = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json"

_jwks = None

def get_jwks():
    global _jwks
    if _jwks is None:
        r = requests.get(JWKS_URL)
        _jwks = r.json()
    return _jwks

def verify_jwt(token):
    jwks = get_jwks()
    headers = jwt.get_unverified_header(token)
    kid = headers.get('kid')
    key = next((k for k in jwks['keys'] if k['kid'] == kid), None)
    if not key:
        raise Exception("Public key not found in jwks")
    public_key = jwk.construct(key)
    message, encoded_sig = token.rsplit('.', 1)
    decoded_sig = base64url_decode(encoded_sig.encode('utf-8'))
    if not public_key.verify(message.encode("utf8"), decoded_sig):
        raise Exception("Signature verification failed")
    claims = jwt.get_unverified_claims(token)
    # verify token use/issuer/audience/time in production
    if COGNITO_APP_CLIENT_ID and claims.get('aud') != COGNITO_APP_CLIENT_ID:
        raise Exception("Invalid audience")
    return claims

def cognito_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", None)
        if not auth:
            return {"message": "Missing Authorization header"}, 401
        token = auth.split(" ")[1] if " " in auth else auth
        try:
            claims = verify_jwt(token)
            g.cognito_claims = claims
            # assume tenant_id is in custom:tenant_id claim or in subdomain
            return f(*args, **kwargs)
        except Exception as e:
            return {"message": f"Token invalid: {str(e)}"}, 401
    return decorated
