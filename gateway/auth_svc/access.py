import os, requests


def _auth_base():
    return f"http://{os.environ.get('AUTH_SVC_ADDRESS')}"


def login(request):
    data = request.get_json(silent=True)
    if data and data.get("email") and data.get("password"):
        response = requests.post(
            f"{_auth_base()}/login",
            json={"email": data["email"], "password": data["password"]},
        )
    else:
        auth = request.authorization
        if not auth:
            return None, ({"error": "missing credentials"}, 401)

        response = requests.post(
            f"{_auth_base()}/login",
            auth=(auth.username, auth.password),
        )

    if response.status_code == 200:
        body = response.json()
        return body.get("token"), None
    try:
        err = response.json()
    except Exception:
        err = {"error": response.text}
    return None, (err, response.status_code)


def register(request):
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return None, ({"error": "email and password required"}, 400)

    response = requests.post(
        f"{_auth_base()}/register",
        json={"email": email, "password": password},
    )
    if response.status_code in (200, 201):
        return response.json().get("token"), None
    try:
        err = response.json()
    except Exception:
        err = {"error": response.text}
    return None, (err, response.status_code)


def token(request):
    """
    Validate JWT by calling the auth service's /validate endpoint.
    """
    encoded_jwt = request.headers.get("Authorization")

    if not encoded_jwt:
        return None, ({"error": "missing credentials"}, 401)

    headers = {"Authorization": encoded_jwt}

    response = requests.post(f"{_auth_base()}/validate", headers=headers)

    if response.status_code == 200:
        return response.text, None
    try:
        err = response.json()
    except Exception:
        err = response.text
    return None, (err, response.status_code)
