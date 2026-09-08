"""SDK-level requests verified without cloud credentials or charges."""
import unittest
import boto3
from botocore.stub import Stubber
from backend import Provider, S3


class TransportTest(unittest.TestCase):
    def test_conditional_writes_and_prefix(self):
        client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
        fs = S3(client,"test-bucket","allowed")
        with Stubber(client) as stub:
            stub.add_response("put_object", {"ETag":'"v1"'}, {"Bucket":"test-bucket","Key":"allowed/code.py","Body":b"one","IfNoneMatch":"*"})
            self.assertEqual(fs.write("code.py",b"one"),{"etag":'"v1"'})
            stub.add_response("put_object", {"ETag":'"v2"'}, {"Bucket":"test-bucket","Key":"allowed/code.py","Body":b"two","IfMatch":'"v1"'})
            fs.write("code.py",b"two",expected={"etag":'"v1"'})
            stub.add_client_error("put_object","PreconditionFailed",http_status_code=412,expected_params={"Bucket":"test-bucket","Key":"allowed/code.py","Body":b"stale","IfMatch":'"v1"'})
            from botocore.exceptions import ClientError
            with self.assertRaises(ClientError): fs.write("code.py",b"stale",expected={"etag":'"v1"'})
            stub.add_response("list_objects_v2", {"CommonPrefixes":[{"Prefix":"allowed/folder/"}]}, {"Bucket":"test-bucket","Prefix":"allowed/","Delimiter":"/"})
            self.assertEqual(fs.list("")[0]["name"],"folder")
            stub.assert_no_pending_responses()
        with self.assertRaises(ValueError): fs.rename("a","b")
        with self.assertRaises(ValueError): Provider().validate(dict(bucket="x",region="x",access_key="x",secret_key="x",endpoint="http://insecure"))
        client.close()


if __name__ == "__main__": unittest.main()
