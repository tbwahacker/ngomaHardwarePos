from celery import shared_task
from django.db.models import Sum
from .models import StockMovementHistory, purchasesItems, salesItems, Purchases, Sales, Products


# @shared_task
def update_stock_movement(product_id, date=None):
    from django.utils import timezone
    print("here")
    date = date or timezone.now().date()

    # Calculate purchased and sold quantities
    purchase_items = purchasesItems.objects.filter(
        product_id=product_id, purchase_id__date_added__date=date
    )
    purchased_quantity = purchase_items.aggregate(Sum('qty'))['qty__sum'] or 0

    sale_items = salesItems.objects.filter(
        product_id=product_id, sale_id__date_added__date=date
    )
    sold_quantity = sale_items.aggregate(Sum('qty'))['qty__sum'] or 0

    # Find previous day's stock movement if it exists
    previous_entry = StockMovementHistory.objects.filter(
        product_id=product_id, date__lt=date
    ).order_by('-date').first()

    if previous_entry:
        initial_stock = previous_entry.initial_stock
        balance = previous_entry.balance + purchased_quantity - sold_quantity
    else:
        # Set initial stock for the first stock movement
        product = Products.objects.get(id=product_id)
        initial_stock = product.quantity
        balance = initial_stock + purchased_quantity - sold_quantity

    # Get purchase and sale entries for the day
    purchases = Purchases.objects.filter(purchasesitems__in=purchase_items)
    sales = Sales.objects.filter(salesitems__in=sale_items)

    # Create or update the StockMovementHistory entry
    stock_movement, created = StockMovementHistory.objects.update_or_create(
        product_id=product_id, date=date,
        defaults={
            'initial_stock': initial_stock,
            'purchased_quantity': purchased_quantity,
            'sold_quantity': sold_quantity,
            'balance': balance
        }
    )

    # Attach the purchases and sales to the StockMovementHistory
    stock_movement.purchases.set(purchases)
    stock_movement.sales.set(sales)
    stock_movement.save()


def update_stock_movement_on_unapprove(item, which=None):
    # Get the StockMovementHistory record for the product and date
    stock_movement = StockMovementHistory.objects.filter(
        product_id=item.product_id.id,
        date=item.purchase_id.date_added if which == 1 else item.sale_id.date_added
    ).first()

    if stock_movement:
        # Subtract the quantity from the purchased_quantity
        stock_movement.purchased_quantity -= item.qty
        stock_movement.save()
        # Update the balance
        stock_movement.balance = stock_movement.initial_stock + stock_movement.purchased_quantity - stock_movement.sold_quantity
        stock_movement.save()
