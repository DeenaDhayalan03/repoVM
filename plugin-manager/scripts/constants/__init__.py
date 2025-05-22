from .api import APIEndPoints, GitApiEndPoints


class STATUS:
    SUCCESS = "success"
    FAILED = "failed"
    SUCCESS_CODES = [200, 201]


redeployment_supported_types = ("widget", "microservice", "custom_app", "formio_component", "kubeflow", "protocols")
job_types = ("widget", "microservice", "custom_app", "formio_component", "kubeflow")
delete_container_support = ("widget", "microservice", "custom_app", "formio_component")
plugin_redeployment_required = (
    "advancedConfiguration",
    "git_access_token",
    "git_username",
)

git_access_token_mask = "*********************"
kubeflow_url_not_found = "Kubeflow URL not found"
antivirus_scan_failed = "Antivirus scan failed"


class Message:
    bundle_message = "Bundle uploaded successfully"
    plugin_not_found = "Plugin not found"
