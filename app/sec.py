from flask_appbuilder.security.sqla.manager import SecurityManager
from flask_appbuilder.security.api import SecurityApi, safe
from flask_appbuilder.views import expose
from flask_appbuilder import const as c
from flask import request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_refresh_token_required,
)
import uuid
import logging
from werkzeug.security import ( generate_password_hash, check_password_hash )
from .models import Wallet, RegisterWallet, random_integer
from .sec_views import WalletModelView, WalletAuthView, WalletModelView
import json
from flask_appbuilder.const import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OAUTH,
    AUTH_OID,
    AUTH_REMOTE_USER,
    LOGMSG_ERR_SEC_ADD_REGISTER_USER,
    LOGMSG_ERR_SEC_AUTH_LDAP,
    LOGMSG_ERR_SEC_AUTH_LDAP_TLS,
    LOGMSG_WAR_SEC_LOGIN_FAILED,
    LOGMSG_WAR_SEC_NO_USER,
    LOGMSG_WAR_SEC_NOLDAP_OBJ,
    PERMISSION_PREFIX,
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
from hexbytes import HexBytes
import os

log = logging.getLogger(__name__)

class WalletSecurityApi(SecurityApi):

    resource_name = "security"
    version = API_SECURITY_VERSION
    openapi_spec_tag = "Security"

    def add_apispec_components(self, api_spec):
        super(SecurityApi, self).add_apispec_components(api_spec)
        jwt_scheme = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        api_spec.components.security_scheme("jwt", jwt_scheme)
        api_spec.components.security_scheme("jwt_refresh", jwt_scheme)

    @expose("/login", methods=["POST"])
    @safe
    def login(self):
        if not request.is_json:
            return self.response_400(message="Request payload is not JSON")
        username = request.json.get('public_key', None)
        public_key = request.json.get('public_key', None)
        nonce = request.json.get('nonce', None)
        provider = request.json.get(API_SECURITY_PROVIDER_KEY, None)
        refresh = request.json.get(API_SECURITY_REFRESH_KEY, False)
        if not username or not nonce or not public_key:
            return self.response_400(message="Missing required parameter")
        if provider == 'wallet':
            user = self.appbuilder.sm.auth_wallet(public_key, nonce)
        elif provider == 'avax':
            password = request.json.get('password', None)
            user = self.appbuilder.sm.auth_avax(username, password)
        elif provider == API_SECURITY_PROVIDER_DB:
            user = self.appbuilder.sm.auth_user_db(username, password)
        else:
            return self.response_400(
                message="Provider {} not supported".format(provider)
            )
        if not user:
            return self.response_401()

        resp = dict()
        resp[API_SECURITY_ACCESS_TOKEN_KEY] = create_access_token(
            identity=user.id, fresh=True
        )
        if refresh:
            resp[API_SECURITY_REFRESH_TOKEN_KEY] = create_refresh_token(
                identity=user.id
            )
        return self.response(200, **resp)

    @expose("/refresh", methods=["POST"])
    @jwt_refresh_token_required
    @safe
    def refresh(self):
        resp = {
            API_SECURITY_ACCESS_TOKEN_KEY: create_access_token(
                identity=get_jwt_identity(), fresh=False
            )
        }
        return self.response(200, **resp)

