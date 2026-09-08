"""S3 objects and prefixes, with conditional object writes."""
import posixpath
from contextlib import contextmanager
from urllib.parse import urlsplit


class Provider:
    id = "s3"
    plugin_name = "file_browser_s3"
    title = "S3 object storage"
    permissions = ("browse", "download", "upload", "edit", "delete")
    fields = [
        {"name": "bucket", "label": "Bucket", "default": ""},
        {"name": "prefix", "label": "Key prefix (optional)", "default": ""},
        {"name": "region", "label": "Region", "default": "us-east-1"},
        {"name": "endpoint", "label": "HTTPS endpoint (optional for AWS)", "default": ""},
        {"name": "access_key", "label": "Access key ID", "secret": True},
        {"name": "secret_key", "label": "Secret access key", "secret": True},
        {"name": "session_token", "label": "Session token (optional)", "secret": True},
    ]

    def validate(self, config):
        result = {field["name"]: str(config.get(field["name"], field.get("default", ""))) for field in self.fields}
        if not all(result[key].strip() for key in ("bucket", "region", "access_key", "secret_key")):
            raise ValueError("Bucket, region and explicit access credentials are required.")
        if any(char in result["bucket"] for char in '/\\\x00:'):
            raise ValueError("Enter a bucket name, not an ARN or URL.")
        if result["endpoint"]:
            url = urlsplit(result["endpoint"])
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("The S3 endpoint must use HTTPS without embedded credentials.")
        result["prefix"] = result["prefix"].strip("/")
        if any(p in (".", "..") for p in result["prefix"].split("/")) or "\\" in result["prefix"] or "\0" in result["prefix"]:
            raise ValueError("Invalid key prefix.")
        return result

    @contextmanager
    def open(self, config, directory):
        import boto3
        from botocore.config import Config
        client = boto3.client("s3", region_name=config["region"], endpoint_url=config["endpoint"] or None,
                              aws_access_key_id=config["access_key"], aws_secret_access_key=config["secret_key"],
                              aws_session_token=config["session_token"] or None,
                              config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2}))
        try:
            yield S3(client, config["bucket"], config["prefix"])
        finally:
            client.close()


class S3:
    def __init__(self, client, bucket, prefix):
        self.client, self.bucket = client, bucket
        self.prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""

    def key(self, relative):
        return self.prefix + relative

    def list(self, relative):
        prefix = self.key(relative.rstrip("/") + "/" if relative else "")
        entries = {}
        pages = self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix, Delimiter="/")
        for page in pages:
            for item in page.get("Contents", []):
                name = item["Key"][len(prefix):]
                if name:
                    entries[name] = dict(name=name, is_dir=False, size=item["Size"], modified=item["LastModified"].timestamp() * 1000)
            for item in page.get("CommonPrefixes", []):
                name = item["Prefix"][len(prefix):].rstrip("/")
                entries[name] = dict(name=name, is_dir=True, size=0, modified=0)
            if len(entries) > 10000:
                raise ValueError("Prefix contains more than 10000 entries; choose a narrower prefix.")
        return list(entries.values())

    def stat(self, relative):
        if not relative:
            return dict(is_dir=True, size=0, modified=0)
        for entry in self.list(posixpath.dirname(relative)):
            if entry["name"] == posixpath.basename(relative):
                return entry
        raise FileNotFoundError(relative)

    def read(self, relative, limit):
        result = self.client.get_object(Bucket=self.bucket, Key=self.key(relative))
        with result["Body"] as stream:
            if result["ContentLength"] > limit:
                raise ValueError("File exceeds the size limit.")
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("File exceeds the size limit.")
        return data, {"etag": result["ETag"]}

    def write(self, relative, content, expected=None):
        condition = {"IfNoneMatch": "*"} if expected is None else {"IfMatch": expected["etag"]}
        result = self.client.put_object(Bucket=self.bucket, Key=self.key(relative), Body=content, **condition)
        return {"etag": result["ETag"]}

    def mkdir(self, relative):
        self.write(relative.rstrip("/") + "/", b"")

    def rename(self, source, destination):
        raise ValueError("S3 has no atomic rename. Download and upload objects to a new key instead.")

    def remove(self, relative, directory=False):
        key = relative.rstrip("/") + "/" if directory else relative
        self.client.delete_object(Bucket=self.bucket, Key=self.key(key))
