from django.contrib import admin
from posApp.models import Category, Products, Sales, salesItems, PaymentMethod, StockMovement, CustomerSalesHistory, \
    SupplierPurchasesHistory, StockMovementHistory, Purchases, purchasesItems

# Register your models here.
admin.site.register(Category)
admin.site.register(Products)
admin.site.register(Sales)
admin.site.register(salesItems)
admin.site.register(Purchases)
admin.site.register(purchasesItems)
admin.site.register(PaymentMethod)
admin.site.register(StockMovement)
admin.site.register(StockMovementHistory)
admin.site.register(CustomerSalesHistory)
admin.site.register(SupplierPurchasesHistory)
# admin.site.register(Employees)
