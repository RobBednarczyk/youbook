from sqlalchemy import Column, String, Integer, create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

# modules for password hashing and sending/receiving tokens
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer)
from itsdangerous import BadSignature, SignatureExpired


Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(), nullable=False)
    email = Column(String())
    user_img = Column(String())
    password_hash = Column(String())

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    @property
    def serialize(self):
        """Return the object in an easily serializable format"""
        return {
            "user_id": self.id,
            "username": self.username,
            "image": self.user_img,
        }


class Bookshelf(Base):
    __tablename__ = "bookshelf"
    id = Column(Integer, primary_key=True)
    name = Column(String())
    user_id = Column(Integer, ForeignKey("user.id"))
    image_url = Column(String())
    user = relationship(User)

    @property
    def serialize(self):
        """Return the object in an easily serializable format"""
        return {
            "bookshelf_id": self.id,
            "bookshelf_name": self.name,
            "bookshelf_image": self.image_url,
        }


class Book(Base):
    __tablename__ = "book"
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    author = Column(String())
    image_url = Column(String())
    category = Column(String())
    description = Column(String())
    bookshelf_id = Column(Integer, ForeignKey("bookshelf.id"))
    bookshelf = relationship(Bookshelf)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship(User)

    @property
    def serialize(self):
        """Return the object in an easily serializable format"""
        return {
            "book_id": self.id,
            "title": self.title,
            "author": self.author,
            "category": self.category,
        }


engine = create_engine("sqlite:///bookshelvesWithUsers_v2.db")
Base.metadata.create_all(engine)
