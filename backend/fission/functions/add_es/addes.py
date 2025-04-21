import logging, json
from typing import Dict, Any, List
from flask import request, current_app
from elasticsearch8 import Elasticsearch

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

    current_app.logger.info(f"[addes] Got {len(records)} record(s) from queue")

    for record in records:
        doc_id = record["data"]["id"]
        index_name = record["platform"].lower()

        resp = es.index(
            index=index_name,
            id=doc_id,
            body=record
        )
        current_app.logger.info(
            f"[addes] Indexed {doc_id}, platform={index_name}, platform={resp}"
        )

    return "OK"
