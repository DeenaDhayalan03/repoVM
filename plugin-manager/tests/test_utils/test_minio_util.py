import pytest
from unittest.mock import patch, MagicMock

from minio.error import MinioException

from scripts.utils.minio_util import MinioUtility

logging_error = "logging.error"


@pytest.fixture
def minio_utility():
    return MinioUtility(endpoint="localhost:9000", access_key="access_key", secret_key="secret_key")


def test_create_bucket_successfully(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "bucket_exists", return_value=False),
        patch.object(minio_utility.minio_client, "make_bucket") as mock_make_bucket,
    ):
        minio_utility.create_bucket("test-bucket")
        mock_make_bucket.assert_called_once_with("test-bucket")


def test_create_bucket_already_exists(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "bucket_exists", return_value=True),
        patch("logging.debug") as mock_logging,
    ):
        minio_utility.create_bucket("test-bucket")
        mock_logging.assert_called_with("Bucket 'test-bucket' already exists.")


def test_create_bucket_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "bucket_exists", side_effect=Exception("Error")),
        patch(logging_error) as mock_logging,
    ):
        minio_utility.create_bucket("test-bucket")
        mock_logging.assert_called_with("Error creating bucket 'test-bucket': Error")


def test_list_buckets_successfully(minio_utility):
    with patch.object(
        minio_utility.minio_client,
        "list_buckets",
        return_value=[
            MagicMock(name="bucket1", object_name="bucket1"),
            MagicMock(name="bucket2", object_name="bucket2"),
        ],
    ):
        buckets = minio_utility.list_buckets()
        assert buckets


def test_list_buckets_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "list_buckets", side_effect=MinioException("Error")),
        patch(logging_error) as mock_logging,
    ):
        with pytest.raises(MinioException):
            minio_utility.list_buckets()
        mock_logging.assert_called_with("Error listing buckets: Error")


def test_upload_object_successfully(minio_utility):
    with patch.object(minio_utility.minio_client, "put_object") as mock_put_object:
        minio_utility.upload_object("test-bucket", "test-object", MagicMock())
        mock_put_object.assert_called_once()


def test_upload_object_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "put_object", side_effect=MinioException("Error")),
        patch(logging_error) as mock_logging,
    ):
        with pytest.raises(MinioException):
            minio_utility.upload_object("test-bucket", "test-object", MagicMock())
        mock_logging.assert_called_with("Error uploading object 'test-object' to bucket 'test-bucket'.")


def test_download_object_successfully(minio_utility):
    with patch.object(minio_utility.minio_client, "fget_object") as mock_fget_object:
        minio_utility.download_object("test-bucket", "test-object", "/path/to/file")
        mock_fget_object.assert_called_once()


def test_download_object_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "fget_object", side_effect=MinioException("Error")),
        patch(logging_error) as mock_logging,
    ):
        with pytest.raises(MinioException):
            minio_utility.download_object("test-bucket", "test-object", "/path/to/file")
        mock_logging.assert_called_with("Error downloading object 'test-object' from bucket 'test-bucket': Error")


def test_list_objects_successfully(minio_utility):
    with patch.object(
        minio_utility.minio_client,
        "list_objects",
        return_value=[MagicMock(object_name="object1"), MagicMock(object_name="object2")],
    ):
        objects = minio_utility.list_objects("test-bucket")
        assert objects == ["object1", "object2"]


def test_list_objects_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "list_objects", side_effect=MinioException("Error")),
        patch(logging_error) as mock_logging,
    ):
        with pytest.raises(MinioException):
            minio_utility.list_objects("test-bucket")
        mock_logging.assert_called_with("Error listing objects in bucket 'test-bucket': Error")


def test_delete_object_successfully(minio_utility):
    with patch.object(minio_utility.minio_client, "remove_object") as mock_remove_object:
        minio_utility.delete_object("test-bucket", "test-object")
        mock_remove_object.assert_called_once()


def test_delete_object_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "remove_object", side_effect=MinioException("Error")),
        patch(logging_error) as mock_logging,
    ):
        with pytest.raises(MinioException):
            minio_utility.delete_object("test-bucket", "test-object")
        mock_logging.assert_called_with("Error deleting object 'test-object' from bucket 'test-bucket': Error")


def test_delete_bucket_successfully(minio_utility):
    with patch.object(minio_utility.minio_client, "remove_bucket") as mock_remove_bucket:
        minio_utility.delete_bucket("test-bucket")
        mock_remove_bucket.assert_called_once()


def test_delete_bucket_raises_exception(minio_utility):
    with (
        patch.object(minio_utility.minio_client, "remove_bucket", side_effect=MinioException("Error")),
        patch(logging_error) as mock_logging,
    ):
        with pytest.raises(MinioException):
            minio_utility.delete_bucket("test-bucket")
        mock_logging.assert_called_with("Error deleting bucket 'test-bucket': Error")
