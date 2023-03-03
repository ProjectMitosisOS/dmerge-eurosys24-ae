#!/usr/bin/env/python
from minio import Minio
from minio.error import S3Error


def main():
    # Create a client with the MinIO server playground, its access key
    # and secret key.
    # {"url":"http://127.0.0.1:9000","accessKey":"wSgN80XAPlP5tLgD","secretKey":"z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W","api":"s3v4","path":"auto"}
    client = Minio(
        endpoint='127.0.0.1:9000',
        secure=False,
        access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
    bucketName = 'asiatrip'
    # Make 'asiatrip' bucket if not exist.
    found = client.bucket_exists(bucketName)
    if not found:
        client.make_bucket(bucketName)
    else:
        print("Bucket 'asiatrip' already exists")

    client.fput_object(
        bucket_name=bucketName, object_name="s3_test.py", file_path="s3_test.py",
    )
    client.fget_object(bucket_name=bucketName, object_name='s3_test.py', file_path='out.py')


if __name__ == "__main__":
    try:
        main()
    except S3Error as exc:
        print("error occurred.", exc)
