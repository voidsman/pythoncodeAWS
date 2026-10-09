import os
import uuid

import boto3
import pymysql
from botocore.config import Config
from flask import Flask, render_template, request
from markupsafe import escape
from werkzeug.utils import secure_filename

app = Flask(__name__)

# All configuration comes from environment variables (injected by Jenkins).
REGION = os.environ.get("AWS_REGION", "eu-north-1")
BUCKET = os.environ.get("S3_BUCKET_NAME")

# Credentials are discovered automatically from the EC2 instance's IAM role.
# No access keys exist anywhere in this code.
s3 = boto3.client("s3", region_name=REGION, config=Config(signature_version="s3v4"))


def get_db_connection():
    # A fresh connection per request avoids stale-connection errors.
    return pymysql.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME", "studentdb"),
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    course = request.form["course"]
    photo = request.files.get("photo")

    if not photo or photo.filename == "":
        return "A photo is required.", 400

    # Unique, sanitized object key so uploads never overwrite each other.
    key = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"

    s3.upload_fileobj(
        photo,
        BUCKET,
        key,
        ExtraArgs={"ContentType": photo.content_type or "application/octet-stream"},
    )

    # Store a permanent reference, NOT a signed URL. Signed URLs made from
    # temporary role credentials are far longer than VARCHAR(500) and expire.
    photo_ref = f"s3://{BUCKET}/{key}"

    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO students (name, email, course, photo_url) "
                "VALUES (%s, %s, %s, %s)",
                (name, email, course, photo_ref),
            )
        db.commit()
    finally:
        db.close()

    # The bucket stays private. Generate a time-limited link on demand.
    signed_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=3600,
    )

    return (
        "<h2>Student Registered Successfully</h2>"
        f'<p><a href="{escape(signed_url)}">View uploaded photo</a> '
        "(link expires in 1 hour)</p>"
        '<p><a href="/">Register another student</a></p>'
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
