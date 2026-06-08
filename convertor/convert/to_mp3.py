import pika, json, tempfile, os, traceback
from bson.objectid import ObjectId
from moviepy import VideoFileClip


def _mark_failed(db_videos, video_fid):
    db_videos.conversions.update_one(
        {"video_fid": video_fid},
        {"$set": {"status": "failed"}},
    )


def start(message, db_videos, fs_videos, fs_mp3s, channel):
    message = json.loads(message)
    video_fid = message["video_fid"]
    video_path = None
    mp3_path = None

    try:
        tf = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        video_path = tf.name
        out = fs_videos.get(ObjectId(video_fid))
        tf.write(out.read())
        tf.close()

        clip = VideoFileClip(video_path)
        if clip.audio is None:
            clip.close()
            _mark_failed(db_videos, video_fid)
            return "video has no audio track"

        mp3_path = os.path.join(tempfile.gettempdir(), f"{video_fid}.mp3")
        clip.audio.write_audiofile(mp3_path, logger=None)
        clip.close()

        with open(mp3_path, "rb") as f:
            data = f.read()

        mp3_fid = fs_mp3s.put(
            data,
            filename=f"{video_fid}.mp3",
            video_fid=video_fid,
            username=message.get("username") or "",
        )

        db_videos.conversions.update_one(
            {"video_fid": video_fid},
            {"$set": {"mp3_fid": str(mp3_fid), "status": "ready"}},
        )

        message["mp3_fid"] = str(mp3_fid)
        mp3_queue = os.environ.get("MP3_QUEUE", "mp3")
        channel.queue_declare(queue=mp3_queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=mp3_queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
    except Exception:
        traceback.print_exc()
        _mark_failed(db_videos, video_fid)
        return "conversion failed"
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        if mp3_path and os.path.exists(mp3_path):
            os.remove(mp3_path)
