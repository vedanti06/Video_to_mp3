import pika, sys, os, time
from pymongo import MongoClient
import gridfs
from convert import to_mp3


def main():
    mongo_host = os.environ.get("MONGO_HOST", "host.minikube.internal")
    mongo_port = int(os.environ.get("MONGO_PORT", "27017"))
    client = MongoClient(mongo_host, mongo_port)
    db_videos = client.videos
    db_mp3s = client.mp3s
    # gridfs
    fs_videos = gridfs.GridFS(db_videos)
    fs_mp3s = gridfs.GridFS(db_mp3s)

    host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    user = os.environ.get("RABBITMQ_USER")
    password = os.environ.get("RABBITMQ_PASS")
    if user and password:
        creds = pika.PlainCredentials(user, password)
        params = pika.ConnectionParameters(host=host, credentials=creds)
    else:
        params = pika.ConnectionParameters(host=host)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    queue_name = os.environ.get("VIDEO_QUEUE", "video")
    channel.queue_declare(queue=queue_name, durable=True)

    def callback(ch, method, properties, body):
        err = to_mp3.start(body, db_videos, fs_videos, fs_mp3s, ch)
        if err:
            ch.basic_nack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)


    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print("Waiting for messages")

    channel.start_consuming()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)