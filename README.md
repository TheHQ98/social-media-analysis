# COMP90024_team_55



## install mastodon script

```bash

fission package create --spec --name mastodon \
	--source ./functions/mastodon/__init__.py \
	--source ./functions/mastodon/mastodonApi.py \
	--source ./functions/mastodon/requirements.txt \
	--source ./functions/mastodon/build.sh \
	--env python39x \
	--buildcmd './build.sh'

fission function create --spec --name mastodon \
    --pkg mastodon \
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
	--function mastodon \
	--cron "@every 30s"

fission httptrigger create --spec \
	--name mastodon-trigger \
	--url "/mastodon" \
	--method GET \
	--function mastodon

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