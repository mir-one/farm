# coding=utf-8
from farm.databases import CRUDMixin
from farm.databases import set_uuid
from farm.farm_flask.extensions import db
from farm.farm_flask.extensions import ma


class CustomController(CRUDMixin, db.Model):
    __tablename__ = "custom_controller"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, unique=True, primary_key=True)
    unique_id = db.Column(db.String, nullable=False, unique=True, default=set_uuid)
    name = db.Column(db.Text, default='Custom Function')
    position_y = db.Column(db.Integer, default=0)
    device = db.Column(db.Text, default='')

    is_activated = db.Column(db.Boolean, default=False)
    log_level_debug = db.Column(db.Boolean, default=False)

    custom_options = db.Column(db.Text, default='')

    def is_active(self):
        """
        :return: Whether the sensor is currently activated
        :rtype: bool
        """
        return self.is_activated

    def __repr__(self):
        return "<{cls}(id={s.id})>".format(s=self, cls=self.__class__.__name__)


class FunctionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CustomController


class FunctionChannel(CRUDMixin, db.Model):
    __tablename__ = "function_channel"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, unique=True, primary_key=True)
    unique_id = db.Column(db.String, nullable=False, unique=True, default=set_uuid)
    function_id = db.Column(db.Text, default=None)
    channel = db.Column(db.Integer, default=None)
    name = db.Column(db.Text, default='')

    custom_options = db.Column(db.Text, default='')

    def __repr__(self):
        return "<{cls}(id={s.id})>".format(s=self, cls=self.__class__.__name__)


class FunctionChannelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FunctionChannel
