import pytest
from unittest.mock import patch
from scripts.utils.sonarqube_scan import SonarQubeScan

test_code_smell = "test:code_smell_file"
test_message = "Test message"
test_bug_file = "test:bug_file"
test_vulnerability_file = "test:vulnerability_file"


@pytest.fixture
def sonarqube_scan():
    return SonarQubeScan(project="test_project")


@pytest.mark.asyncio
async def test_get_values_handles_exception(sonarqube_scan):
    with patch("scripts.utils.common_util.hit_external_service", side_effect=Exception("Test exception")):
        result = sonarqube_scan.get_values()
        assert result


@pytest.mark.asyncio
async def test_sonarqube_code_smells_report_returns_correct_data(sonarqube_scan):
    code_smells = {
        "issues": [
            {
                "component": test_code_smell,
                "severity": "MAJOR",
                "line": 10,
                "message": test_message,
                "rule": "test_rule",
            }
        ]
    }
    result = sonarqube_scan.sonarqube_code_smells_report(code_smells)
    assert result[0]["file"] == "code_smell_file"
    assert result[0]["severity"] == "MAJOR"


@pytest.mark.asyncio
async def test_sonarqube_vulnerabilities_report_returns_correct_data(sonarqube_scan):
    vulnerabilities = {
        "issues": [
            {
                "component": test_vulnerability_file,
                "severity": "CRITICAL",
                "line": 20,
                "message": test_message,
                "rule": "test_rule",
            }
        ]
    }
    result = sonarqube_scan.sonarqube_vulnerabilities_report(vulnerabilities)
    assert result[0]["file"] == test_vulnerability_file
    assert result[0]["severity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_sonarqube_bug_report_returns_correct_data(sonarqube_scan):
    bugs = {
        "issues": [
            {
                "component": test_bug_file,
                "severity": "BLOCKER",
                "line": 30,
                "message": test_message,
                "rule": "test_rule",
            }
        ]
    }
    result = sonarqube_scan.sonarqube_bug_report(bugs)
    assert result[0]["file"] == "bug_file"
    assert result[0]["severity"] == "BLOCKER"
