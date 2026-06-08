import jwt, datetime, os
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

server = Flask(__name__)

server.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST")
server.config["MYSQL_USER"] = os.environ.get("MYSQL_USER")
server.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD")
server.config["MYSQL_DB"] = os.environ.get("MYSQL_DB")
server.config["MYSQL_PORT"] = int(os.environ.get("MYSQL_PORT", 3306))

mysql = MySQL(server)


def _credentials_from_request():
    """Accept email/password from JSON body or HTTP Basic auth."""
    data = request.get_json(silent=True)
    if data:
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        if email and password:
            return email, password
    auth = request.authorization
    if auth and auth.username and auth.password:
        return auth.username.strip(), auth.password
    return None, None


def _password_ok(stored, provided):
    if stored.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored, provided)
    return stored == provided


def _authenticate(email, password):
    cur = mysql.connection.cursor()
    res = cur.execute("SELECT email, password FROM user WHERE email=%s", (email,))
    if res <= 0:
        return None
    row = cur.fetchone()
    if not _password_ok(row[1], password):
        return None
    return row[0]


@server.route("/login", methods=["POST"])
def login():
    email, password = _credentials_from_request()
    if not email or not password:
        return jsonify({"error": "missing credentials"}), 401

    user_email = _authenticate(email, password)
    if not user_email:
        return jsonify({"error": "invalid credentials"}), 401

    token = createJWT(user_email, os.environ.get("JWT_SECRET"), True)
    return jsonify({"token": token})


@server.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO user (email, password) VALUES (%s, %s)",
            (email, generate_password_hash(password)),
        )
        mysql.connection.commit()
    except Exception:
        return jsonify({"error": "email already registered"}), 409

    token = createJWT(email, os.environ.get("JWT_SECRET"), True)
    return jsonify({"token": token}), 201


@server.route("/validate", methods=["POST"])
def validate():
    encoded_jwt = request.headers.get("Authorization")

    if not encoded_jwt:
        return jsonify({"error": "missing credentials"}), 401

    encoded_jwt = encoded_jwt.split(" ")[1]

    try:
        decoded = jwt.decode(
            encoded_jwt, os.environ.get("JWT_SECRET"), algorithms=["HS256"]
        )
    except Exception:
        return jsonify({"error": "not authorized"}), 403

    return jsonify(decoded), 200


def createJWT(username, secret, authz):
    return jwt.encode(
        {
            "username": username,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(),
            "admin": authz,
        },
        secret,
        algorithm="HS256",
    )


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=5000)
