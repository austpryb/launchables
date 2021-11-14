import requests
import json
from random import random

user = '0x64ab13a5Ce815beDDe590C4B9953e82cf016C548'
message = '0xfee0cf7bf681dee21491a37f9f85d0db045f3f8943cd0143b3a2de58d1f7ab713147e0bffce2501edb44cb05b9a7a6f8100ffd7abf5f0e1cb4421053db527c4a1b'
_hash = '123'

nonce = requests.get('http://localhost:5000/nonce/{}'.format(user))
assert nonce.status_code == 200 
nonce = json.loads(nonce.content)['nonce']
print(nonce)

auth = requests.post('http://localhost:5000/signature/{signature}/{public_key}/{_hash}'.format(signature=message, public_key=user, _hash=_hash))
assert auth.status_code == 200 
auth = json.loads(auth.content)
print(auth)

