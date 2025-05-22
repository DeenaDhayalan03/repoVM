import logging
import traceback

from scripts.config import SonarQubeConfig
from scripts.constants.sonar_constants import sonarqube_constants
from scripts.utils.common_util import hit_external_service
from scripts.utils.docker_util import DockerUtil

logger = logging.getLogger()


class SonarQubeScan:
    def __init__(self, project: str):
        self.sonarqube_user = SonarQubeConfig.sonarqube_user
        self.sonarqube_password = SonarQubeConfig.sonarqube_password
        self.sonarqube_token = SonarQubeConfig.sonarqube_token
        self.project = project
        self.sonarqube_url = (
            f"https://{self.sonarqube_user}:{self.sonarqube_password}@{SonarQubeConfig.sonarqube_url}/api/issues/search"
        )

    def initialize_project(self, src_folder: str):
        docker_util = DockerUtil()
        docker_util.docker_client.containers.run(
            image="sonarsource/sonar-scanner-cli:5",
            command=f"sonar-scanner -X -Dsonar.projectKey={self.project} -Dsonar.sources=. -Dsonar.host.url=https://{SonarQubeConfig.sonarqube_url} -Dsonar.token={self.sonarqube_token} -Dsonar.language=py,js,ts -Dsonar.plugins.downloadOnlyRequired=true -Dsonar.inclusions='**/*.py,**/*.js,**/*.ts'",
            volumes={src_folder: {"bind": "/usr/src", "mode": "rw"}},
            network_mode="host",
            group_add=[2000],
            user=1000,
            remove=True,
        )

    def get_values(self):
        try:
            logging.info(f"SonarQube URL {self.sonarqube_url}")
            code_smell_json = hit_external_service(
                api_url=self.sonarqube_url,
                method="get",
                params={
                    "componentKeys": self.project,
                    "types": "CODE_SMELL",
                    "statuses": sonarqube_constants["statuses"],
                    "severities": SonarQubeConfig.code_smell_severity,
                },
            )
            logging.info(f"Code Smell Json {code_smell_json}")
            vulnerability_json = hit_external_service(
                api_url=self.sonarqube_url,
                method="get",
                params={
                    "componentKeys": self.project,
                    "types": "VULNERABILITY",
                    "statuses": sonarqube_constants["statuses"],
                    "severities": SonarQubeConfig.vulnerability_severity,
                },
            )
            logging.info(f"Vulnerability  Json {vulnerability_json}")
            bug_json = hit_external_service(
                api_url=self.sonarqube_url,
                method="get",
                params={
                    "componentKeys": self.project,
                    "types": "BUG",
                    "statuses": sonarqube_constants["statuses"],
                    "severities": SonarQubeConfig.bug_severity,
                },
            )
            logging.info(f"Bug  Json {bug_json}")
            return {
                "code_smells": code_smell_json,
                "vulnerabilities": vulnerability_json,
                "bug": bug_json,
            }

        except Exception as e:
            print(traceback.format_exc())
            logger.error(f"Error in getting values ---> {str(e)}")

    def sonarqube_code_smells_report(self, code_smells: dict):
        data = []
        for code_smell in code_smells.get("issues"):
            data.append(
                {
                    "type": "CODE_SMELL",
                    "file": code_smell.get("component").split(":")[1],
                    "severity": code_smell.get("severity"),
                    "line": code_smell.get("line"),
                    "message": code_smell.get("message"),
                    "rule": code_smell.get("rule"),
                }
            )
        return data

    def sonarqube_vulnerabilities_report(self, vulnerabilities: dict):
        data = []
        for vulnerability in vulnerabilities.get("issues"):
            data.append(
                {
                    "type": "VULNERABILITY",
                    "file": vulnerability.get("component", None),
                    "severity": vulnerability.get("severity", None),
                    "line": vulnerability.get("line", None),
                    "message": vulnerability.get("message", None),
                    "rule": vulnerability.get("rule", None),
                }
            )
        return data

    def sonarqube_bug_report(self, bugs: dict):
        data = []
        for bug in bugs.get("issues"):
            data.append(
                {
                    "type": "BUG",
                    "file": bug.get("component").split(":")[1],
                    "severity": bug.get("severity"),
                    "line": bug.get("line"),
                    "message": bug.get("message"),
                    "rule": bug.get("rule"),
                }
            )
        return data
