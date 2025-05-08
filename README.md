# COMP90024_team_55



## mastodon (fetch by timeline_public) script yaml file

```bash
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
```

## mastodon by fetch tag (fetch by timeline_hashtag) script yaml file
Note: program takes the tags from the Redis list called `mastodon:tags` and crawls them in order.

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

## mastodon post-processor yaml file

```bash
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

## addes yaml file

```bash
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