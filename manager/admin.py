from django.contrib import admin

# Register your models here.
from manager.dbmodels.vetti import Vetti


@admin.register(Vetti)
class VettiAdmin(admin.ModelAdmin):
    list_display = ('vetti_id', 'name', 'mac_display', 'ip_addr', 'armed', 'updated', 'enabled')
