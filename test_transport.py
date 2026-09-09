"""SDK-level requests verified without cloud credentials or charges."""
import io
import tempfile
import unittest
import boto3
from botocore.stub import Stubber, ANY
from botocore.response import StreamingBody
from backend import Provider, S3


class TransportTest(unittest.TestCase):
    def test_conditional_writes_and_prefix(self):
        client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
        fs = S3(client,"test-bucket","allowed")
        def check_body(params, **kwargs):
            self.assertTrue(hasattr(params["Body"], "read"))
        client.meta.events.register("before-parameter-build.s3.PutObject", check_body)
        with Stubber(client) as stub:
            stub.add_response("put_object", {"ETag":'"v1"'}, {"Bucket":"test-bucket","Key":"allowed/code.py","Body":ANY,"IfNoneMatch":"*"})
            self.assertEqual(fs.write("code.py",io.BytesIO(b"one")),{"etag":'"v1"'})
            stub.add_response("put_object", {"ETag":'"v2"'}, {"Bucket":"test-bucket","Key":"allowed/code.py","Body":ANY,"IfMatch":'"v1"'})
            fs.write("code.py",io.BytesIO(b"two"),expected={"etag":'"v1"'})
            stub.add_client_error("put_object","PreconditionFailed",http_status_code=412,expected_params={"Bucket":"test-bucket","Key":"allowed/code.py","Body":ANY,"IfMatch":'"v1"'})
            from botocore.exceptions import ClientError
            with self.assertRaises(ClientError): fs.write("code.py",io.BytesIO(b"stale"),expected={"etag":'"v1"'})
            stub.add_response("list_objects_v2", {"CommonPrefixes":[{"Prefix":"allowed/folder/"}]}, {"Bucket":"test-bucket","Prefix":"allowed/","Delimiter":"/"})
            self.assertEqual(fs.list("")[0]["name"],"folder")
            stub.add_response("put_object", {"ETag": '"empty"'}, {"Bucket": "test-bucket", "Key": "allowed/empty/", "Body": ANY, "IfNoneMatch": "*"})
            fs.mkdir("empty")
            large = b"x" * (2 * 1024 * 1024 + 17)
            with tempfile.TemporaryFile() as source:
                source.write(large)
                source.seek(0)
                stub.add_response("put_object", {"ETag": '"large"'},
                                  {"Bucket": "test-bucket", "Key": "allowed/large.txt", "Body": source, "IfNoneMatch": "*"})
                self.assertEqual(fs.write("large.txt", source), {"etag": '"large"'})
            class BoundedReader(io.BytesIO):
                def read(self, size=-1):
                    assert 0 < size <= 1024 * 1024
                    return super().read(size)
            for limit in (len(large), len(large) - 1):
                body = StreamingBody(BoundedReader(large), len(large))
                stub.add_response("get_object", {"Body": body, "ContentLength": len(large), "ETag": '"large"'},
                                  {"Bucket": "test-bucket", "Key": "allowed/large.txt"})
                output = io.BytesIO()
                if limit == len(large):
                    self.assertEqual(fs.read("large.txt", output, limit), {"etag": '"large"'})
                    self.assertEqual(output.getvalue(), large)
                else:
                    with self.assertRaises(ValueError):
                        fs.read("large.txt", output, limit)
                    self.assertLessEqual(output.tell(), limit)
                self.assertTrue(body._raw_stream.closed)
            stub.assert_no_pending_responses()
        with self.assertRaises(ValueError): fs.rename("a","b")
        with self.assertRaises(ValueError): Provider().validate(dict(bucket="x",region="x",access_key="x",secret_key="x",endpoint="http://insecure"))
        client.close()


if __name__ == "__main__": unittest.main()
