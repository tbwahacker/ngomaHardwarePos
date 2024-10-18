from datetime import datetime

from django.contrib.auth.models import User
from django.db.models import Sum
from unicodedata import category
from django.db import models
from django.utils import timezone


# Configuratiions


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    logo = models.BinaryField(blank=True, null=True)
    is_direct_pricing_method = models.BooleanField(default=False)
    configured = models.BooleanField(default=False)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class StoreLocations(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    code = models.CharField(max_length=100, blank=True, null=True)
    name = models.TextField(unique=True)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Units(models.Model):
    name = models.TextField()
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# Create user profile
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_language = models.CharField(max_length=40, choices=[('en', 'English'), ('sw', 'Swahili')], default='en')


# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    has_loan = models.BooleanField(default=False)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    has_loan = models.BooleanField(default=False)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.TextField()
    description = models.TextField()
    status = models.IntegerField(default=1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id}-{self.name}"


class Products(models.Model):
    code = models.CharField(max_length=1000000000)
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.TextField(unique=True)
    description = models.TextField()
    buying_price = models.FloatField(default=0)
    price = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    markup = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    left_pieces = models.IntegerField(default=0)
    max_pieces = models.IntegerField(default=1)
    total_pieces = models.IntegerField(default=0)
    units = models.ForeignKey(Units, on_delete=models.SET_NULL, null=True, blank=True)
    minimum_quantity = models.IntegerField(default=5)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        permissions = [
            ("view_fully_in_product", "Can view fully in product"),
        ]

    def __str__(self):
        return self.name


class Sales(models.Model):
    code = models.CharField(max_length=100000000)
    sub_total = models.FloatField(default=0)
    tendered_total = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    tax_amount = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    tendered_amount = models.FloatField(default=0)
    amount_change = models.FloatField(default=0)
    advance_amount = models.FloatField(default=0)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    phone_no = models.TextField(blank=True, null=True)
    status = models.IntegerField(default=0)  # 0=pending , 1= success , 2 = rejected
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True,
                                       blank=True)  # 0001=cash , 0002=due
    loan_status = models.IntegerField(default=0)  # 0=not loaned , 1=loan, 2=Completed Loan, 3. partial loan
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        permissions = [
            ("view_order_confirmation", "Can view order confirmation"),
            ("view_delete_order_button", "Can view delete sale button"),
        ]

    def __str__(self):
        return self.code


class salesItems(models.Model):
    sale_id = models.ForeignKey(Sales, related_name='salesitems', on_delete=models.CASCADE)
    product_id = models.ForeignKey(Products, on_delete=models.CASCADE)
    tendered_price = models.FloatField(default=0)
    change = models.FloatField(default=0)
    price = models.FloatField(default=0)
    qty = models.FloatField(default=0)
    pcs = models.IntegerField(default=0)
    total = models.FloatField(default=0)
    total_tendered_price = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("view_loan_repayment", "Can view loan repayment")
        ]


class DuePaymentHistory(models.Model):
    sale_id = models.ForeignKey(Sales, on_delete=models.CASCADE)
    initial_loan = models.FloatField(default=0)
    paid_amount = models.FloatField(default=0)
    total_paid_amount = models.FloatField(default=0)
    disbursed_amount = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class Purchases(models.Model):
    code = models.CharField(max_length=100000000)
    sub_total = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    buying_price_change = models.FloatField(default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.IntegerField(default=0)  # 0=pending , 1= success , 2 = rejected
    advance_amount = models.FloatField(default=0)
    tendered_amount = models.FloatField(default=0)
    car_number = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True,
                                       blank=True)  # 0001=cash , 0002=due
    loan_status = models.IntegerField(default=0)  # 0=not loaned , 1=loan, 2=Completed Loan, 3. partial loan
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        permissions = [
            ("view_purchase_confirmation", "Can view purchase confirmation"),
            ("view_delete_purchase_button", "Can view delete purchase button"),
        ]

    def __str__(self):
        return self.code


# Pruchases Model

