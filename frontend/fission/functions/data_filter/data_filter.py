"""
Handles query requests from the front-end, constructs Elasticsearch queries,
performs scroll paging, and returns structured results.

Input:
payload (str): a JSON string passed in by the frontend, containing filtered fields such as content,
 tags, keywords, as well as size and max_docs configuration.

Returns:
- str: JSON string containing the total number of hits and a list of documents,
 only the required fields are kept for each document.
"""

import json
from elasticsearch8 import Elasticsearch
from flask import request, current_app
from datetime import datetime

ES_HOST = "https://elasticsearch-master.elastic.svc.cluster.local:9200"
ES_INDEX = "socialplatform"
CONFIG_MAP = "shared-data"
MAX_DOCS_DEFAULT = 500000


def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()


def query(payload: dict) -> dict:
    """
        check the payload context, and produce the correct format
        :param payload: str, payload context
        :return: correct format for elastic search
    """
    and_or = payload.get("combine") == "or"
    content_terms = payload.get("content", [])
    tag_terms = payload.get("tags", [])
    keyword_terms = payload.get("keywords", [])
    date_range = payload.get("date_range")

    # return none, if not context provided
    if not (content_terms or tag_terms or keyword_terms or date_range):
        return {"bool": {"must": [{"match_none": {}}]}}

    must, should, filter_content = [], [], []

    # produce data.content
    if content_terms:
        q = " OR ".join(f'"{w}"' if " " in w else w for w in content_terms)
        clause = {
            "simple_query_string": {
                "query": q,
                "fields": ["data.content"],
                "default_operator": "OR"
            }
        }
        (should if and_or else must).append(clause)

    # produce data.tags
    if tag_terms:
        clause = {"terms": {"data.tags": tag_terms}}
        (should if and_or else filter_content).append(clause)

    # produce keywords
    if keyword_terms:
        clause = {"terms": {"keywords": keyword_terms}}
        (should if and_or else filter_content).append(clause)

    # produce date_range
    if date_range:
        gte = datetime.strptime(date_range["from"], "%d-%m-%Y").strftime("%Y-%m-%dT%H:%M:%SZ")
        lte = datetime.strptime(date_range["to"], "%d-%m-%Y").strftime("%Y-%m-%dT%H:%M:%SZ")
        filter_content.append({
            "range": {
                "data.createdAt": {"gte": gte, "lte": lte}
            }
        })

    bool_q = {}
    if must:
        bool_q["must"] = must
    if filter_content:
        bool_q["filter"] = filter_content
    if should:
        bool_q["should"] = should
        bool_q["minimum_should_match"] = 1

    return {"bool": bool_q}


def handle_request(payload: str):
    """
    handle payload request, and return the filtered data from ES
    :param payload: json string contains content, tags, keywords,
                    scroll batch size, and maximum document count
    :return:
    """

    # produce payload, return none is no payload provided
    try:
        payload = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "Payload must be valid JSON"})

    batch_size = int(payload.get("size", 1000))
    max_docs = int(payload.get("max_docs", MAX_DOCS_DEFAULT))

    # building ES query_body
    query_body = {
        "track_total_hits": True,
        "_source": [
            "platform",
            "sentiment",
            "sentimentLabel",
            "keywords",
            "data.createdAt",
            "data.tags"
        ],
        "sort": [{"data.createdAt": {"order": "desc"}}],
        "query": query(payload)
    }

    es_auth = (config('ES_USERNAME'), config('ES_PASSWORD'))
    es = Elasticsearch(hosts=ES_HOST,
                       verify_certs=False,
                       ssl_show_warn=False,
                       basic_auth=es_auth)
    scroll_time = "2m"

    # start query
    resp = es.search(
        index=ES_INDEX,
        body=query_body,
        scroll=scroll_time,
        size=batch_size,

    )
    scroll_id = resp.get("_scroll_id")
    hits = resp["hits"]["hits"]
    docs = hits.copy()

    # scrolling query
    while hits and len(docs) < max_docs and scroll_id:
        resp = es.scroll(scroll_id=scroll_id, scroll=scroll_time)
        scroll_id = resp.get("_scroll_id") or ""
        hits = resp["hits"]["hits"]
        docs.extend(hits)

    # check scrolling id
    if scroll_id:
        try:
            es.clear_scroll(scroll_id=scroll_id)
        except Exception as e:
            current_app.logger.error(e)
            pass

    # produce output
    docs = docs[:max_docs]
    data = []
    for d in docs:
        src = d["_source"].copy()
        src["_id"] = d["_id"]
        data.append(src)

    return json.dumps({"total": len(data), "data": data}, ensure_ascii=False)


def main():
    # main function
    payload = request.get_data(as_text=True)
    return handle_request(payload)
