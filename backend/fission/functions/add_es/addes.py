"""
Mainly used to send data to ElasticSearch from Redis List
Only data that is structured correctly will end up being sent to ElasticSearch.
"""

from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse
from elasticsearch8 import Elasticsearch
from elasticsearch8.exceptions import ConflictError
from flask import request, current_app

CONFIG_MAP = "shared-data"
ES_URL = "https://elasticsearch-master.elastic.svc.cluster.local:9200"


def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()


def is_iso_datetime(time: str) -> bool:
    """
    Check is a legal ISO 8601 datetime string
    :param time: str
    :return: bool
    """
    try:
        if time.endswith("Z"):
            s_mod = time[:-1]
        else:
            s_mod = time
        datetime.fromisoformat(s_mod)
        return True
    except Exception as e:
        current_app.logger.error(f"Convert iso time error: {e}")
        return False


def legal_record(record: Dict[str, Any]) -> bool:
    """
    Check whether a record is valid
    If not a valid, drop it
    :param record: Dict[str, Any]
    :return: bool
    """

    # check keys
    for key in ("platform", "version", "fetchedAt", "sentiment", "sentimentLabel", "keywords", "data"):
        if key not in record:
            current_app.logger.error(f"A illegal record found")
            return False

    # check version value type
    if not isinstance(record["version"], (int, float)):
        current_app.logger.error(f"A illegal record found")
        return False

    # check fetchedAt value type
    if not isinstance(record["fetchedAt"], str) or not is_iso_datetime(record["fetchedAt"]):
        current_app.logger.error(f"A illegal record found")
        return False

    # check sentiment value type and range
    if not isinstance(record["sentiment"], float) or not -1 <= record["sentiment"] <= 1:
        current_app.logger.error(f"A illegal record found")
        return False

    # check sentimentLabel value
    if record.get("sentimentLabel") not in {"positive", "neutral", "negative"}:
        current_app.logger.error(f"A illegal record found")
        return False

    # check keywords type
    if (not isinstance(record.get("keywords", []), list) or
            not all(isinstance(k, str) for k in record.get("keywords", []))):
        current_app.logger.error(f"A illegal record found")
        return False

    # check sub values in data
    data = record["data"]
    for key in ("id", "createdAt", "content", "sensitive", "favouritesCount", "repliesCount", "tags", "url", "account"):
        if key not in data:
            current_app.logger.error(f"A illegal record found")
            return False

    # check data.id
    if not isinstance(data["id"], str) or not data["id"].strip():
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.createdAt
    if not isinstance(data["createdAt"], str) or not is_iso_datetime(data["createdAt"]):
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.content
    if not isinstance(data["content"], str) or not data["content"].strip():
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.sensitive
    if not isinstance(data["sensitive"], bool):
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.favouritesCount
    if not isinstance(data["favouritesCount"], int) or data["favouritesCount"] < 0:
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.repliesCount
    if not isinstance(data["repliesCount"], int) or data["favouritesCount"] < 0:
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.tags
    if not isinstance(data["tags"], list) or not all(isinstance(t, str) for t in data["tags"]):
        current_app.logger.error(f"A illegal record found")
        return False

    # check url
    try:
        url = urlparse(data["url"])
        if not (url.scheme and url.netloc):
            raise ValueError()
    except Exception as e:
        current_app.logger.warning(f"A illegal record found, post url: {e}")
        return False

    # check keys in data.account
    account = data["account"]
    for key in ("id", "username", "createdAt",
                "followersCount/linkKarma", "followingCount/commentKarma"):
        if key not in account:
            current_app.logger.error(f"A illegal record found")
            return False

    # check data.account.id
    if not isinstance(account["id"], str) or not account["id"].strip():
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.account.username
    if not isinstance(account["username"], str):
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.account.username
    if not isinstance(account["createdAt"], str) or not is_iso_datetime(account["createdAt"]):
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.account.username
    if not isinstance(account["followersCount/linkKarma"], int) or account["followersCount/linkKarma"] < 0:
        current_app.logger.error(f"A illegal record found")
        return False

    # check data.account.username
    if not isinstance(account["followingCount/commentKarma"], int) or account["followingCount/commentKarma"] < 0:
        current_app.logger.error(f"A illegal record found")
        return False

    return True


def main() -> str:
    """
    get data from redis list, check the data structure and send to elasticsearch
    """
    es_auth = (config('ES_USERNAME'), config('ES_PASSWORD'))

    es = Elasticsearch(
        ES_URL,
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=es_auth
    )

    # get data
    payload = request.get_json(force=True)
    records: List[Dict[str, Any]] = payload if isinstance(payload, list) else [payload]
    current_app.logger.info(f"Got {len(records)} record from queue")

    # check each data structure, only validated data send to ES
    for record in records:
        if not legal_record(record):
            continue

        post_id = record["data"]["id"]
        platform = record["platform"].lower()

        # ID is a combination of the platform name and post ID
        # only if the data with this ID does not exist, otherwise skips it
        try:
            es.index(
                index="socialplatform",
                id=f"{platform}_{post_id}",
                body=record,
                op_type='create'
            )
            current_app.logger.info(f"{platform}_{post_id} sent to ES successfully")
        except ConflictError as e:
            current_app.logger.error(f"An error happened while send to ES: {e}")

    return "OK"
