import os
from flask_appbuilder.security.views import UserDBModelView, AuthDBView
from flask_babel import lazy_gettext
from flask_appbuilder.views import expose
from flask import abort, current_app, flash, g, redirect, request, session, url_for
from flask_babel import lazy_gettext
from flask_login import login_user, logout_user
from flask_appbuilder.forms import DynamicForm
from wtforms import StringField
from wtforms.validators import DataRequired
from web3 import Web3
from eth_account.messages import encode_defunct
from flask_appbuilder._compat import as_unicode
from flask_appbuilder import ModelView
from flask_appbuilder.utils.base import lazy_formatter_gettext
from flask_appbuilder.security.decorators import has_access
from werkzeug.wrappers import Response as WerkzeugResponse
from wtforms.validators import EqualTo
from flask_babel import gettext
from wtforms.validators import ValidationError
import requests
from .models import Wallet, random_integer
import json
from flask import Flask, jsonify, request
from flask_appbuilder.const import (
    API_SECURITY_ACCESS_TOKEN_KEY,
    API_SECURITY_PASSWORD_KEY,
    API_SECURITY_PROVIDER_DB,
    API_SECURITY_PROVIDER_KEY,
    API_SECURITY_PROVIDER_LDAP,
    API_SECURITY_REFRESH_KEY,
    API_SECURITY_REFRESH_TOKEN_KEY,
    API_SECURITY_USERNAME_KEY,
    API_SECURITY_VERSION
)
from web3 import Web3
import eth_account
from .config import WEB3_INFURA_PROJECT_HTTPS
APPLICATION_HOST = 'http://localhost:5000'

class WalletModelView(UserDBModelView):

    show_fieldsets = [
        (
            lazy_gettext("Wallet info"),
            {"fields": ["username", "public_key", "nonce", "active"]},
        ),
        (
            lazy_gettext("Audit Info"),
            {
                "fields": [
                    "last_login",
                    "fail_login_count",
                    "created_on",
                    "created_by",
                    "changed_on",
                    "changed_by",
                ],
                "expanded": False,
            },
        ),
    ]

    user_show_fieldsets = [
        (
            lazy_gettext("Wallet info"),
            {"fields": ["username","public_key","nonce","active"]},
        )
    ]

    add_columns = [
        "username",
        "public_key",
        "first_name",
        "last_name",
        "nonce",
        "active",
    ]
    list_columns = [
        "username",
        "public_key",
        "nonce",
        "active",
    ]
    edit_columns = [
        "username",
        "public_key",
        "first_name",
        "last_name",
        "nonce",
        "active",
    ]

def validate_message(form, field):
    url = url_for('WalletAuthView.nonce', public_key=form.data['public_key'])
    try:
        url = requests.get(APPLICATION_HOST + url)
        print(url)
        if url.status_code == 200:
            nonce = json.loads(url.content)['nonce']
            if field.data != str(nonce) or nonce == str(None):
                raise ValidationError('Signed message must must match serverside nonce')
    except Exception as e:
        print(e)
        raise ValidationError('Nonce api down')

class WalletAuthForm(DynamicForm):
    public_key = StringField(lazy_gettext("Wallet (Public Key)"), validators=[DataRequired()])
    message = StringField(lazy_gettext("Signed Message"), validators=[DataRequired(), validate_message])

