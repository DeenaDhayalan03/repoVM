create_new = "Create New"
ui_date_format = "%I:%M %p %d %b %Y"
plugin_list_table_header = {
    "headerContent": [
        {
            "headerName": "Plugin Name",
            "field": "name",
            "key": "name",
            "checkboxSelection": True,
            "headerCheckboxSelection": True,
        },
        {"headerName": "Version", "field": "version", "key": "version"},
        {
            "headerName": "Plugin Type",
            "field": "plugin_type",
            "key": "plugin_type",
            "floatingFilter": True,
            "filter": "selectionFilter",
            "filterParams": {
                "values": [
                    {"label": "Widget", "value": "widget"},
                    {"label": "Custom App", "value": "custom_app"},
                    {"label": "Formio Component", "value": "formio_component"},
                    {"label": "Kubeflow", "value": "kubeflow"},
                    {"label": "Micro Service", "value": "microservice"},
                ],
                "suppressAndOrCondition": True,
            },
        },
        {"headerName": "Deployment Status", "field": "plugin_status", "key": "plugin_status", "floatingFilter": False},
        {"headerName": "Deployed By", "field": "deployed_by", "key": "deployed_by"},
        {"headerName": "Deployed On", "field": "deployed_on", "key": "deployed_on", "floatingFilter": False},
    ]
}

plugin_list_table_actions = {
    "actions": [
        {"action": "edit", "type": "edit", "class": "ra-sm-edit", "tooltip": "Edit"},
        {"action": "start", "type": "start", "class": "ra-md-play", "tooltip": "Start", "disabled": True},
        {"action": "pause", "type": "pause", "class": "ra-sm-pause", "tooltip": "Stop", "disabled": True},
        {"action": "logs", "type": "logs", "class": "ra-md-logs", "tooltip": "Plugin Logs"},
    ],
    "externalActions": [{"action": "auto_refresh", "label": "Refresh", "type": "auto_refresh"}],
    "topLeftActions": [
        {"type": "start", "icon_class": "ra-md-play", "tooltip": "Start", "label": "Start"},
        {"type": "pause", "icon_class": "ra-sm-pause", "tooltip": "Stop", "label": "Stop", "section": True},
        {
            "type": "register",
            "icon_class": "ra-sm-build-and-deploy",
            "tooltip": "Deploy",
            "label": "Deploy",
            "section": True,
        },
        {"type": "delete", "icon_class": "ra-md-delete", "tooltip": "Delete", "label": "Delete"},
    ],
}

create_new_button = {
    "action": "addnew",
    "label": create_new,
    "type": "button",
    "icon_class": "ra-sm-plus",
    "btn_class": "btn-primary",
}

security_checks = [
    {
        "label": "Antivirus Scan",
        "key": "antivirus",
        "value": None,
    },
    {
        "label": "SonarQube Scan",
        "key": "sonarqube",
        "value": None,
    },
    {
        "label": "Vulnerability Scan",
        "key": "vulnerabilities",
        "value": None,
    },
]

plugin_advance_config_header = [
    {"label": "Property", "key": "propertyLabel"},
    {"label": "Description", "key": "description"},
    {"label": "Input", "key": "input"},
]

plugin_code_scans_header_content = {
    "antivirus": {
        "headerContent": [
            {"label": "Infected Files", "value": "infected_files"},
        ]
    },
    "sonarqube": {
        "headerContent": [
            {"label": "Type", "value": "type"},
            {"label": "File", "value": "file"},
            {"label": "Severity", "value": "severity"},
            {"label": "Line", "value": "line"},
            {"label": "Message", "value": "message"},
            {"label": "Rule", "value": "rule"},
        ]
    },
    "vulnerabilities": {
        "headerContent": [
            {"label": "Package", "value": "Pacakge"},
            {"label": "Description", "value": "Description"},
        ]
    },
}

plugin_registration_types = {
    "git": "Git/VCS",
    "docker": "Docker Image",
    "bundle": "Bundle Upload",
}

plugin_list_table_header_for_portal = {
    "headerContent": [
        {
            "headerName": "Plugin Name",
            "field": "name",
            "key": "name",
            "checkboxSelection": True,
            "headerCheckboxSelection": True,
        },
        {"headerName": "Version", "field": "version", "key": "version"},
        {
            "headerName": "Plugin Type",
            "field": "plugin_type",
            "key": "plugin_type",
            "floatingFilter": True,
            "filter": "selectionFilter",
            "filterParams": {
                "values": [
                    {"label": "Widget", "value": "widget"},
                    {"label": "Custom App", "value": "customApp"},
                    {"label": "Formio Component", "value": "formioComponent"},
                    {"label": "Kubeflow", "value": "kubeflow"},
                    {"label": "Micro Service", "value": "microService"},
                ],
                "suppressAndOrCondition": True,
            },
        },
        {"headerName": "Status", "field": "plugin_status", "key": "plugin_status", "floatingFilter": False},
        {"headerName": "Last Modified By", "field": "deployed_by", "key": "deployed_by"},
        {"headerName": "Last Modified On", "field": "deployed_on", "key": "deployed_on", "floatingFilter": False},
    ]
}

plugin_list_table_actions_for_portal = {
    "actions": [
        {"action": "edit", "type": "edit", "class": "ra-sm-edit", "tooltip": "Edit"},
        {"type": "register", "class": "ra-md-reset-controllers", "tooltip": "Scan", "section": True},
    ],
    "externalActions": [
        {"action": "auto_refresh", "label": "Refresh", "type": "auto_refresh"},
        {
            "action": "addnew",
            "label": create_new,
            "type": "button",
            "icon_class": "ra-sm-plus",
            "btn_class": "btn-outline-primary",
        },
    ],
    "topLeftActions": [
        {
            "type": "artifact_download",
            "icon_class": "ra-md-download",
            "label": "Download",
            "tooltip": "Download",
            "section": True,
        },
        {
            "type": "register",
            "icon_class": "ra-md-reset-controllers",
            "tooltip": "Scan",
            "label": "Scan",
            "section": True,
        },
        {
            "type": "delete",
            "icon_class": "ra-md-delete",
            "tooltip": "Delete",
            "label": "Delete",
        },
    ],
}

git_target_list_table_header = {
    "headerContent": [
        {
            "headerName": "Git Target Name",
            "field": "name",
            "key": "name",
            "checkboxSelection": True,
            "headerCheckboxSelection": True,
        },
        {"headerName": "Created On", "field": "created_on", "key": "created_on"},
        {"headerName": "Created By", "field": "created_by", "key": "created_by"},
    ]
}

git_target_list_table_actions = {
    "actions": [
        {"class": "fa-pencil", "action": "edit", "tooltip": "Edit"},
        {"class": "fa-trash", "action": "delete", "tooltip": "Delete"},
    ],
    "externalActions": [
        {"type": "button", "action": "addnew", "label": "Create New", "icon_class": "fa fa-plus-circle"}
    ],
}

git_target_list_table_column_defs = [
    {
        "headerName": "Target Name",
        "field": "targetName",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "filterParams": {"suppressAndOrCondition": True},
    },
    {
        "headerName": "Created On",
        "field": "createdOn",
        "filter": "agTextColumnFilter",
        "floatingFilter": False,
        "filterParams": False,
    },
    {
        "headerName": "Created By",
        "field": "createdBy",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "filterParams": {"suppressAndOrCondition": True},
    },
]
