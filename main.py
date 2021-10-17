import os
import re
import uuid

import redis
from flask import Flask, jsonify, request, render_template, sessions, redirect

import constants as const

app = Flask(__name__)


def database_conn():
    try:
        redis_url = "redis://localhost:6379"
        redis_db_conn = redis.StrictRedis(
            host="localhost", port=6379, db=0, password=os.environ["REDIS_PASS"]
        )
        return redis_db_conn
    except Exception as e:
        print(e)
        exit(1)


def is_valid_url(url):

    regex = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    if regex.search(url):
        return True
    else:
        return False


def base62_encode(deci):

    s = const.CHARACHTERS_BASE62
    hash_str = ""
    while deci > 0 and len(hash_str) <= 7:
        ind = deci % 62
        hash_str = s[int(ind)] + hash_str
        deci //= 62
    return hash_str.strip()


def generate_hashid():
    id_ = uuid.uuid4()
    return (id_, base62_encode(id_.int & (1 << 64) - 1))


def db_validation(short_url, long_url, uid, b62_id):
    try:
        conn = database_conn()
        keys_list = [keys.decode() for keys in conn.scan_iter()]
        if b62_id in keys_list:
            resp_ = conn.hgetall(b62_id)
            return resp_["short_url"]
        else:
            print("entering the else block")
            val_dict = {
                "short_url": short_url,
                "long_url": long_url,
                "uid": str(uid),
            }
            print(val_dict)
            result = conn.hmset(b62_id, val_dict)
            if result:
                return short_url
            else:
                raise Exception("Unable to insert record to DB")
    except Exception as e:
        print(e)
        exit(1)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/shorten", methods=["GET", "POST"])
def shorten():
    long_url = request.form.get("longUrl")
    if is_valid_url(long_url):
        uid, b62_val = generate_hashid()
        shortened_url = f"http://{const.SHORTENER_DOMAIN}/{b62_val}"
        db_validation(shortened_url, long_url, uid, b62_val)
        # return shortened_url
        return render_template("response.html", short_url=shortened_url)
    else:
        return "<h2> Invalid URL </h2>"


@app.route("/<b62id>")
def redirect_url(b62id):
    conn = database_conn()
    keys_list = [keys.decode() for keys in conn.scan_iter()]
    if b62id in keys_list:
        resp_ = conn.hgetall(b62id)
        result = resp_[b"long_url"].decode()
    return redirect(result.strip())


def testing_redis(b62_id):
    conn = database_conn()
    keys_list = [keys.decode() for keys in conn.scan_iter()]
    if b62_id in keys_list:
        resp_ = conn.hgetall(b62_id)
        print(type(resp_))


if __name__ == "__main__":
    # run() method of Flask class runs the application)
    # on the local development server.
    app.run(debug=True)
    # testing_redis("ovAPfjGY")
