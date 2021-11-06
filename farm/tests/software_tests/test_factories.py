# coding=utf-8
""" make sure the fixtures are behaving as expected """
import pytest
from farm.tests.software_tests.factories import UserFactory
from farm.tests.software_tests.factories import RoleFactory


# (Factory, kwargs)
known_factories = [
    (UserFactory, {}),
    (RoleFactory, {}),
]


@pytest.mark.usefixtures('db')
def test_model_factories():
    """ create a user model using the model factory """
    for model_factory, config in known_factories:
        model = model_factory(**config).save()
        assert model
