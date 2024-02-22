from django.contrib import admin
from .models import Event, Member, Expense, UserPreferences, Transaction

# Register your models here.
   
admin.site.register(Event)
admin.site.register(Member)
admin.site.register(Expense)
admin.site.register(UserPreferences)
admin.site.register(Transaction)