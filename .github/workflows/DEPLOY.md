Django migrations are currently manual:

```bash
az webapp ssh --resource-group gliff_staging --name store-staging-gliff

```

then:

```bash
cd $APP_PATH
source /antenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

The DB env vars are set in Azure