import requests 
import json
from random import random

user = '0x64ab13a5Ce815beDDe590C4B9953e82cf016C548'
data = {'username':user,'public_key':user}

req = requests.post('http://localhost:5000/register-wallet/wallet', data=json.dumps(data))
print(req.content)
assert req.status_code == 200

print(req)
