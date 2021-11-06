# coding=utf-8
""" A collection of model factories using factory boy """
import factory  # factory boy
from farm.farm_flask.extensions import db
from farm.databases import models
from faker import Faker


faker = Faker()


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """ A factory for creating user models """
    class Meta(object):
        model = models.User
        sqlalchemy_session = db.session

    name = faker.name()
    email = faker.email()
