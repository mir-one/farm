# -*- coding: utf-8 -*-
from farm.databases import CRUDMixin
from farm.databases import set_uuid
from farm.farm_flask.extensions import db
from farm.farm_flask.extensions import ma


class Math(CRUDMixin, db.Model):
    __tablename__ = "math"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, unique=True, primary_key=True)
    unique_id = db.Column(db.String, nullable=False, unique=True, default=set_uuid)
    name = db.Column(db.Text, default='Input Name')
    math_type = db.Column(db.Text, default=None)
    is_activated = db.Column(db.Boolean, default=False)
    log_level_debug = db.Column(db.Boolean, default=False)
    period = db.Column(db.Float, default=15.0)  # Duration between readings
    start_offset = db.Column(db.Float, default=10.0)
    max_measure_age = db.Column(db.Integer, default=60)

    # Backup options
    order_of_use = db.Column(db.Text, default='')

    # Difference options
    difference_reverse_order = db.Column(db.Boolean, default=False)  # False: var1 - var2 or True: var2 - var1
    difference_absolute = db.Column(db.Boolean, default=False)

    # Equation
    equation_input = db.Column(db.Text, default='')
    equation = db.Column(db.Text, default='x*1')

    # Verification options
    max_difference = db.Column(db.Float, default=10.0)  # Maximum difference between any measurements

    # Multi-input options
    inputs = db.Column(db.Text, default='')

    # Humidity calculation
    dry_bulb_t_id = db.Column(db.Text, default=None)
    dry_bulb_t_measure_id = db.Column(db.Text, default=None)
    wet_bulb_t_id = db.Column(db.Text, default=None)
    wet_bulb_t_measure_id = db.Column(db.Text, default=None)
    pressure_pa_id = db.Column(db.Text, default=None)
    pressure_pa_measure_id = db.Column(db.Text, default=None)

    # Misc IDs
    unique_id_1 = db.Column(db.Text, default=None)
    unique_measurement_id_1 = db.Column(db.Text, default=None)
    unique_id_2 = db.Column(db.Text, default=None)
    unique_measurement_id_2 = db.Column(db.Text, default=None)

    def is_active(self):
        """
        :return: Whether the sensor is currently activated
        :rtype: bool
        """
        return self.is_activated

    def __repr__(self):
        return "<{cls}(id={s.id})>".format(s=self, cls=self.__class__.__name__)


class MathSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Math