class purchasesItems(models.Model):
    purchase_id = models.ForeignKey(Purchases, on_delete=models.CASCADE)
    product_id = models.ForeignKey(Products, on_delete=models.CASCADE)
    price = models.FloatField(default=0)
    qty = models.IntegerField(default=0)
    total = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)


class PurchasesDuePaymentHistory(models.Model):
    purchase_id = models.ForeignKey(Purchases, on_delete=models.CASCADE)
    initial_loan = models.FloatField(default=0)
    paid_amount = models.FloatField(default=0)
    total_paid_amount = models.FloatField(default=0)
    disbursed_amount = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class StockMovement(models.Model):
    product = models.ForeignKey(Products, on_delete=models.SET_NULL, blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.TextField()
    buying_price = models.FloatField(default=0)
    selling_price = models.FloatField(default=0)
    tendered_amount = models.FloatField(default=0)
    quantity_in_past = models.IntegerField(default=0)  # quantity before purchases
    quantity_in_stock = models.IntegerField(default=0)  # quantity in/after purchases
    quantity_purchased = models.IntegerField(default=0)  # zilizonunuliwa
    quantity_sold = models.IntegerField(default=0)  # zilizouzwa
    quantity_returned = models.IntegerField(default=0)  # after deletion
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.product.code + " - " + self.product.name


class CustomProforma(models.Model):
    code = models.CharField(max_length=100000000, default=0)
    sub_total = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class CustomProformaItems(models.Model):
    proforma_id = models.ForeignKey(CustomProforma, on_delete=models.CASCADE)
    product_id = models.ForeignKey(Products, on_delete=models.CASCADE)
    tendered_price = models.FloatField(default=0)
    price = models.FloatField(default=0)
    qty = models.IntegerField(default=0)
    total = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)


class CustomerSalesHistory(models.Model):
    code = models.CharField(max_length=1000000000)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    sale_id = models.ForeignKey(Sales, on_delete=models.CASCADE, null=True, blank=True)  # Loan
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True,
                                       blank=True)  # 0001=cash , 0002=due
    initial_loan_amount = models.FloatField(default=0)
    paid_amount = models.FloatField(default=0)
    total_paid_amount = models.FloatField(default=0)
    balance = models.FloatField(default=0)
    tendered_initial_loan_amount = models.FloatField(default=0)
    tendered_paid_amount = models.FloatField(default=0)
    tendered_total_paid_amount = models.FloatField(default=0)
    tendered_balance = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class SupplierPurchasesHistory(models.Model):
    code = models.CharField(max_length=1000000000)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)
    purchase_id = models.ForeignKey(Purchases, on_delete=models.CASCADE, null=True, blank=True)  # Loan
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    initial_loan_amount = models.FloatField(default=0)
    paid_amount = models.FloatField(default=0)
    total_paid_amount = models.FloatField(default=0)
    balance = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class StockMovementHistory(models.Model):
    product = models.ForeignKey('Products', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    initial_stock = models.IntegerField(default=0)
    initial_stock_pieces = models.IntegerField(default=0)

    purchases = models.ManyToManyField('Purchases', blank=True)
    sales = models.ManyToManyField('Sales', blank=True)

    purchased_quantity = models.IntegerField(default=0)
    sold_quantity = models.IntegerField(default=0)

    balance = models.IntegerField(default=0)
    balance_pieces = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} on {self.date}"


from django.db.models.signals import post_save
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .tasks import update_stock_movement


# Purchases
@receiver(post_save, sender=purchasesItems)
def update_stock_movement_on_purchase_added(sender, instance, **kwargs):
    print(instance.product_id.id)
    # update_stock_movement.delay(instance.product_id.id, instance.purchase_id.date_added.date())
    # update_stock_movement(instance.product_id.id, instance.purchase_id.date_added.date())


  # Sales
@receiver(post_save, sender=salesItems)
def update_stock_movement_on_sale_added(sender, instance, **kwargs):
    print(instance.product_id.id)
    print(instance.sale_id.date_added.date())
    # update_stock_movement.delay(instance.product_id.id, instance.sale_id.date_added.date())
    # update_stock_movement(instance.product_id.id, instance.sale_id.date_added.date())