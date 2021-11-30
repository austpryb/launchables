from flask import g, request, flash, redirect, session, Markup, send_from_directory, make_response, send_file
from flask_appbuilder import ModelView, CompactCRUDMixin, MasterDetailView
from flask_appbuilder.views import expose
from flask_appbuilder.models.sqla.filters import FilterEqualFunction, FilterInFunction
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.views import UserDBModelView
from flask_appbuilder.security.registerviews import BaseRegisterUser
from flask_babel import lazy_gettext
from flask_appbuilder.filemanager import FileManager, uuid_namegen
from flask_appbuilder.upload import FileUploadField
from flask_appbuilder.actions import action
from flask_appbuilder import ModelRestApi, BaseView, has_access, expose
from flask_appbuilder._compat import as_unicode
from flask_appbuilder.widgets import ListWidget
from flask_appbuilder.urltools import get_filter_args
from sqlalchemy import create_engine
from . import appbuilder, db
from app.models import CollectionLayers, LayerFiles, LayerImages, LaunchableCollection, assoc_launchable_collection_layers
from .PinataPy import PinataFileUploadField, PinataFileManager, PinataPy
from .widgets import Web3FormWidget, Web3ListWidget, Web3ShowWidget
from datetime import datetime
from io import BytesIO
from brownie import *
from dotenv import load_dotenv
import pandas as pd
import xlsxwriter
import json
import os
from PIL import Image
import random
import logging
import time
from web3 import Web3
import requests

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

developer_wallet=os.environ.get('WALLET')
pinata_api_key = os.environ.get('PINATA_API_KEY')
pinata_secret_api_key = os.environ.get('PINATA_API_SECRET')
project_id = os.environ.get('IPFS_PROJECT_ID')
project_secret = os.environ.get('IPFS_PROJECT_SECRET')
factory_override = os.environ.get('FACTORY_OVERRIDE') #factory, stats, fund-launch, fund, launch, payload

