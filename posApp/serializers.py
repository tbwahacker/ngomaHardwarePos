from rest_framework import serializers
from .models import Products, Category, salesItems, Customer, Sales, PaymentMethod, StockMovement
from .views import User


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'status', 'date_added', 'date_updated']

class ProductSerializer(serializers.ModelSerializer):
    category_id = CategorySerializer()

    class Meta:
        model = Products
        fields = ['id', 'code', 'category_id', 'name', 'description', 'buying_price',
                  'price', 'status', 'quantity', 'units', 'minimum_quantity',
                  'date_added', 'date_updated', 'user']

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'code']

class SalesItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_id.name', read_only=True)

    class Meta:
        model = salesItems
        fields = ['id', 'product_id', 'product_name', 'qty', 'price', 'tendered_price', 'change', 'total', 'total_tendered_price']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'address', 'phone']

class SalesSerializer(serializers.ModelSerializer):
    # items = SalesItemsSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)

    # payment_method = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.all())
    # user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Sales
        fields = [
            'id', 'code', 'sub_total', 'tax', 'tax_amount', 'grand_total',
            'tendered_total', 'tendered_amount', 'amount_change', 'advance_amount',
            'customer', 'loan_status', 'status', 'date_added', 'date_updated'
        ]

    # class Meta:
    #     model = Sales
    #     fields = ['id', 'customer', 'user', 'status', 'payment_method', 'tendered_total', 'items', 'date_added', 'date_updated']

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'