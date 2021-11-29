import os

basedir = os.path.abspath(os.path.dirname(__file__))

#FLASK_ENV='development'
#FLASK_DEBUG=1
APP_ICON='https://gateway.pinata.cloud/ipfs/'
APP_ICON_WIDTH = 300
CSRF_ENABLED = True
SECRET_KEY = "launchable"
WEB3_INFURA_PROJECT_HTTPS='https://mainnet.infura.io/v3/'
PINATA_API_SECRET_KEY='37e14eb.....'
PINATA_API_KEY='4471dfe6d......'
APPLICATION_HOST = 'http://localhost:5000'

OPENID_PROVIDERS = [
    {"name": "Google", "url": "https://www.google.com/accounts/o8/id"},
    {"name": "Yahoo", "url": "https://me.yahoo.com"},
    {"name": "AOL", "url": "http://openid.aol.com/<username>"},
    {"name": "Flickr", "url": "http://www.flickr.com/<username>"},
    {"name": "MyOpenID", "url": "https://www.myopenid.com"},
]

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")

AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Public"
RECAPTCHA_PUBLIC_KEY = "6LedRP0SAAAAAOF03Nsv_ny2NzOF_Dthe_Xn269v"
RECAPTCHA_PRIVATE_KEY = "6LedRP0SAAAAAPnsdEKgj5VU1QbFcPv7mO8cW0So"

MAIL_PORT = 587
MAIL_USE_SSL = False
MAIL_SERVER = "smtp.gmail.com"
MAIL_USE_TLS = True
MAIL_USERNAME = ""
MAIL_PASSWORD = ""
MAIL_DEFAULT_SENDER = ""

# ------------------------------
# GLOBALS FOR GENERAL APP's
# ------------------------------
UPLOAD_FOLDER = basedir + "/app/static/uploads/"
TEMPLATES_FOLDER = basedir + "/app/static/appbuilder/"
IMG_UPLOAD_FOLDER = basedir + "/app/static/uploads/"
IMG_UPLOAD_URL = "/static/uploads/"
FILE_ALLOWED_EXTENSIONS = ("txt", "pdf", "jpeg", "jpg", "gif", "png")
AUTH_TYPE = 1
# AUTH_LDAP_SERVER = "ldap://dc.domain.net"
AUTH_ROLE_ADMIN = "Admin"
AUTH_ROLE_PUBLIC = "Public"
APP_NAME = "Launchables"
##APP_THEME = "darkly.css"
#APP_THEME = "vapor.css"
# APP_THEME = "amelia.css"
# APP_THEME = "cosmo.css"
# APP_THEME = "cyborg.css"       # COOL
# APP_THEME = "flatly.css"
# APP_THEME = "journal.css"
# APP_THEME = "readable.css"
# APP_THEME = "simplex.css"
# APP_THEME = "slate.css"          # COOL
# APP_THEME = "spacelab.css"      # NICE
# APP_THEME = "united.css"
