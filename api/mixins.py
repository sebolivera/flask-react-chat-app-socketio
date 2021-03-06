"""
Not gonna lie to u chief, I forgot what this file was supposed to be about. I don't even plan on implementing authlib.
"""

from authlib.oauth1 import ClientMixin
import models
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, relationship


class Client(ClientMixin, models.User):
    id = Column(Integer, primary_key=True)
    client_id = Column(String(48), index=True)
    client_secret = Column(String(120), nullable=False)
    default_redirect_uri = Column(Text, nullable=False, default='')
    user_id = Column(
        Integer, ForeignKey('user.id', ondelete='CASCADE')
    )
    user = relationship('User')

    def get_default_redirect_uri(self):
        return self.default_redirect_uri

    def get_client_secret(self):
        return self.client_secret

    def get_rsa_public_key(self):
        return None
