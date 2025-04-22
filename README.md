# COMP90024_team_55



## install mastodon script

```bash

fission package create --spec --name mastodon_harvester \
	--source ./functions/mastodon_harvester/__init__.py \
	--source ./functions/mastodon_harvester/mastodon_harvester.py \
	--source ./functions/mastodon_harvester/requirements.txt \
	--source ./functions/mastodon_harvester/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name mastodon_harvester \
    --pkg mastodon_harvester \
    --env python39x \
    --configmap masto-config \
    --entrypoint "mastodonApi.main"


fission package create --spec --name addes \
	--source ./functions/add_es/__init__.py \
	--source ./functions/add_es/addes.py \
	--source ./functions/add_es/requirements.txt \
	--source ./functions/add_es/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name addes \
  --pkg addes \
  --env python \
  --entrypoint "addes.main"

fission timer create --spec \
	--name mastodon_harvester-api \
	--function mastodon_harvester \
	--cron "@every 30s"

fission httptrigger create --spec \
	--name mastodon_harvester-trigger \
	--url "/mastodon" \
	--method GET \
	--function mastodon_harvester

fission mqtrigger create --spec --name mastodon_harvester-addes \
  --function addes \
  --mqtype redis \
  --mqtkind keda \
  --topic mastodon_harvester \
  --errortopic errors \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=100 \
  --metadata listName=mastodon_harvester
```