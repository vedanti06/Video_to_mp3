import os, gridfs, json
from flask import Flask, request, send_file, jsonify
from flask_pymongo import PyMongo

from auth_svc import access
from storage import util
from bson.objectid import ObjectId


server=Flask(__name__)
server.config["MONGO_URI"] = os.environ.get(
    "MONGO_URI", "mongodb://host.minikube.internal:27017/videos"
)

mongo=PyMongo(server)
fs=gridfs.GridFS(mongo.db)
fs_mp3s = gridfs.GridFS(mongo.cx["mp3s"])
mp3_files = mongo.cx["mp3s"]["fs.files"]

@server.before_request
def _cors_preflight():
    if request.method == "OPTIONS":
        return "", 204


@server.after_request
def _cors(resp):
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)

    if not err:
        return jsonify({"token": token})
    else:
        body, code = err
        return jsonify(body if isinstance(body, dict) else {"error": body}), code


@server.route("/register", methods=["POST"])
def register():
    token, err = access.register(request)

    if not err:
        return jsonify({"token": token}), 201
    else:
        body, code = err
        return jsonify(body if isinstance(body, dict) else {"error": body}), code


@server.route("/upload", methods=["POST"])
def upload():
    access_payload, err = access.token(request)

    if err:
        body, code = err
        return jsonify(body if isinstance(body, dict) else {"error": body}), code

    claims = json.loads(access_payload)

    if claims["admin"]:
        if len(request.files) > 1 or len(request.files) < 1:
            return "exactly 1 file required", 400

        for _, f in request.files.items():
            out = util.upload(f, fs, claims, mongo.db)
            if isinstance(out, tuple):
                return out
            return jsonify(out), 200
    else:
        return jsonify({"error": "not authorized"}), 401


def _auth_claims():
    access_payload, err = access.token(request)
    if err:
        return None, err
    return json.loads(access_payload), None


def _owned_conversion(username, video_fid):
    return mongo.db.conversions.find_one(
        {"username": username, "video_fid": video_fid}
    )


@server.route("/files", methods=["GET"])
def list_files():
    claims, err = _auth_claims()
    if err:
        body, code = err
        return jsonify(body if isinstance(body, dict) else {"error": body}), code

    username = claims["username"]
    files = []
    for doc in mongo.db.conversions.find({"username": username}).sort(
        "created_at", -1
    ):
        status = doc.get("status", "processing")
        mp3_fid = doc.get("mp3_fid")
        if status == "processing" and not mp3_fid:
            mp3_doc = mp3_files.find_one({"video_fid": doc["video_fid"]})
            if mp3_doc:
                mp3_fid = str(mp3_doc["_id"])
                status = "ready"
                mongo.db.conversions.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"mp3_fid": mp3_fid, "status": "ready"}},
                )

        created = doc.get("created_at")
        files.append(
            {
                "video_fid": doc["video_fid"],
                "mp3_fid": mp3_fid,
                "filename": doc.get("filename", "video"),
                "status": status,
                "created_at": created.isoformat() if created else None,
            }
        )

    return jsonify({"files": files})


@server.route("/status", methods=["GET"])
def status():
    access_payload, err = access.token(request)
    if err:
        body, code = err
        return jsonify(body if isinstance(body, dict) else {"error": body}), code

    video_fid = request.args.get("video_fid")
    if not video_fid:
        return jsonify({"error": "missing video_fid"}), 400

    doc = mp3_files.find_one({"video_fid": video_fid})
    if not doc:
        return jsonify({"ready": False}), 200
    return jsonify({"ready": True, "mp3_fid": str(doc["_id"])}), 200


@server.route("/download", methods=["GET"])
def download():
    claims, err = _auth_claims()
    if err:
        body, code = err
        return jsonify(body if isinstance(body, dict) else {"error": body}), code

    username = claims["username"]
    mp3_fid = request.args.get("mp3_fid")
    video_fid = request.args.get("video_fid")

    if mp3_fid:
        doc = mongo.db.conversions.find_one(
            {"username": username, "mp3_fid": mp3_fid}
        )
        if not doc:
            return jsonify({"error": "not found"}), 404
        try:
            grid_out = fs_mp3s.get(ObjectId(mp3_fid))
        except Exception:
            return jsonify({"error": "not found"}), 404
        name = (doc.get("filename") or "audio").rsplit(".", 1)[0] + ".mp3"
        return send_file(
            grid_out,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=name,
        )

    if video_fid:
        doc = _owned_conversion(username, video_fid)
        if not doc:
            return jsonify({"error": "not found"}), 404
        try:
            grid_out = fs.get(ObjectId(video_fid))
        except Exception:
            return jsonify({"error": "not found"}), 404
        return send_file(
            grid_out,
            mimetype="video/mp4",
            as_attachment=True,
            download_name=doc.get("filename") or "video.mp4",
        )

    return jsonify({"error": "mp3_fid or video_fid required"}), 400


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080)