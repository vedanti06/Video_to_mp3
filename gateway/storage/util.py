import os, pika, json, traceback, datetime


def _rabbitmq_connection_parameters():
    host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    user = os.environ.get("RABBITMQ_USER")
    password = os.environ.get("RABBITMQ_PASS")
    if user and password:
        creds = pika.PlainCredentials(user, password)
        return pika.ConnectionParameters(host=host, credentials=creds)
    return pika.ConnectionParameters(host=host)


def _publish_video_job(message):
    queue_name = os.environ.get("VIDEO_QUEUE", "video")
    connection = pika.BlockingConnection(_rabbitmq_connection_parameters())
    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
    finally:
        connection.close()


def upload(f, fs, access, db):
    try:
        data = f.read()
        fid = fs.put(data, filename=f.filename)
    except Exception:
        traceback.print_exc()
        return "internal server error", 500

    message = {
        "video_fid": str(fid),
        "mp3_fid": None,
        "username": access["username"],
    }
    try:
        _publish_video_job(message)
    except Exception:
        traceback.print_exc()
        fs.delete(fid)
        return "Internal server error", 500

    filename = f.filename or "video"
    db.conversions.insert_one(
        {
            "username": access["username"],
            "video_fid": str(fid),
            "mp3_fid": None,
            "filename": filename,
            "status": "processing",
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }
    )

    return {"video_fid": str(fid), "filename": filename}