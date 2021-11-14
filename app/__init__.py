import logging
from flask import Flask, send_from_directory, request
from flask_appbuilder import AppBuilder, SQLA
from flask_appbuilder.menu import Menu
from .sec import WalletSecurityManager
from .index import IndexView

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object("config")

db = SQLA(app)

appbuilder = AppBuilder(app, db.session, menu=Menu(reverse=True), security_manager_class=WalletSecurityManager, indexview=IndexView, base_template='web3_base.html')

#white = ['http://localhost:8080','http://localhost:9000','http://localhost:3000','http://localhost:5000']

#@app.after_request
#def add_cors_headers(response):
#    r = request.referrer[:-1]
#    if r in white:
#        response.headers.add('Access-Control-Allow-Origin', r)
#        response.headers.add('Access-Control-Allow-Origin', '*')
#        response.headers.add('Access-Control-Allow-Credentials', 'true')
#        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
#        response.headers.add('Access-Control-Allow-Headers', 'Cache-Control')
#        response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With')
#        response.headers.add('Access-Control-Allow-Headers', 'Authorization')
#        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
#    return response

#@app.route("/static/<path>")
#def static_dir(path):
    #return send_from_directory("build/static", path)
    #return send_from_directory("dist", path)

from . import views
