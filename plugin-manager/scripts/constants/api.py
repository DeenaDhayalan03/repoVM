class _APIEndPoints:
    api_base = "/api"

    # versions
    v1 = "/v1"

    # inner routes
    plugin_services_base = "/plugins"
    plugin_save = "/save"
    plugin_edit = "/edit"
    plugin_delete = "/delete"
    plugin_list = "/list"
    plugin_list_by_type = "/list-by-type"
    plugin_details = "/details"
    plugin_fetch = "/fetch"
    plugin_deploy = "/deploy"
    plugin_logs = "/plugin-logs"
    plugin_state = "/plugin-state"
    plugin_report = "/plugin-report"
    plugin_logs_download = "/download-plugin-logs"
    plugin_env_config = "/plugin-env-config"
    plugin_bundle_upload = "/bundle-upload"
    plugin_v2_bundle_upload = "/v2/bundle-upload"
    plugin_bundle_download = "/bundle-download"
    plugin_report_download = "/download-plugin-report"
    plugin_advance_config = "/plugin-advance-config"
    resource_config = "/resource-config"
    upload_files = "/upload"
    update_configuration = "/update-configuration"
    uploaded_files_base = "/uploaded-files"
    get_uploaded_files = f"{uploaded_files_base}/get"
    download_uploaded_files = f"{uploaded_files_base}/download"
    get_errors = "/errors/get"
    get_info = "/info"
    plugin_headercontent = "/plugin-headercontent"
    ui_services_base = "/ui-svc"
    get_dropdown_elements = "/get-dropdowns"
    get_dependant_dropdown_elements = "/get-dependant-dropdowns"
    update_dropdown_elements = "/update-dropdown"
    plugin_securuty_check = "/plugin-security-check"
    download_docker_image = "/initiate-download"
    download_file = "/download-docker-file"
    fetch_versions = "/fetch-versions"

    protocols_base = "/protocols"
    plugin_protocol_validate = "/protocol_validate"
    template_download = "/template/download"
    get_deployed_container_status = "/get-deployed-container-status"
    api_save_refresh_load_conf = "/refresh_load_conf"


class _GitAPIEndPoints:
    git_services_base = "/git-services"
    git_target_list = "/git-list"
    git_target_create = "/git-create"
    git_target_delete = "/git-delete"
    git_validation = "/git_validation"
    list_reposotories = "/list_reposotories"
    git_headercontent = "/git-headercontent"
    git_target_get = "/get-git-target"


class _ExternalAPI:
    deploy = "/deploy"
    delete_resources = "/delete-resource"
    status = "/status"
    deployment_status = "/deployment-status"
    plugin_logs = "/plugin-logs"
    plugin_switch = "/plugin-switch"
    api_load_configurations = "widget/load_configuration"
    secrets = "/secrets"


APIEndPoints = _APIEndPoints()
ExternalAPI = _ExternalAPI()
GitApiEndPoints = _GitAPIEndPoints
