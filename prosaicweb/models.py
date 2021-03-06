#  prosaicweb
#  Copyright (C) 2016  nathaniel smith
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json
from functools import lru_cache

from flask_login import UserMixin
from prosaic.models import Base, Source, Corpus, Phrase, corpora_sources, Database
from sqlalchemy import create_engine, Column, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import ARRAY, TEXT, INTEGER, JSON
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

from .cfg import DB

def get_engine(db: Database) -> Engine:
    return create_engine('postgresql://{user}:{password}@{host}:{port}/{dbname}'\
           .format(**db))

Session = sessionmaker()
engine = get_engine(DB)
Session.configure(bind=engine)

def get_session(db: Database):
    Session.configure(bind=get_engine(db))
    return Session()

users_sources = Table('users_sources', Base.metadata,
                    Column('user_id', INTEGER, ForeignKey('users.id')),
                    Column('source_id', INTEGER, ForeignKey('sources.id')))

users_corpora = Table('users_corpora', Base.metadata,
                    Column('user_id', INTEGER, ForeignKey('users.id')),
                    Column('corpus_id', INTEGER, ForeignKey('corpora.id')))

users_templates = Table('users_templates', Base.metadata,
                    Column('user_id', INTEGER, ForeignKey('users.id')),
                    Column('template_id', INTEGER, ForeignKey('templates.id')))

class Template(Base):
    __tablename__ = 'templates'

    id = Column(INTEGER, primary_key=True)
    name = Column(TEXT, nullable=False)
    lines = Column(JSON, nullable=False)

    @property
    def json(self) -> str:
        return json.dumps(self.lines)

    @property
    def pretty(self) -> str:
        # TODO wtf
        output = ''
        for line in self.lines:
            output += json.dumps(line) + '\n'
        return output

    def __repr__(self) -> str:
        return "Template<'{}'>".format(self.lines)

class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(INTEGER, primary_key=True)
    pwhash = Column(TEXT, nullable=False)
    email = Column(TEXT, nullable=False, unique=True)

    # TODO check on table encoding, make sure it's utf-8
    sources = relationship('Source', secondary=users_sources)
    corpora = relationship('Corpus', secondary=users_corpora)
    templates = relationship('Template', secondary=users_templates)

    def get_id(self) -> str:
        return self.email

    def __repr__(self) -> str:
        return "User(email='{}', pwhash='{}')".format(
            self.email, self.pwhash
        )
