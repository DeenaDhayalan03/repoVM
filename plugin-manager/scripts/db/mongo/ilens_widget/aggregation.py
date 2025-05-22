class AggregationsWidget:
    @staticmethod
    def get_widget_plugins_agg_query(project_id, plugin_id):
        return [
            {
                "$match": {"project_id": project_id, "plugin_id": plugin_id},
            },
            {
                "$sort": {
                    "installed_on": -1,
                },
            },
            {
                "$group": {
                    "_id": "$chart_type",
                    "first_doc": {
                        "$first": "$$ROOT",
                    },
                },
            },
            {
                "$replaceRoot": {
                    "newRoot": "$first_doc",
                },
            },
        ]
