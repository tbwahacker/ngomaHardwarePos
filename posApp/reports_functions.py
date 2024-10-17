from django.db.models import Sum
from django.utils import timezone

from posApp.models import purchasesItems, salesItems, StockMovementHistory


# def update_stock_movement(product, date=None):
#     if date is None:
#         date = timezone.now().date()
#
#     print(f"reached: {product} , {date}")
#
#     # Get the purchase and sales data for the given product and date
#     purchased_items = purchasesItems.objects.filter(
#         product_id=product, date_added__date=date
#     ).aggregate(total_purchased=Sum('qty'))
#
#     sold_items = salesItems.objects.filter(
#         product_id=product, date_added__date=date
#     ).aggregate(total_sold=Sum('qty'))
#
#     # Calculate the total quantities for the day
#     total_purchased = purchased_items['total_purchased'] or 0
#     total_sold = sold_items['total_sold'] or 0
#
#     # Get or create the StockMovementHistory entry for this product and date
#     stock_movement, created = StockMovementHistory.objects.get_or_create(
#         product=product,
#         date=date,
#         defaults={'initial_stock': product.quantity}  # Initial stock only used for the first day
#     )
#
#     # If stock movement already exists, update quantities
#     if not created:
#         stock_movement.purchased_quantity = total_purchased
#         stock_movement.sold_quantity = total_sold
#     else:
#         stock_movement.purchased_quantity = total_purchased
#         stock_movement.sold_quantity = total_sold
#
#     # Save the updated stock movement (balance calculation will be handled in the save method)
#     stock_movement.save()
#     return stock_movement
