# coding=utf-8
from farm.farm_flask.extensions import db
from farm.databases import CRUDMixin
from farm import config


class AlembicVersion(CRUDMixin, db.Model):
    __tablename__ = "alembic_version"
    __table_args__ = {'extend_existing': True}

    version_num = db.Column(db.String(32), primary_key=True, nullable=False, default=config.ALEMBIC_VERSION)

    def __repr__(self):
        return "<{cls}(version_number={s.version_num})>".format(s=self, cls=self.__class__.__name__)
