from flask import g, request, flash, redirect, session, Markup, send_from_directory
from flask_appbuilder import ModelView, CompactCRUDMixin, MasterDetailView
from flask_appbuilder.views import expose
from flask_appbuilder.models.sqla.filters import FilterEqualFunction
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.views import UserDBModelView
from flask_appbuilder.security.registerviews import BaseRegisterUser
from flask_babel import lazy_gettext
from flask_appbuilder.filemanager import FileManager, uuid_namegen
from flask_appbuilder.upload import FileUploadField
from flask_appbuilder.actions import action
from sqlalchemy import create_engine
from . import appbuilder, db
import json
from flask_appbuilder._compat import as_unicode
from app.models import CollectionLayers, LayerFiles, LayerImages, LaunchableCollection
from .PinataPy import PinataFileUploadField, PinataFileManager
from flask_appbuilder.models.sqla.filters import FilterInFunction
from flask_appbuilder import ModelRestApi, BaseView, has_access, expose
import os

def get_user_id():
    return g.user.id

def wallet_level_security():
    model = 'LaunchableCollection'
    if model == 'LaunchableCollection':
        try:
            wallet_collections = appbuilder.session.query(LaunchableCollection.created_by_fk) \
                                           .filter(LaunchableCollection.created_by_fk == get_user_id())
            appbuilder.session.close()
            return wallet_collections
        except Exception as e:
            print(e)
            return None
    elif model == 'CollectionLayers':
        try:
            wallet_collections = appbuilder.session.query(CollectionLayers.created_by_fk) \
                                           .filter(CollectionLayers.created_by_fk == get_user_id())
            appbuilder.session.close()
            return wallet_collections
        except Exception as e:
            print(e)
            return None

def get_collection(id):
    try:
        collection = appbuilder.session.query(LaunchableCollection.collection_name, CollectionLayers.layer_name) \
                                       .filter(LaunchableCollection.id == id) \
                                       .all()
        appbuilder.session.close()
        return collection
    except Exception as e:
        print(e)
        return None

class RegisterWalletView(BaseRegisterUser):
    route_base = "/register-wallet"

    @expose("/activation/<string:activation_hash>")
    def activation(self, activation_hash):
        """
            Endpoint to expose an activation url, this url
            is sent to the user by email, when accessed the user is inserted
            and activated
        """
        reg =   self.appbuilder.sm.find_register_user(activation_hash)
        if not reg:
            log.error(c.LOGMSG_ERR_SEC_NO_REGISTER_HASH.format(activation_hash))
            flash(as_unicode(self.false_error_message), "danger")
            return redirect(self.appbuilder.get_url_for_index)
        if not self.appbuilder.sm.add_wallet(
            username=reg.username,
            public_key=reg.public_key,
            #nonce=reg.nonce,
            role=self.appbuilder.sm.find_role(
                self.appbuilder.sm.auth_user_registration_role
            ),
            #hashed_password=reg.password,
        ):
            flash(as_unicode(self.error_message), "danger")
            return redirect(self.appbuilder.get_url_for_index)
        else:
            self.appbuilder.sm.del_register_user(reg)
            return self.render_template(
                self.activation_template,
                username=reg.username,
                public_key=reg.public_key,
                #nonce=reg.nonce,
                appbuilder=self.appbuilder,
            )

    def register_post_api(self, data):
        register_wallet = self.appbuilder.sm.add_wallet_registration(
            username=data['username'],
            public_key=data['public_key']
        )
        return register_wallet

    @expose("/wallet", methods=["POST"])
    def this_form_post(self):
        data = json.loads(request.data)
        response = self.register_post_api(data)
        if response:
            return json.dumps({'success':'registered user'}), 200
        else:
            return json.dumps({'error':'register api error'}), 200

class LayerFilesModelView(ModelView):
    show_template = 'show.html'
    list_template = 'list.html'
    add_template = 'add.html'
    edit_template = 'edit.html'

    datamodel = SQLAInterface(LayerFiles)

    label_columns = {"download": "Download"}
    add_columns = ["layer", "description"]
    edit_columns = ["layer","description"]
    list_columns = ["layer","download"]
    show_columns = ["layer","download"]


