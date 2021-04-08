```bash
python manage.py migrate
```

then
```bash
uvicorn server.asgi:application --host 0.0.0.0 --port 8033 --log-level trace --reload
```

or

```bash
python start.py
```


You can then do:

```typescript
import * as Etebase from 'etebase';

const etebase = await Etebase.Account.signup({
  username: "craig",
  email: "craig@gliff.ai"
}, "SecretPassword1", "http://0.0.0.0:8033/etebase");

console.log(etebase)
```