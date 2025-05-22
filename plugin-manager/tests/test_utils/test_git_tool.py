import pytest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from scripts.utils.git_tools import pull_code_from_git

git_clone = "git.Repo.clone_from"


@pytest.fixture
def git_params():
    with TemporaryDirectory() as temp_dir:
        yield {
            "git_url": "https://example.com/repo.git",
            "git_branch": "main",
            "git_username": "user",
            "git_access_token": "token",
            "pull_path": Path(temp_dir) / "repo",
        }


def test_pull_code_successfully(git_params):
    with patch(git_clone) as mock_clone:
        pull_code_from_git(**git_params)
        mock_clone.assert_called_once_with(
            f"https://{git_params['git_username']}:{git_params['git_access_token']}@example.com/repo.git",
            git_params["pull_path"],
            branch=git_params["git_branch"],
        )


def test_pull_code_existing_repo_deleted(git_params):
    with patch("shutil.rmtree") as mock_rmtree, patch(git_clone) as mock_clone:
        git_params["pull_path"].mkdir(parents=True, exist_ok=True)
        pull_code_from_git(**git_params)
        mock_rmtree.assert_called_once_with(git_params["pull_path"])
        mock_clone.assert_called_once_with(
            f"https://{git_params['git_username']}:{git_params['git_access_token']}@example.com/repo.git",
            git_params["pull_path"],
            branch=git_params["git_branch"],
        )


def test_pull_code_raises_runtime_error(git_params):
    with patch(git_clone, side_effect=Exception("Clone failed")):
        with pytest.raises(RuntimeError, match="Error occurred while pulling the code from git"):
            pull_code_from_git(**git_params)