class LayerImagesModelView(ModelView):
    show_template = 'show.html'
    list_template = 'list.html'
    add_template = 'add.html'
    edit_template = 'edit.html'

    datamodel = SQLAInterface(LayerImages)

    list_title = "List Layer Images"
    show_title = "Show Layer Images"
    add_title = "Add Layer Image"
    edit_title = "Edit Layer Image"

    edit_form_extra_fields = add_form_extra_fields = {
          "image": PinataFileUploadField("Upload Image",
                                        description="",
                                        filemanager=PinataFileManager,
                )
            }

    label_columns = {
        "photo_img": "Render IPFS",
        "photo_img_thumbnail": "Render IPFS",
    }
    list_columns = [
        "photo_img_thumbnail",
        "description"
    ]
    show_fieldsets = [
        (
            "Layer Images",
            {
                "fields": [
                    "photo_img",
                    "image",
                    "description",
                    "layer",
                ],
                "expanded": True,
            },
        )
    ]
    add_fieldsets = [
        (
            "Layer Images",
            {
                "fields": [
                    "image",
                    "description",
                    "layer"
                ],
                "expanded": True,
            },
        )
    ]

    @action("muldelete", "Delete", "Delete all Really?", "fa-rocket")
    def muldelete(self, items):
        if isinstance(items, list):
            self.datamodel.delete_all(items)
            self.update_redirect()
        else:
            self.datamodel.delete(items)
        return redirect(self.get_redirect())

class CollectionLayersMasterDetailView(MasterDetailView):
    show_template = 'show.html'
    list_template = 'left_master_detail.html'
    add_template = 'add.html'
    edit_template = 'edit.html'

    datamodel = SQLAInterface(CollectionLayers)
    related_views = [LayerImagesModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]
    #related_views = [LayerFilesModelView, LayerImagesModelView]

    show_template = "appbuilder/general/model/show_cascade.html"
    edit_template = "appbuilder/general/model/edit_cascade.html"

    list_title = "List All Layers"
    show_title = "Show Layer"
    add_title = "Add Layer"
    edit_title = "Edit Layer"

    #list_widget = ListThumbnail

    label_columns = {
        "collection_name": "Collection",
        "layer_img": "Layer",
        "layer_img_thumbnail": "Layer",
    }

    list_columns = [
        "layer_name"
    ]

    show_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "layer_name",
                    "layer_description",
                    "layer_order",
                    "download"
                ],
                "expanded": True,
            },
        )
    ]

    add_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "layer_name",
                    "layer_description",
                    "layer_order"
                ],
                "expanded": True,
            },
        )
    ]
    edit_columns = ["layer_name","layer_description"]

    @action("muldelete", "Delete", "Delete all Really?", "fa-rocket")
    def muldelete(self, items):
        if isinstance(items, list):
            self.datamodel.delete_all(items)
            self.update_redirect()
        else:
            self.datamodel.delete(items)
        return redirect(self.get_redirect())

class CollectionLayersModelView(ModelView):
    show_template = 'show.html'
    list_template = 'list.html'
    add_template = 'add.html'
    edit_template = 'edit.html'

    datamodel = SQLAInterface(CollectionLayers)
    related_views = [LayerImagesModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]
    #related_views = [LayerFilesModelView, LayerImagesModelView]

    show_template = "appbuilder/general/model/show_cascade.html"
    edit_template = "appbuilder/general/model/edit_cascade.html"

    list_title = "List All Layers"
    show_title = "Show Layer"
    add_title = "Add Layer"
    edit_title = "Edit Layer"

    #list_widget = ListThumbnail

    label_columns = {
        "collection_name": "Collection",
        "layer_img": "Layer",
        "layer_img_thumbnail": "Layer",
    }

    list_columns = [
        "layer_name"
    ]

    show_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "layer_name",
                    "layer_description",
                    "layer_order"
                ],
                "expanded": True,
            },
        )
    ]

    add_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "layer_name",
                    "layer_description",
                    "layer_order"
                ],
                "expanded": True,
            },
        )
    ]
    edit_columns = ["layer_name","layer_description"]

    @action("muldelete", "Delete", "Delete all Really?", "fa-rocket")
    def muldelete(self, items):
        if isinstance(items, list):
            self.datamodel.delete_all(items)
            self.update_redirect()
        else:
            self.datamodel.delete(items)
        return redirect(self.get_redirect())

