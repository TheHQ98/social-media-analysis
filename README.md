# Mirror Notice!
This repository is a **mirror backup** of the original project hosted on GitLab:  
[https://gitlab.unimelb.edu.au/chenhaof/comp90024_team_55](https://gitlab.unimelb.edu.au/chenhaof/comp90024_team_55)

Please note that the original GitLab repository is **private** and not publicly accessible.

COMP90024 Assignment 2 **feedback** from Prof. Richard O. Sinnott
```
Report Comments. There was no need to submit your code in the zip file - a link to the gitlab repo would have been fine. You had three distinct scenarios: AFL, elections and cost of living. Certainly this should have had lots of data associated with it. The overall architecture as shown in Figure 3 is fine, but it could have been extended with some more details, e.g. the ElasticSearch indices, the API and the endpoints that were supported. It was nice that you explored all of the platforms (BlueSky, Mastodon, Reddit). 2.5m posts is a reasonable amount! It was nice that you collected the data and then decided on the scenarios (vs focusing on the scenarios and then trying to get the data which may or may not exist). The implementation section is nicely done and how the functions, triggers and processing works across the platforms. The pros and cons of NeCTAR and the related technologies could have been enhanced with insights based on your actual experiences. The error handling section was ok. The testing section was nicely defined. You might have also discussed end to end tests and shown examples of successful and failure test cases. The graphs, charts, analysis and discussions are nicely done. Overall the report was nicely done.

Implementation comments:
Overall: a good harvesting pipeline, but testing and API are of insufficient quality.
ReSTful API: the APi is composed of a single resource and incomplete, since a Jupyter notebook queries ES directly.
Architecture: ConfigMaps are used consistently; secrets are not used; use of message queues;
Harvesting: harvesting from Reddit, BlueSky, and Mastodon; large quantity of data harvested (3.5M posts, 5+GB); the harvesting of all three platforms is ongoing at the rate of about 50K per day.
Use of Fission: there are some leftover routes and functions from the workshop; use or routes, triggers, specs, and MQ triggers;
Use of ElasticSearch: use of shards; use of explicit mappings; use of pagination; use of complex queries;
Error handling: exceptions are often too wide in scope; inconsistent use of logging; no use of HTTP status codes.
Test quality: the tests look more like proof-of-concepts for harvesting from Mastodon than test cases.
Documentation: the README is minimal and leaves out testing, creation of ConfigMaps, and the index creation is wrong (the JSON does not exist).
Repo layout: overall clean repo.
Code quality: dependencies are versioned; the reading of ConfigMaps should have been put in a common library; some parameters should have been put in ConfigMaps.
```

# COMP90024_team_55  

### Our project report is [here](Report.pdf)

## Team

| Name       | Email                           | Student Number |
| ---------- | ------------------------------- | -------------- |
| Josh Feng  | chenhaof@student.unimelb.edu.au | 1266669        |
| Fan Yi     | yify@student.unimelb.edu.au     | 1193689        |
| Siyan Pan  | siyanpan@student.unimelb.edu.au | 1627057        |
| Shijia Gu  | shijiag1@student.unimelb.edu.au | 1266137        |
| Weiqi Chen | weiqchen@student.unimelb.edu.au | 1266370        |

## Folder Structure

```
Project/  
├─ backend/  
│  ├─ fission/  
│  │  ├─ functions/  
│  │  │  ├─ bluesky_harvester_tag/        --- bluesky harvester by search_term  
│  │  │  ├─ mastodon_harvester/           --- mastodon harvester by time_line  
│  │  │  ├─ mastodon_harvester_tag/       --- mastodon harvester by tag  
│  │  │  ├─ reddit_harvester_hot/         --- reddit harvester by hot  
│  │  │  ├─ reddit_harvester_tag/         --- reddit harvester by new  
│  │  │  ├─ enqueue/                      --- for passing data into Redis lists  
│  │  │  ├─ post_processor/               --- get data in Redis, process keyword extraction and sentiment analysis  
│  │  │  ├─ add_es/                       --- check data structure and put into Elastic Search (only valid data)  
├─ frontend/  
│  ├─ fission/  
│  │  ├─ functions/  
│  │  │  ├─ data_filter/                  --- deploy in Fission for API interface called by frontend, use for query  
│  ├─ frontend.ipynb                      --- scenario for AFL and Cost Living  
│  ├─ politics.ipynb                      --- scenario for Australian Election  
├─ database/  
│  ├─ socialplatform.yaml                 --- defining the structure of the socialplatform index in Elasticsearch  
├─ test/  
│  ├─ unitTest.py                         --- unit tests for back-end functions, used to check data structures  
│  ├─ mastodonApi.py  
├─ .gitignore  
├─ README.md
├─ Report.pdf
```

# Install
## Software Stack Installation

The Cluster environment used for this project was deployed with full reference and adherence to the [General Installation](https://gitlab.unimelb.edu.au/feit-comp90024/comp90024/-/blob/master/installation/README.md), [Fission FaaS](https://gitlab.unimelb.edu.au/feit-comp90024/comp90024/-/blob/master/fission/README.md) and [ElasticSearch](https://gitlab.unimelb.edu.au/feit-comp90024/comp90024/-/blob/master/elastic/README.md).

Base on the guide, we completed the installation and configuration of the following components:
- OpenStack
- Kubernetes cluster initialisation with 1 master node and 3 worker nodes
- Helm
- Fission
- ElasticSearch and Kibana
- Redis
- ConfigMap

For the Redis URL, we're only using: `redis://redis-headless.redis.svc.cluster.local:6379`

After install, the environment in Fission should contain:
```
(base) ➜  ~ fission env list
NAME      IMAGE                      BUILDER_IMAGE              POOLSIZE MINCPU MAXCPU MINMEMORY MAXMEMORY EXTNET GRACETIME NAMESPACE
nodejs    fission/node-env           fission/node-builder       3        0      0      0         0         false  0         default
python    fission/python-env         fission/python-builder     3        0      0      0         0         false  0         default
python39  fission/python-env-3.9     fission/python-builder-3.9 3        0      0      0         0         false  0         default
python39x lmorandini/python39x:1.0.0 fission/python-builder-3.9 3        0      0      0         0         false  0         default
```

In Config Map, assuming you have following config, otherwise some Fission function won't work:
```
(base) ➜  ~ kubectl get configmap
NAME               DATA   AGE
bluesky-config     2      8d
kube-root-ca.crt   1      29d
masto-config       2      27d
reddit-config      3      24d
reddit-config2     3      19d
shared-data        2      28d
```

```
(base) ➜  ~ kubectl describe configmap masto-config
Name:         masto-config
Namespace:    default
Labels:       <none>
Annotations:  <none>

Data
====
ACCESS_TOKEN:
----
YourAccessToken

API_BASE_URL:
----
https://mastodon.au


BinaryData
====

Events:  <none>
```
```
(base) ➜  ~ kubectl describe configmap reddit-config
Name:         reddit-config
Namespace:    default
Labels:       <none>
Annotations:  <none>

Data
====
REDDIT_CLIENT_SECRET:
----
YourSecret

REDDIT_USER_AGENT:
----
YourAgent

REDDIT_CLIENT_ID:
----
YourID


BinaryData
====

Events:  <none>
```
```
(base) ➜  ~ kubectl describe configmap bluesky-config
Name:         bluesky-config
Namespace:    default
Labels:       <none>
Annotations:  <none>

Data
====
BSKY_APP_PASSWORD:
----
YourPassword

BSKY_USERNAME:
----
YourUsername


BinaryData
====

Events:  <none>
```
## Install index in Elastic Search
Change location to `/database/`

Running `kubectl port-forward service/elasticsearch-master -n elastic 9200:9200` in your terminal

Install `socialplatform`:
```bash
curl -X PUT "http://localhost:9200/socialplatform" \
  -H "Content-Type: application/json" \
  -u elastic:elastic \
  -d @socialplatform.json
```
## Install enqueue, post_processor, add_es and harvesters MQTrigger in Fission
change your current directory in `backend/fission/`, and add yaml:
```bash
fission spec init

fission package create --spec --name enqueue \
    --source ./functions/enqueue/__init__.py \
    --source ./functions/enqueue/enqueue.py \
    --source ./functions/enqueue/requirements.txt \
    --source ./functions/enqueue/build.sh \
    --env python \
    --buildcmd './build.sh'
  fission function create --spec --name enqueue \
    --pkg enqueue \
    --env python \
    --entrypoint "enqueue.main"

fission package create --spec --name post-processor \
	--source ./functions/post_processor/__init__.py \
	--source ./functions/post_processor/post_processor.py \
	--source ./functions/post_processor/requirements.txt \
	--source ./functions/post_processor/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name post-processor \
    --pkg post-processor \
    --env python39x \
    --entrypoint "post_processor.main"

fission package create --spec --name addes \
	--source ./functions/add_es/__init__.py \
	--source ./functions/add_es/addes.py \
	--source ./functions/add_es/requirements.txt \
	--source ./functions/add_es/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name addes \
  --pkg addes \
  --env python39x \
  --configmap shared-data \
  --entrypoint "addes.main"

fission mqtrigger create --spec --name addes \
  --function addes \
  --mqtype redis \
  --mqtkind keda \
  --topic elastic \
  --errortopic addes_errors \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=100 \
  --metadata listName=elastic
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```
## Install Mastodon Harvesters
Note: you must install `post-process` and `addes` functions and corresponding MQTrigger in previous section, the following Mastodon harvesters will finally send the data into the Redis list called `mastodon`.
### Mastodon Harvester
install mastodon_harvester, function will fetch the latest 40 posts based on the timeline, the timer will call the function every 20 seconds, change your current directory in `backend/fission`. Add yaml:
``` bash
fission package create --spec --name mastodon-harvester \
	--source ./functions/mastodon_harvester/__init__.py \
	--source ./functions/mastodon_harvester/mastodon_harvester.py \
	--source ./functions/mastodon_harvester/requirements.txt \
	--source ./functions/mastodon_harvester/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name mastodon-harvester \
    --pkg mastodon-harvester \
    --env python39x \
    --configmap masto-config \
    --entrypoint "mastodon_harvester.main"

fission timer create --spec \
	--name mastodon-harvester \
	--function mastodon-harvester \
	--cron "@every 20s"

fission mqtrigger create --spec --name mastodon-postprocessor \
  --function post-processor \
  --mqtype redis \
  --mqtkind keda \
  --topic mastodon \
  --errortopic post_mastodon_errors \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=100 \
  --metadata listName=mastodon
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```
### Mastodon Harvester Tag
Install mastodon_harvester_tag.
In Redis, you need to create a list called `mastodon:tags`, add the tags in the list, and the function will crawl all the posts related to the tags from 1st of Jan, 2023 to now.

change your current directory in `backend/fission/`. Add yaml:
```bash
fission package create --spec --name mastodon-harvester-tag \
	--source ./functions/mastodon_harvester_tag/__init__.py \
	--source ./functions/mastodon_harvester_tag/mastodon_harvester_tag.py \
	--source ./functions/mastodon_harvester_tag/requirements.txt \
	--source ./functions/mastodon_harvester_tag/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name mastodon-harvester-tag \
    --pkg mastodon-harvester-tag \
    --env python39x \
    --configmap masto-config \
    --entrypoint "mastodon_harvester_tag.main"

fission timer create --spec \
	--name mastodon-harvester-tag \
	--function mastodon-harvester-tag \
	--cron "@every 30s"
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```

## Install Reddit Harvesters
Note: you must install `post-process` and `addes` functions and corresponding MQTrigger in previous section, the following Reddit harvesters will finally send the data into the Redis list called `reddit`.
### Reddit Harvester tag
Install reddit_harvester_tag, the function will crawl based on `new` list in Reddit

In Redis, you need to create a list called `reddit:tags`, add the tags in the list, and the function will crawl all the posts related to the tags.

change your current directory in `backend/fission/`. Add yaml:
```bash
fission package create --spec --name reddit-harvester-tag \
	--source ./functions/reddit_harvester_tag/__init__.py \
	--source ./functions/reddit_harvester_tag/reddit_harvester_tag.py \
	--source ./functions/reddit_harvester_tag/requirements.txt \
	--source ./functions/reddit_harvester_tag/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name reddit-harvester-tag \
    --pkg reddit-harvester-tag \
    --env python39x \
    --configmap reddit-config2 \
    --entrypoint "reddit_harvester_tag.main"

fission timer create --spec \
	--name reddit-harvester-tag \
	--function reddit-harvester-tag \
	--cron "@every 60s"

fission mqtrigger create --spec --name reddit-postprocessor \
  --function post-processor \
  --mqtype redis \
  --mqtkind keda \
  --topic reddit \
  --errortopic post_reddit_errors \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=100 \
  --metadata listName=reddit
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```

### Reddit Harvester Hot
Install reddit_harvester_hot, the function will crawl 40 post a time based on `hot` list in Reddit

In Redis, you need to create a list called `reddit:hot`, add the tags in the list, and the function will crawl all the posts related to the tags, 40 post each time.

change your current directory in `backend/fission`. Add yaml:
```bash
fission package create --spec --name reddit-harvester-hot \
	--source ./functions/reddit_harvester_hot/__init__.py \
	--source ./functions/reddit_harvester_hot/reddit_harvester_hot.py \
	--source ./functions/reddit_harvester_hot/requirements.txt \
	--source ./functions/reddit_harvester_hot/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name reddit-harvester-hot \
    --pkg reddit-harvester-hot \
    --env python39x \
    --configmap reddit-config2 \
    --entrypoint "reddit_harvester_hot.main"

fission timer create --spec \
	--name reddit-harvester-hot \
	--function reddit-harvester-hot \
	--cron "@every 60s"
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```

## Install Bluesky Harvester
Note: you must install `post-process` and `addes` functions and corresponding MQTrigger in previous section, the following Bluesky harvester will finally send the data into the Redis list called `bluesky`.

Install bluesky_harvester_tag, the function will crawl 40 post a time based `search_term`

In Redis, you need to create a list called `bluesky:tags`, add the tags in the list, and the function will crawl all the posts related to the tags, 40 post each time.

change your current directory in `backend/fission/`. Add yaml:
```bash
fission package create --spec --name bluesky-harvester-tag \
	--source ./functions/bluesky_harvester_tag/__init__.py \
	--source ./functions/bluesky_harvester_tag/bluesky_harvester_tag.py \
	--source ./functions/bluesky_harvester_tag/requirements.txt \
	--source ./functions/bluesky_harvester_tag/build.sh \
	--env python39 \
	--buildcmd './build.sh'

fission function create --spec --name bluesky-harvester-tag \
    --pkg bluesky-harvester-tag \
    --env python39 \
    --configmap bluesky-config \
    --entrypoint "bluesky_harvester_tag.main"

fission timer create --spec \
	--name bluesky-harvester-tag \
	--function bluesky-harvester-tag \
	--cron "@every 30s"

fission mqtrigger create --spec --name bluesky-postprocessor \
  --function post-processor \
  --mqtype redis \
  --mqtkind keda \
  --topic bluesky \
  --errortopic post_bluesky_errors \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=100 \
  --metadata listName=bluesky
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```
## Install frontend data-filter in Fission
`data-filter`: frontend oriented query interface service, as a system dedicated to the front-end to provide data filtering and search service interface

change your current directory in `frontend/fission/`. Add yaml:
```bash
fission spec init

fission package create --spec --name data-filter \
	--source ./functions/data_filter/__init__.py \
	--source ./functions/data_filter/data_filter.py \
	--source ./functions/data_filter/requirements.txt \
	--source ./functions/data_filter/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name data-filter \
  --pkg data-filter \
  --env python39x \
  --configmap shared-data \
  --entrypoint "data_filter.main"

fission route create --spec --name data-filter \
  --method POST \
  --url /data-filter \
  --function data-filter
```
and apply into the Cluster:
```bash
fission spec apply --specdir specs --wait
```

## Use frontend
In `frontend` folder, there are two frontend `ipynb`. The `frontend.ipynb` contain the scenario for AFL and Cost Living, and `politics.ipynb` contain the scenario for Australia Election

Note: before running the cell, you need to run `kubectl port-forward svc/router 8888:80 -n fission` in your terminal
