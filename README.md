# STORE

This is a Django app consisting of 3 parts:

`/etebase` is an etebase server
`/api` are the store endpoints (authd using etebase access tokens)
`/django/(/admin)` the django application 


## Setup

```bash
git submodule init
git submodule update
cp -r package_tools/* etebase_server/
pip install -r requirements.txt
rm -r etebase_server/myauth # we use our copy of this one level up
```

## Running

```bash
python manage.py makemigrations
python manage.py migrate
```

then

```bash
uvicorn server.asgi:app --host 0.0.0.0 --port 8000 --log-level trace --reload
```
or
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
Production TBD