OPENSEA_FORMAT = "https://testnets.opensea.io/assets/{}/{}"
NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["hardhat", "development", "ganache"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS + [
    "mainnet-fork",
    "binance-fork",
    "matic-fork",
]

DECIMALS = 18
INITIAL_VALUE = Web3.toWei(2000, "ether")

if os.environ.get('DEPLOYMENT') == 'local':
    os.chdir(r'brownie/')
else:
    os.chdir(r'/usr/src/app/brownie/')

network.connect('rinkeby')
project = project.load(r'.')
project.load_config()

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
        payload = {}
        collection = appbuilder.session.query(CollectionLayers.id, LaunchableCollection.collection_name, CollectionLayers.layer_name, CollectionLayers.layer_order) \
                                       .join(LaunchableCollection) \
                                       .filter(LaunchableCollection.id == id) \
                                       .order_by(CollectionLayers.layer_order) \
                                       .all()
        collection_len = len(collection)
        payload['collection_name'] = list(set([x.collection_name for x in collection]))[0]
        collection_layer_ids = set([x.id for x in collection])
        print('Collection has {} layers to process'.format(collection_len))
        for i in collection:
            images = [x.image for x in appbuilder.session.query(LayerImages.image) \
                                                         .filter(LayerImages.layer_id.in_([i.id]))]
            payload[i.layer_order] = images
        appbuilder.session.close()
        return payload
    except Exception as e:
        print(e)
        return None

def get_account(index=None, id=None):
    if index:
        return accounts[index]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        return accounts[0]
    if id:
        return accounts.load(id)
    return accounts.add(config["wallets"]["from_key"])

def get_contract(contract_name):
    """If you want to use this function, go to the brownie config and add a new entry for
    the contract that you want to be able to 'get'. Then add an entry in the in the variable 'contract_to_mock'.
    You'll see examples like the 'link_token'.
        This script will then either:
            - Get a address from the config
            - Or deploy a mock to use for a network that doesn't have it
        Args:
            contract_name (string): This is the name that is refered to in the
            brownie config and 'contract_to_mock' variable.
        Returns:
            brownie.network.contract.ProjectContract: The most recently deployed
            Contract of the type specificed by the dictonary. This could be either
            a mock or the 'real' contract on a live network.
    """
    contract_to_mock = {
        "link_token": project.LinkToken
    }
    contract_type = contract_to_mock[contract_name]
    if network.show_active() in NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        if len(contract_type) <= 0:
            deploy_mocks()
        contract = contract_type[-1]
    else:
        try:
            contract_address = config["networks"][network.show_active()][contract_name]
            contract = Contract.from_abi(
                contract_type._name, contract_address, contract_type.abi
            )
        except KeyError:
            print(
                f"{network.show_active()} address not found, perhaps you should add it to the config or deploy mocks?"
            )
            print(
                f"brownie run scripts/deploy_mocks.py --network {network.show_active()}"
            )
    return contract

def fund_with_link(
    contract_address, account=None, link_token=None, amount=1000000000000000000
):
    account = account if account else get_account()
    link_token = link_token if link_token else get_contract("link_token")
    tx = link_token.transfer(contract_address, amount, {"from": account})
    print("Funded {}".format(contract_address))
    return tx


def deploy_factory(payload):
    #try:
        proxy_registry_address = developer_wallet
        account = accounts.add(config['wallets']['from_key'])
        if factory_override == 'factory':
            launchable = project.LaunchCollectible.deploy(
                proxy_registry_address,
                {"from": account},
                publish_source=True
            )
            factory = project.Factory.deploy(
                proxy_registry_address,
                launchable.address,
                config["networks"][network.show_active()]["vrf_coordinator"],
                config["networks"][network.show_active()]["link_token"],
                config["networks"][network.show_active()]["keyhash"],
                {"from": account},
                publish_source=True,
            )
            fund_factory = fund_with_link(account=account, contract_address=factory.address)
            return factory.address, launchable.address
        elif factory_override == 'payload':
            nft_images = map_layers_from_index(layers=get_layers(payload), nft_request=nft_request(randomness=get_randomness_dev()))
            logging.info('NFT Images:')
            logging.info(nft_images)
            nft = process_mapped_image(nft_images)
            logging.info('NFT:')
            logging.info(nft)
            image = assemble_layers(nft)
            logging.info('Combined Image:')
            logging.info(image)
            return True, True
        elif factory_override == 'fund-launch':
            factory = project.Factory[len(project.Factory) - 1] #0x88933d0D5aA80855E0cB1Aa12A36924891a754B4
            fund_factory = fund_with_link(wallet=account, contract_address=factory.address)
            transaction = factory.requestLaunchable("CLINK", {"from": account})
            transaction.wait(1)
            time.sleep(35)
            print(transaction.events)
            requestId = transaction.events["RandomnessRequest"]["requestID"]
            tokenId = factory.requestToTokenId(requestId)
            return requestId, tokenId
        elif factory_override == 'fund':
            factory = project.Factory[len(project.Factory) - 1]
            fund_factory = fund_with_link(account=account, contract_address=factory.address)
            return True, True
        elif factory_override == 'launch':
            factory = project.Factory[len(project.Factory) - 1]
            logging.info(factory.address)
            transaction = factory.requestLaunchable("HACK2", {"from": account})
            transaction.wait(1)
            time.sleep(30)
            requestId = transaction.events["RandomnessRequest"]["requestID"]
            token_id = factory.requestToTokenId(requestId)
            return requestId, token_id
        elif factory_override == 'stats':
            factory = project.Factory[len(project.Factory) - 1]
            logging.info(factory.address)
            count = factory.getNumberOfLaunchables()
            logging.info(count)
            overview = factory.getLaunchableStats(count)
            logging.info(overview)
            return factory.address, overview
    #except Exception as e:
    #    logging.error(e)
    #    return str(e), None

def mint(factory_address, launchable_address):
    try:
        return True
    except Exception as e:
        logging.error(e)
        return str(e)

def map_layers_from_index(layers, nft_request):
    print('mapping layers')
    print(layers)
    print('to nft request')
    print(nft_request)
    mapped_layers = {}
    for layer in layers.keys():
        if layers[layer]:
            mapped_layers[layer] = layers[layer][nft_request[layer]]
    return mapped_layers

def process_mapped_image(nft_images):
    nft = {}
    for layer in nft_images.keys():
        if nft_images[layer]:
            response = requests.get(nft_images[layer])
            nft[layer] = Image.open(BytesIO(response.content))
    return nft

def assemble_images(nft):
    for i in nft.values():
        yield i

def get_randomness_dev():
    randomness = {
            'layer1':random.randint(0, 2),
            'layer2':random.randint(0, 2),
            'layer3':random.randint(0, 2),
            'layer4':None,
            'layer5':None,
            'layer6':None,
            'layer7':None
            }
    logging.info('Randomness:')
    logging.info(randomness)
    return randomness

def nft_request(randomness): # gets list of files from directory passed in
    request = {
            'layer1':randomness['layer1'],
            'layer2':randomness['layer2'],
            'layer3':randomness['layer3'],
            'layer4':randomness['layer4'],
            'layer5':randomness['layer5'],
            'layer6':randomness['layer6'],
            'layer7':randomness['layer7']
            }
    logging.info('Random Request:')
    logging.info(request)
    return request

def get_layers(payload): # gets list of files from directory passed in
    layers = {}
    for i in payload.keys():
        if isinstance(i, int):
            layers['layer'+str(i)] = payload[i]

    def get_layer(layers, key):
        key = layers.get(key)
        return key

    layers = {
            'layer1':get_layer(layers, 'layer1'),
            'layer2':get_layer(layers, 'layer2'),
            'layer3':get_layer(layers, 'layer3'),
            'layer4':get_layer(layers, 'layer4'),
            'layer5':get_layer(layers, 'layer5'),
            'layer6':get_layer(layers, 'layer6'),
            'layer7':get_layer(layers, 'layer7')
            }
    logging.info('Mapped Layers')
    logging.info(layers)
    return layers

def set_file(path):
    files = {
        'file': path
    }
    return files

def pin_to_pinata(metadata):
    ipfs = PinataPy(pinata_api_key=pinata_api_key, pinata_secret_api_key=pinata_secret_api_key)
    ipfs.pin_json_to_ipfs(json_to_pin=metadata)
    return ipfs

def pin_image_to_pinata(bytes):
    ipfs = PinataPy(pinata_api_key=pinata_api_key, pinata_secret_api_key=pinata_secret_api_key)
    ipfs = ipfs.pin_file_object_to_ipfs(bytes)
    return ipfs

def assemble_layers(nft):
    combined = nft['layer1'].paste(nft['layer2'], (0,0), nft['layer2'])
    combined = nft['layer1'].paste(nft['layer3'], (0,0), nft['layer3'])

    nft_name = 'HACK'
    nft_description = 'Chainlink Hackathon NFT'

    metadata = {
          "name": nft_name,
          "description": nft_description,
          "image": nft['layer1'],
          "attributes": []
        }

    img_byte_arr = BytesIO()
    nft['layer1'].save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    image_uri = 'https://gateway.pinata.cloud/ipfs/' + str(pin_image_to_pinata(img_byte_arr)['IpfsHash'])

    #ipfs = pin_to_pinata(metadata)
    return image_uri

class ListDownloadWidget(ListWidget):
    template = 'widgets/list_download.html'

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

    add_widget = Web3FormWidget
    list_widget = Web3ListWidget
    show_widget = Web3ShowWidget

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

    add_widget = Web3FormWidget
    list_widget = Web3ListWidget
    show_widget = Web3ShowWidget

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
    #show_template = 'show.html'
    #list_template = 'left_master_detail.html'
    #add_template = 'add.html'
    #edit_template = 'edit.html'

    #add_widget = Web3FormWidget
    #list_widget = Web3ListWidget
    #show_widget = Web3ShowWidget

    datamodel = SQLAInterface(CollectionLayers)
    related_views = [LayerImagesModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]

    #show_template = "appbuilder/general/model/show_cascade.html"
    #edit_template = "appbuilder/general/model/edit_cascade.html"

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

    add_widget = Web3FormWidget
    list_widget = Web3ListWidget
    show_widget = Web3ShowWidget

    datamodel = SQLAInterface(CollectionLayers)
    related_views = [LayerImagesModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]
    #related_views = [LayerFilesModelView, LayerImagesModelView]

    #show_template = "appbuilder/general/model/show_cascade.html"
    #edit_template = "appbuilder/general/model/edit_cascade.html"

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

    add_widget = Web3FormWidget
    list_widget = Web3ListWidget
    show_widget = Web3ShowWidget

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

    add_widget = Web3FormWidget
    list_widget = Web3ListWidget
    show_widget = Web3ShowWidget

    datamodel = SQLAInterface(LaunchableCollection)
    related_views = [CollectionLayersModelView]
    base_filters = [['created_by_fk', FilterInFunction, wallet_level_security]]

    def launch_pad(self, item):
        payload = get_collection(item)
        logging.info(item, payload)
        #factory_contract, launchable_contract = deploy_factory(payload)
        #logging.info(str(factory_contract) + ' | '  +  str(launchable_contract))
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
    list_widget = ListDownloadWidget

    @expose('/csv', methods=['GET'])
    def download_csv(self):
        output = BytesIO()
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        get_filter_args(self._filters)

        if not self.base_order:
            order_column, order_direction = '', ''
        else:
            order_column, order_direction = self.base_order
        count, lst = self.datamodel.query(self._filters, order_column, order_direction)
        excel = []
        scope = [] # scope = get a list of all user_id's using employer_id
        for i in self.datamodel.get_values(lst, self.list_columns):
            #if i.user_id in scope:
            excel.append(i)
        df = pd.DataFrame(excel)
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, 'data', index=False)
        writer.save()
        output.seek(0)
        return send_file(output, attachment_filename='{date_time}.xlsx'.format(date_time), as_attachment=True)

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
    LaunchableCollectionModelView, "Launch Collections", category_icon='fa-bars', icon="fa-file", category="Collections"
)

appbuilder.add_view(
    CollectionLayersModelView, "NFT Layers", category_icon='fa-bars', icon="fa-bars", category="Collections"
)

appbuilder.add_view(
    CollectionLayersMasterDetailView, "Add Images to Layer", category_icon='fa-bars', icon="fa-image", category="Collections"
)

appbuilder.add_view_no_menu(RegisterWalletView)
appbuilder.add_view_no_menu(LayerFilesModelView)
appbuilder.add_view_no_menu(LayerImagesModelView)