class WalletSecurityManager(SecurityManager):

    user_view = WalletModelView
    user_model = Wallet
    userdbmodelview = WalletModelView
    registeruser_model = RegisterWallet
    security_api = WalletSecurityApi
    authdbview = WalletAuthView
    #web3_infura_https=os.environ.get('WEB3_INFURA_PROJECT_HTTPS')

    @property
    def get_url_for_registeruser(self):
        return url_for(
            "%s.%s"
            % (self.registeruser_view.endpoint, self.registeruser_view.default_view)
        )

    def add_wallet_registration(
        self, username="", public_key="" #, nonce=""
    ):
        wallet = self.registeruser_model()
        wallet.username = username
        wallet.email = ""
        wallet.first_name = ""
        wallet.last_name = ""
        wallet.public_key = public_key
        registration_hash = str(uuid.uuid1())
        wallet.registration_hash = registration_hash
        wallet.registration_hash_url = url_for(
            ".activation",
            _external=True,
            activation_hash=registration_hash,
        )
        try:
            self.get_session.add(wallet)
            self.get_session.commit()
            return wallet
        except Exception as e:
            log.error(c.LOGMSG_ERR_SEC_ADD_REGISTER_USER.format(str(e)))
            self.appbuilder.get_session.rollback()
            return None

    def del_wallet(self, wallet):
        try:
            self.get_session.delete(wallet)
            self.get_session.commit()
            return True
        except Exception as e:
            log.error(c.LOGMSG_ERR_SEC_DEL_REGISTER_USER.format(str(e)))
            self.get_session.rollback()
            return False

    def register_wallet(self, wallet):
        url = url_for(
            ".activation",
            _external=True,
            activation_hash=wallet.registration_hash,
        )
        try:
            return True
        except Exception as e:
            log.error("Registration exception: {0}".format(str(e)))
            return False

    def send_signing_request(wallet):
        return True

    def add_registration(self, username, public_key):
        wallet = self.add_wallet_registration(
            username, public_key
                )
        if wallet:
            if self.send_signing_request(wallet):
                return wallet
        else:
            self.del_wallet(wallet)
            return None

    def add_wallet(
        self,
        username,
        public_key,
        role
    ):
        try:
            wallet = self.user_model()
            wallet.public_key = public_key
            wallet.username = username
            wallet.email = ""
            wallet.first_name = ""
            wallet.last_name = ""
            wallet.active = True
            wallet.roles = role if isinstance(role, list) else [role]
            self.get_session.add(wallet)
            self.get_session.commit()
            log.info(c.LOGMSG_INF_SEC_ADD_USER.format(username))
            return wallet
        except Exception as e:
            log.error(c.LOGMSG_ERR_SEC_ADD_USER.format(str(e)))
            self.get_session.rollback()
            return False

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
            log.info(e)
            return None

    def recover_address(self, signature, hash, public_key):
        try:
            w3 = Web3(Web3.HTTPProvider(os.environ.get('WEB3_INFURA_PROJECT_HTTPS')))
            assert w3.isConnected() == True, 'Web3 Cannot Connect to Provider'
            nonce = self.get_nonce(public_key)
            log.info('SIGNATURE: {}'.format(signature))
            log.info('MESSAGE HASH: {}'.format(hash))
            log.info('CHECK NONCE: {}'.format(nonce))
            # encoded_message = encode_defunct(bytes(message, encoding='utf8'))  #'9999999'
            message_hash = eth_account.messages.defunct_hash_message(text=str(nonce))
            # address = w3.eth.account.recoverHash(message_hash, signature=signature)
            address = w3.eth.account.recoverHash(message_hash, signature=signature)
            log.info('RECOVERED ADDRESS: {}'.format(address))
            return address
        except AssertionError:
            log.error('Failed to connect to Web3 Provider')
            return False

    def validate_signature(self, signature, public_key, hash):
        try:
            recovered_public_key = self.recover_address(signature, hash, public_key)
            if recovered_public_key == '' or recovered_public_key == None:
                log.info('Web3 Failed to Connect: {}'.format(nonce))
            else:
                nonce = self.get_nonce(public_key) # Need to check the nonce against the recovered nonce
                log.info('CONTROL NONCE: {}'.format(nonce))
                return recovered_public_key
        except Exception as e:
            log.info(e)
            return None

    def check_public_key_signature(self, signature, public_key, hash):
        validation = True if public_key == self.validate_signature(signature, public_key, hash) else None
        return validation

    def auth_wallet(self, signature, public_key, hash):
        log.info("AUTH ATTEMPT BY {}".format(public_key))
        if public_key is None or public_key == "":
            return None
        user = self.find_user(username=public_key)
        if user is None or (not user.is_active):
            check_password_hash(
                "pbkdf2:sha256:150000$Z3t6fmj2$22da622d94a1f8118"
                "c0976a03d2f18f680bfff877c9a965db9eedc51bc0be87c",
                "password",
            )
            log.info(LOGMSG_WAR_SEC_LOGIN_FAILED.format(public_key))
            return None
        elif self.check_public_key_signature(signature, user.public_key, hash):
            log.info('AUTHENTICATED WALLET: {}'.format(user.public_key))
            self.update_user_auth_stat(user, True)
            return user
        else:
            self.update_user_auth_stat(user, False)
            log.info(LOGMSG_WAR_SEC_LOGIN_FAILED.format(public_key))
            return None
