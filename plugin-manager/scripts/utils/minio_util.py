import logging

from minio import Minio
from minio.error import MinioException


class MinioUtility:
    def __init__(self, endpoint, access_key, secret_key, secure=True):
        self.minio_client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def create_bucket(self, bucket_name):
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
                logging.debug(f"Bucket '{bucket_name}' created successfully.")
            else:
                logging.debug(f"Bucket '{bucket_name}' already exists.")
        except Exception as e:
            logging.error(f"Error creating bucket '{bucket_name}': {e}")

    def list_buckets(self):
        try:
            buckets = self.minio_client.list_buckets()
            return [bucket.name for bucket in buckets]
        except MinioException as e:
            logging.error(f"Error listing buckets: {e}")
            raise

    def upload_object(self, bucket_name, object_name, file):
        try:
            self.minio_client.put_object(bucket_name, object_name, file, length=-1, part_size=10 * 1024 * 1024)
            logging.debug(f"Object '{object_name}' uploaded successfully to bucket '{bucket_name}'.")
        except MinioException:
            logging.error(f"Error uploading object '{object_name}' to bucket '{bucket_name}'.")
            raise

    def download_object(self, bucket_name, object_name, file_path):
        try:
            self.minio_client.fget_object(bucket_name, object_name, file_path)
            logging.debug(f"Object '{object_name}' downloaded successfully from bucket '{bucket_name}'.")
        except MinioException as e:
            logging.error(f"Error downloading object '{object_name}' from bucket '{bucket_name}': {e}")
            raise

    def list_objects(self, bucket_name):
        try:
            objects = self.minio_client.list_objects(bucket_name)
            return [obj.object_name for obj in objects]
        except MinioException as e:
            logging.error(f"Error listing objects in bucket '{bucket_name}': {e}")
            raise

    def delete_object(self, bucket_name, object_name):
        try:
            self.minio_client.remove_object(bucket_name, object_name)
            logging.debug(f"Object '{object_name}' deleted successfully from bucket '{bucket_name}'.")
        except MinioException as e:
            logging.error(f"Error deleting object '{object_name}' from bucket '{bucket_name}': {e}")
            raise

    def delete_bucket(self, bucket_name):
        try:
            self.minio_client.remove_bucket(bucket_name)
            logging.debug(f"Bucket '{bucket_name}' deleted successfully.")
        except MinioException as e:
            logging.error(f"Error deleting bucket '{bucket_name}': {e}")
            raise
