import datetime
from flask_appbuilder.filemanager import ImageManager
from flask_appbuilder.models.mixins import ImageColumn
from flask import g, Markup, url_for
from flask_appbuilder import Model
from flask_appbuilder.models.mixins import ImageColumn, AuditMixin, FileColumn
from flask_appbuilder.security.sqla.models import User
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Boolean, Sequence, Table, UniqueConstraint, Enum
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, Query
from random import randint
from . import PinataPy
import json
from sqlalchemy.orm import sessionmaker
from flask_appbuilder.filemanager import get_file_original_name

mindate = datetime.date(datetime.MINYEAR, 1, 1)

def random_integer():
    min_ = 1000000
    max_ = 10000000000
    rand = randint(min_, max_)

    #from sqlalchemy.orm import sessionmaker
    #db_session_maker = sessionmaker(bind=your_db_engine)
    #db_session = db_session_maker()
    #while db_session.query(Table).filter(uuid == rand).limit(1).first() is not None:
    #    rand = randint(min_, max_)

    return rand

class WalletQuery(Query):

  def update_nonce(self, public_address):
    update_nonce = random_integer()
    return self.filter(Wallet.public_address == public_address).update({'nonce': update_nonce})

class Wallet(User):
    __tablename__ = "ab_user"

    query_class = WalletQuery
    username = Column('username', String(64), unique=True, nullable=False)
    nonce = Column('nonce', Integer, nullable=True, default=random_integer)
    public_key = Column('public_key', String(256), nullable=False, unique=True)

    def __repr__(self):
        return self.public_key

    def get_nonce(self, cls):
        return self.nonce

    def get_user_id(self, cls):
        try:
            return g.user.id
        except Exception:
            return None

class CollectionType(Model):
    __tablename__ = 'collection_type'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    collection_type = Column('collection_type', String(250))

    def __repr__(self):
        return self.collection_type

assoc_launchable_collection_layers = Table(
    "launchable_collection_layers",
    Model.metadata,
    Column('id', Integer, primary_key=True),
    Column('collection_layers_id', Integer, ForeignKey('collection_layers.id')),
    Column('launchable_collection_id', Integer, ForeignKey('launchable_collection.id'))
)

class LaunchableCollection(AuditMixin, Model):
    __tablename__ = 'launchable_collection'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    collection_id = Column('collection_id', String(250))
    collection_name = Column('collection_name', String(250))
    collection_description = Column('collection_description', String(250))

    collection_type_id = Column('collection_type_id', Integer, ForeignKey("collection_type.id"), nullable=True)
    collection_type = relationship('CollectionType')

    collection_layer_id = Column('collection_layer_id', Integer, ForeignKey("collection_layers.id"), nullable=True)
    collection_layer = relationship('CollectionLayers')

    launchable_collection_layers = relationship(
            "CollectionLayers", secondary=assoc_launchable_collection_layers, backref='launchable_collection',
    )

    def __repr__(self):
        return self.collection_name

class CollectionLayers(AuditMixin, Model):
    __tablename__ = 'collection_layers'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    layer_order = Column('layer_order', Integer)
    layer_name = Column('collection_name', String(250))
    layer_description = Column('collection_description', String(250))

    def __repr__(self):
        return self.layer_name

class LayerFiles(AuditMixin, Model):
    __tablename__ = "layer_files"

    id = Column('id', Integer, primary_key=True)
    file = Column('file', FileColumn, nullable=False)
    description = Column('description', String(150))

    layer_id = Column('layer_id', Integer, ForeignKey("collection_layers.id"))
    layer = relationship("CollectionLayers")

    def download(self):
        return Markup(
            '<a href="'
            + url_for("LayerFilesModelView.download", filename=str(self.file))
            + '">Download</a>'
        )

    def filename(self):
        return get_file_original_name(str(self.file))

class LayerImages(AuditMixin, Model):
    __tablename__ = "layer_images"

    id = Column('id', Integer, primary_key=True)
    image = Column('image', ImageColumn(size=(300, 300, True), thumbnail_size=(60, 60, True)))
    description = Column('description', String(150))

    layer_id = Column('layer_id', Integer, ForeignKey("collection_layers.id"))
    layer = relationship("CollectionLayers")

    def photo_img(self):
        im = PinataPy.PinataFileManager()
        if self.image:
            return Markup('<a href="' + url_for('LayerImagesModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="' + self.image +\
             '" alt="Photo" class="img-rounded img-responsive"></a>')
        else:
            return Markup('<a href="' + url_for('LayerImagesModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="' + self.image +\
             '" alt="Photo" class="img-responsive"></a>')

    def photo_img_thumbnail(self):
        im = PinataPy.PinataFileManager()

        if self.image:
            return Markup('<a href="' + url_for('LayerImagesModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="' + self.image +\
             '" alt="Photo" class="img-rounded img-responsive"></a>')
        else:
            return Markup('<a href="' + url_for('LayerImagesModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="' + self.image + '" alt="Photo" class="img-responsive"></a>')

    def __repr__(self):
        return self.layer

class ContractType(Model):
    __tablename__ = 'contract_type'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    contract_type = Column('contract_type', String(250))

    def __repr__(self):
        return self.contract_type

class Contracts(AuditMixin, Model):
    __tablename__ = 'contracts'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    contract = Column('contract', String(250))
    contract_name = Column('contract_name', String(250))
    status = Column('status', Enum('Not Launched', 'Launched', 'Launch in Progress'), nullable=False, default='Not Launched')

    contract_type_id = Column('contract_type_id', Integer, ForeignKey('contract_type.id'))
    contract_type = relationship('ContractType')

    def __repr__(self):
        return self.contract

class RegisterWallet(Model):
    __tablename__ = "ab_register"

    id = Column(Integer, Sequence("ab_register_user_id_seq"), primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password = Column(String(256))
    nonce = Column(Integer, nullable=True, default=random_integer, unique=True)
    public_key = Column(String(256), nullable=True, unique=True)
    registration_date = Column(DateTime, default=datetime.datetime.now, nullable=True)
    registration_hash = Column(String(256))
    registration_hash_url = Column(String(256))

    def __repr__(self):
        return self.public_key
