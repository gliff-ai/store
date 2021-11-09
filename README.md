# STORE

This is a Django app consisting of 3 parts:

`/etebase` is an etebase server
`/api` are the store endpoints (authd using etebase access tokens)
`/django/(/admin)` the django application 


## Setup (development)

```bash
git submodule init
git submodule update
rm -r etebase-server/myauth # we use our copy of this one level up
pipenv sync --dev
```

## Setup (deployment)

```bash
git submodule init
git submodule update
rm -r etebase-server/myauth # we use our copy of this one level up
pip install -r requirements.txt
```

## Adding `new-package`

```bash
pipenv install new-package
pipenv lock -r --dev > requirements.txt
```

### Adding `new-dev-package`

```bash
pipenv install --dev new-dev-package
pipenv lock -r --dev > requirements.txt
```

## Running (with `pipenv run` if development)

```bash
python manage.py makemigrations
python manage.py migrate
```

then

```bash
python start.py
```

You can then do something like:

```typescript
import * as Etebase from 'etebase';

const etebase = await Etebase.Account.signup({
  username: "craig",
  email: "craig@gliff.ai"
}, "SecretPassword1", "http://0.0.0.0:8000/etebase");

console.log(etebase);

const { authToken } = etebase;

fetch("http://0.0.0.0:8000/api", {
  headers: {
    "Content-Type": "application/json",
    Authorization: `Token ${authToken}`,
  },
}).then((response) => response.json())
  .then((data) => console.log(data));
```

There's also a Docker image if preferred.

## Deploying

Staging deploys to: https://store.staging.gliff.app/
Production https://store.gliff.app/

## Black Box Tests

These run against the API with a clean sqlite instance on port 8000. 
Definitely don't run them when pointing at a real DB unless you are 1000% certain
The target can be changed by setting `BASE_URL` as an env var before running npm test, the default is `http://localhost:8000`

One time: `cd __tests__ && npm i` (Requires Node 16)

Run as normal (with `DJANGO_SETTINGS_MODULE=server.settings.test`)

then `cd __tests__ && npm run test`