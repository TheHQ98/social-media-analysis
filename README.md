# COMP90024_team_55



## install mastondon script

```bash

fission package create --spec --name mastondon \
	--source ./functions/mastondon/__init__.py \
	--source ./functions/mastondon/mastodonApi.py \
	--source ./functions/mastondon/requirements.txt \
	--source ./functions/mastondon/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name mastondon \
    --pkg mastondon \
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
	--name mastodon-api \
	--function mastondon \
	--cron "@every 30s"

fission httptrigger create --spec \
	--name mastondon-trigger \
	--url "/mastodon" \
	--method GET \
	--function mastondon

fission mqtrigger create --spec --name mastodon-addes \
  --function addes \
  --mqtype redis \
  --mqtkind keda \
  --topic mastodon \
  --errortopic errors \
  --maxretries 3 \
  --metadata address=redis-headless.redis.svc.cluster.local:6379 \
  --metadata listLength=100 \
  --metadata listName=mastodon
```