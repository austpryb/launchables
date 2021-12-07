import requests
import json
from random import random

user = '0x5e7564d9942F2073d20C6B65d0e73750a6EC8D81'
data = {'username':user,'public_key':user}

req = requests.post('http://launchable-backend:5000/register-wallet/wallet', data=json.dumps(data))
print(req.content)
assert req.status_code == 200

print(req)