class WalletAuthView(AuthDBView):
    basedir = os.path.abspath(os.path.dirname(__file__))
    #login_template = "login_wallet.html"

    def get_nonce(self, public_key):
        try:
            nonce = self.appbuilder.session.query(Wallet.nonce).filter(Wallet.public_key == public_key).first()
            if nonce:
                #update_nonce = random_integer()
                #return appbuilder.session.query.query(Wallet.nonce).filter(Wallet.public_address == public_address).update({'nonce': update_nonce})
                self.appbuilder.session.close()
                return nonce[0]
            else:
                return None
        except Exception as e:
            print(e)
            return None

    def build_preflight_response(self):
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

    @expose("/nonce/<public_key>", methods=["GET"])
    def nonce(self, public_key):
        nonce = self.get_nonce(public_key)
        response = jsonify(nonce=nonce)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @expose("/signature/<signature>/<public_key>/<hash>", methods=["GET","POST","OPTIONS"])
    def signature(self, signature, public_key, hash):
        if request.method == 'OPTIONS':
            return build_preflight_response()

        elif request.method == 'POST':
            wallet = self.appbuilder.sm.auth_wallet(signature, public_key, hash)
            if not wallet:
                return jsonify(wallet=None, success=False)
                #return redirect(self.appbuilder.get_url_for_login)
            print('AUTH WALLET EXECUTED: ', wallet.public_key)
            login_user(wallet, remember=False)
            response = jsonify(wallet=wallet.public_key, url=self.appbuilder.get_url_for_index)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response

        elif request.method == 'GET':
            if g.user is not None and g.user.is_authenticated:
                return redirect(self.appbuilder.get_url_for_index)
            wallet = self.appbuilder.sm.auth_wallet(signature, public_key, hash)
            print('AUTH WALLET EXECUTED: ', wallet)
            if not wallet:
                flash(as_unicode(self.invalid_login_message), "warning")
                return jsonify(wallet=None, success=False)
                #return redirect(self.appbuilder.get_url_for_login)
            login_user(wallet, remember=False)
            return redirect(self.appbuilder.get_url_for_index)

            #return self.render_template(
            #    self.login_template, title=self.title, form=form, appbuilder=self.appbuilder
            #)

    #@expose("/login/", methods=["GET", "POST"])
    #def login(self):
    #    if g.user is not None and g.user.is_authenticated:
    #        return redirect(self.appbuilder.get_url_for_index)
    #    self.update_redirect()
    #    return redirect(self.appbuilder.get_url_for_login)
        #return self.render_template('web3.html')

    #@expose("/login-deprecated/", methods=["GET", "POST"])
    #def login_deprecated(self):
    #    if g.user is not None and g.user.is_authenticated:
    #        return redirect(self.appbuilder.get_url_for_index)

    #    form = WalletAuthForm()

    #    if form.validate_on_submit():
    #        w3 = Web3(Web3.HTTPProvider(self.appbuilder.app.config['WEB3_INFURA_PROJECT_HTTPS']))
    #        encoded_message = encode_defunct(bytes(form.message.data, encoding='utf8'))
    #        user = self.appbuilder.sm.auth_wallet(form.public_key.data, form.message.data)
    #        if not user:
    #            flash(as_unicode(self.invalid_login_message), "warning")
    #            return redirect(self.appbuilder.get_url_for_login)
    #        login_user(user, remember=False)
    #        print('Logged In User')
    #        return redirect(self.appbuilder.get_url_for_index)
    #    return self.render_template(
    #        self.login_template, title=self.title, form=form, appbuilder=self.appbuilder
    #    )

def _roles_custom_formatter(string: str) -> str:
    if current_app.config.get("AUTH_ROLES_SYNC_AT_LOGIN", False):
        string += (
            ". <div class='alert alert-warning' role='alert'>"
            "AUTH_ROLES_SYNC_AT_LOGIN is enabled, changes to this field will "
            "not persist between user logins."
            "</div>"
        )
    return string

class WalletModelView(ModelView):
    route_base = "/users"

    list_title = lazy_gettext("List Users")
    show_title = lazy_gettext("Show User")
    add_title = lazy_gettext("Add User")
    edit_title = lazy_gettext("Edit User")

    label_columns = {
        "public_key": lazy_gettext("Public Key"),
        "username": lazy_gettext("User Name"),
        "nonce": lazy_gettext("Nonce"),
        "active": lazy_gettext("Is Active?"),
        "roles": lazy_gettext("Role"),
        "last_login": lazy_gettext("Last login"),
        "login_count": lazy_gettext("Login count"),
        "fail_login_count": lazy_gettext("Failed login count"),
        "created_on": lazy_gettext("Created on"),
        "created_by": lazy_gettext("Created by"),
        "changed_on": lazy_gettext("Changed on"),
        "changed_by": lazy_gettext("Changed by"),
    }

    description_columns = {
        "public_key": lazy_gettext("The wallet's public key"),
        "username": lazy_gettext(
            "Wallet valid for authentication"
        ),
        "nonce": lazy_gettext("The wallet's nonce for validation"),
        "active": lazy_gettext(
            "It's not a good policy to remove the wallet address, just make it inactive"
        ),
        "roles": lazy_formatter_gettext(
            "The user role on the application,"
            " this will associate with a list of permissions",
            _roles_custom_formatter,
        ),
    }

    list_columns = ["username", "public_key", "active", "roles"]

    show_fieldsets = [
        (
            lazy_gettext("Wallet info"),
            {"fields": ["public_key", "nonce", "active", "roles", "login_count"]},
        ),
        (
            lazy_gettext("Audit Info"),
            {
                "fields": [
                    "last_login",
                    "fail_login_count",
                    "created_on",
                    "created_by",
                    "changed_on",
                    "changed_by",
                ],
                "expanded": False,
            },
        ),
    ]

    user_show_fieldsets = [
        (
            lazy_gettext("Wallet info"),
            {"fields": ["public_key", "active", "roles", "login_count"]},
        ),
    ]

    search_exclude_columns = ["password"]

    add_columns = ["public_key", "username", "first_name", "last_name", "email", "active", "roles"]
    edit_columns = ["public_key", "username", "first_name", "last_name", "email", "active", "roles"]
    user_info_title = lazy_gettext("Your wallet details")

    @expose("/userinfo/")
    @has_access
    def userinfo(self) -> WerkzeugResponse:
        item = self.datamodel.get(g.user.id, self._base_filters)
        widgets = self._get_show_widget(
            g.user.id, item, show_fieldsets=self.user_show_fieldsets
        )
        self.update_redirect()
        return self.render_template(
            self.show_template,
            title=self.user_info_title,
            widgets=widgets,
            appbuilder=self.appbuilder,
        )
