import uuid
from django.db import models

from .base import *


class Vetti(Base):
    vetti_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=150)
    mac_addr = models.CharField(unique=True, max_length=30)
    ip_addr = models.CharField(blank=True, default='', max_length=100)
    armed = models.BooleanField(default=False, editable=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Vetti'
        verbose_name_plural = 'Vetti'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} <{self.mac_display}>'

    def save(self, *args, **kwargs):
        self.mac_addr = self.mac_addr.lower().replace("-", "").zfill(12)
        super(Vetti, self).save(*args, **kwargs)

    @property
    def mac_display(self):
        return ':'.join([self.mac_addr[i:i+2] for i in range(0, len(self.mac_addr), 2)])
