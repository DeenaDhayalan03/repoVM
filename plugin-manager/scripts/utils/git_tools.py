import logging
import shutil
from pathlib import Path

import git
import requests
from requests.auth import HTTPBasicAuth
import re


def pull_code_from_git(
    git_url: str, git_branch: str, git_username: str, git_access_token: str, pull_path: Path
) -> None:
    try:
        access_token_url = git_url.replace("https://", f"https://{git_username}:{git_access_token}@")
        if pull_path.exists():
            logging.warning(f"****DELETING EXISTING REPO {pull_path}")
            shutil.rmtree(pull_path)
        git.Repo.clone_from(access_token_url, pull_path, branch=git_branch)
    except Exception as e:
        logging.exception(e)
        raise RuntimeError("Error occurred while pulling the code from git") from e


def is_valid_url(url):
    """
    Validates the given URL format using regex and checks if it's reachable.

    :param url: The URL to validate.
    :return: True if the URL is valid and reachable, False otherwise.
    """

    pattern = r"https?://[a-zA-Z0-9.-]+(/[a-zA-Z0-9./_-]*)*"
    if not re.match(pattern, url):
        return False

    try:

        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def extract_domain_from_url(url):
    """
    Extracts the domain name from the URL using regex.
    """
    pattern = r"https?://([a-zA-Z0-9.-]+)"
    return match.group(1) if (match := re.match(pattern, url)) else None


def detect_platform_from_url(url):
    """
    Detects the platform (GitHub, GitLab, or Azure) based on the URL.
    """
    if "github" in url.lower():
        return "github"
    elif "gitlab" in url.lower():
        return "gitlab"
    elif "azure" in url.lower():
        return "azure"
    else:
        return None


def verify_git_credentials(username, access_token, url):
    """
    Verifies the credentials (username and access token) for GitHub, GitLab, or Azure DevOps.
    Returns True if valid credentials and username match, False otherwise.

    :param username: The username to verify.
    :param access_token: The access token to verify.
    :param url: The URL to extract domain and platform from.
    :return: True if the credentials are valid and username matches, False otherwise.
    """

    if not is_valid_url(url):
        return False

    platform = detect_platform_from_url(url)
    if not platform:
        return False

    domain = extract_domain_from_url(url)
    if not domain:
        return False

    response = get_platform_response(platform, domain, username, access_token)
    if not response:
        return False

    return validate_response(response, platform, username)


def get_platform_response(platform, domain, username, access_token):
    if platform == "github":
        api_url = "https://api.github.com/user"
        headers = {"Authorization": f"token {access_token}"}
        return requests.get(api_url, headers=headers)

    elif platform == "gitlab":
        api_url = f"https://{domain}/api/v4/user"
        headers = {"PRIVATE-TOKEN": access_token}
        return requests.get(api_url, headers=headers)

    elif platform == "azure":
        organization = username
        api_url = f"https://{domain}/{organization}/_apis/connectionData?api-version=7.1-preview.1"
        auth = HTTPBasicAuth("", access_token)
        return requests.get(api_url, auth=auth)

    return None


def validate_response(response, platform, username):
    if response.status_code != 200:
        return False

    user_data = response.json()
    platform_usernames = {
        "gitlab": user_data.get("username"),
        "github": user_data.get("login"),
        "azure": user_data.get("authenticatedUser", {}).get("userName"),
    }

    return platform_usernames.get(platform) == username
