from typing import Dict, Any, List

from elasticsearch8 import Elasticsearch
from elasticsearch8.exceptions import ConflictError
from flask import request, current_app

ES_URL = "https://elasticsearch-master.elastic.svc.cluster.local:9200"
ES_AUTH = ("elastic", "elastic")


def main() -> str:
    """
    get data from redis list, and send to elasticsearch
    """
    es = Elasticsearch(
        ES_URL,
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=ES_AUTH
    )

    payload = request.get_json(force=True)
    records: List[Dict[str, Any]] = payload if isinstance(payload, list) else [payload]

    current_app.logger.info(f"Got {len(records)} record from queue")

    for record in records:
        post_id = record["data"]["id"]
        platform = record["platform"].lower()

        try:
            es.index(
                index="mastodon",
                id=f"{platform}_{post_id}",
                body=record,
                op_type='create'
            )
            current_app.logger.info(f"A record sent to ES successfully")
        except ConflictError:
            current_app.logger.info(f"Skipped existing post: {platform}_{post_id}")

    return "OK"