class LaunchableCollectionMasterDetailView(MasterDetailView):
    show_template = 'show.html'
    list_template = 'list.html'
    add_template = 'add.html'
    edit_template = 'edit.html'

    datamodel = SQLAInterface(LaunchableCollection)
    related_views = [CollectionLayersModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]

    def launch_pad(self, item):
        collection = get_collection(item)
        return True
    #related_views = [CollectionLayersModelView]

    #show_template = "appbuilder/general/model/show_cascade.html"
    #edit_template = "appbuilder/general/model/edit_cascade.html"
    list_columns = [
        "collection_name"
    ]
    show_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "collection_name",
                    "collection_description",
                    "collection_type",
                    "launchable_collection_layers"
                ],
                "expanded": True,
            },
        )
    ]

    add_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "collection_name",
                    "collection_description",
                    "collection_type",
                    "launchable_collection_layers"
                ],
                "expanded": True,
            },
        )
    ]
    edit_columns = ["collection_name","collection_description","collection_type","launchable_collection_layers"]

    @action("launch", "Launch", "Launch collection(s)? There's no going back.", "fa-rocket")
    def launch(self, items):
        if isinstance(items, list):
            for item in items:
                self.launch_pad(item.id)
            self.update_redirect()
        else:
            self.launch_pad(items)
        return redirect(self.get_redirect())

class LaunchableCollectionModelView(ModelView):
    show_template = 'show.html'
    list_template = 'list.html'
    add_template = 'add.html'
    edit_template = 'edit.html'

    datamodel = SQLAInterface(LaunchableCollection)
    related_views = [CollectionLayersModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]

    def launch_pad(self, item):
        collection = get_collection(item)
        return True

    list_columns = [
        "collection_name"
    ]

    show_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "collection_name",
                    "collection_description",
                    "collection_type",
                    "launchable_collection_layers"
                ],
                "expanded": True,
            },
        )
    ]

    add_fieldsets = [
        (
            "Layer Details",
            {
                "fields": [
                    "collection_name",
                    "collection_description",
                    "collection_type",
                    "launchable_collection_layers"
                ],
                "expanded": True,
            },
        )
    ]
    edit_columns = ["collection_name","collection_description","collection_type","launchable_collection_layers"]

    @action("launch", "Launch", "Launch collection(s)? There's no going back.", "fa-rocket")
    def launch(self, items):
        if isinstance(items, list):
            for item in items:
                self.launch_pad(item.id)
            self.update_redirect()
        else:
            self.launch_pad(items)
        return redirect(self.get_redirect())

class Web3ConnectView(BaseView):

    @expose('/web3/<string:param1>')
    def web3_connect(self, param1):
        self.update_redirect()
        return self.render_template('web3.html', param1=param1)

appbuilder.add_view_no_menu(Web3ConnectView)

appbuilder.add_view(
    LaunchableCollectionModelView, "Launchable Collections", category_icon='fa-bars', icon="fa-bars", category="Collections"
)

appbuilder.add_view(
    CollectionLayersModelView, "NFT Layers", category_icon='fa-bars', icon="fa-bars", category="Collections"
)

appbuilder.add_view(
    CollectionLayersMasterDetailView, "Add Layer Images", category_icon='fa-bars', icon="fa-bars", category="Collections"
)

appbuilder.add_view_no_menu(RegisterWalletView)
appbuilder.add_view_no_menu(LayerFilesModelView)
appbuilder.add_view_no_menu(LayerImagesModelView)
