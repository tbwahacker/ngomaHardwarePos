####################################### API ###################################
from django.contrib.auth import  login
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout

from posApp.views import User, generate_unique_code
from datetime import date, datetime


#### USER AUTH ###########

# class RegisterApi(APIView):
#     def post(self, request, *args, **kwargs):
#         if request.user.is_authenticated:
#             return Response({'error': 'You are already logged in'}, status=status.HTTP_400_BAD_REQUEST)
#
#         form = UserRegisterForm(request.data)
#         if form.is_valid():
#             user = form.save(commit=False)
#             full_name = form.cleaned_data.get('full_name')
#             phone = form.cleaned_data.get('phone')
#             email = form.cleaned_data.get('email')
#             password = form.cleaned_data.get('password1')
#
#             # Save the user
#             user.set_password(password)
#             user.save()
#
#             user = authenticate(email=email, password=password)
#             if user is not None:
#                 login(request, user)
#
#                 profile = Profile.objects.get(user=request.user)
#                 profile.full_name = full_name
#                 profile.phone = phone
#                 profile.save()
#
#                 # Generate JWT token
#                 refresh = RefreshToken.for_user(request.user)
#                 return Response({
#                     'success': 'Account created successfully',
#                     'username': request.user.username,
#                     'email': request.user.email,
#                     'refresh': str(refresh),
#                     'access': str(refresh.access_token),
#                 }, status=status.HTTP_201_CREATED)
#             else:
#                 return Response({'error': 'Authentication failed'}, status=status.HTTP_400_BAD_REQUEST)
#         else:
#             return Response({'error': 'Invalid form data', 'details': form.errors}, status=status.HTTP_400_BAD_REQUEST)


class LoginApi(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=username)
            # user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # If you prefer JWT tokens, replace the token generation part with:
                # Generate JWT token
                refresh = RefreshToken.for_user(user)
                return Response({
                    'success': 'You are logged in',
                    'username': user.username,
                    'email': user.email,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid username or password'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def LogoutApi(request):
    # Get the user's token and delete it
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
    except Token.DoesNotExist:
        return Response({'error': 'Token does not exist'}, status=status.HTTP_400_BAD_REQUEST)

    # Log the user out
    logout(request)
    return Response({'success': 'You have been logged out'}, status=status.HTTP_200_OK)


################ PRODUCTS ################
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Products, Sales, salesItems, Company, Customer, PaymentMethod, StockMovement, CustomerSalesHistory, \
    DuePaymentHistory
from .serializers import ProductSerializer, SalesSerializer, SalesItemsSerializer, CustomerSerializer, \
    PaymentMethodSerializer, StockMovementSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Require login
def products_api(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 150)

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 100  # Fallback to 100 if conversion fails

    if query:
        product_list = Products.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(code__icontains=query) |
            Q(category_id__name__icontains=query)
        ).order_by('-date_added')
    else:
        product_list = Products.objects.all().order_by('-date_added')

    paginator = PageNumberPagination()
    paginator.page_size = per_page
    paginated_products = paginator.paginate_queryset(product_list, request)

    serializer = ProductSerializer(paginated_products, many=True)

    # Calculate total price for all products
    total_price = sum(product.buying_price * product.quantity for product in product_list)

    return paginator.get_paginated_response({
        'products': serializer.data,
        'total_price': total_price
    })


############### SALES ########################

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure the user is authenticated
def pos_api(request):
    # Fetch active products, all customers, and payment methods
    products = Products.objects.filter(status=1).order_by('-date_added')
    customers = Customer.objects.all().order_by('-date_added')
    payment_methods = PaymentMethod.objects.all()

    # Serialize the data
    products_serializer = ProductSerializer(products, many=True)
    customers_serializer = CustomerSerializer(customers, many=True)
    payment_methods_serializer = PaymentMethodSerializer(payment_methods, many=True)

    # Prepare response data
    response_data = {
        'page_title': "Point of Sale",
        'products': products_serializer.data,
        'customers': customers_serializer.data,
        'payment_methods': payment_methods_serializer.data,
    }

    return Response(response_data)


class SavePosApi(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(permission_required('posApp.add_sales', raise_exception=True))
    # @method_decorator(permission_required('posApp.change_sales', raise_exception=True))
    def post(self, request):
        resp = {'status': 'failed', 'msg': ''}
        data = request.data
        company = Company.objects.filter(user=request.user).first()
        print(data)
        try:
            with transaction.atomic():
                sale_id = int(data.get('sale_id', 0))
                item_id = data.get('id', None)
                product_id = data.get('product_id', None)
                quantity = int(data.get('quantity', 0))
                selling_price = float(data.get('price', 0))

                # add single item
                if sale_id and sale_id > 0:
                    product = Products.objects.get(id=product_id)
                    quantity_in_past = product.quantity
                    sale = Sales.objects.filter(id=sale_id).first()
                    if sale:
                        if quantity > 0 and selling_price > 10:
                            if quantity <= product.quantity:
                                if selling_price >= product.price:
                                    sales_item = salesItems.objects.create(
                                        sale_id=sale,
                                        product_id=product,
                                        tendered_price=selling_price,
                                        change=selling_price - float(product.price),
                                        qty=quantity,
                                        price=product.price,
                                        total=product.price * quantity,
                                        total_tendered_price=selling_price * quantity
                                    )

                                    if sale.status == 1:
                                        product.quantity -= quantity
                                        product.save()

                                        StockMovement.objects.create(
                                            product=product,
                                            product_name=product.name,
                                            customer_id=sale.customer.pk,
                                            buying_price=product.buying_price,
                                            selling_price=product.price,
                                            tendered_amount=selling_price,
                                            quantity_in_past=quantity_in_past,
                                            quantity_in_stock=product.quantity,
                                            quantity_sold=quantity,
                                            user=request.user
                                        )

                                    new_grand_total = 0
                                    for i in salesItems.objects.filter(sale_id=sale):
                                        new_grand_total += i.total_tendered_price

                                    sale.tendered_amount = selling_price
                                    sale.tendered_total = new_grand_total
                                    sale.grand_total = new_grand_total
                                    sale.save()

                                    if sale.payment_method.code == '0001':
                                        CustomerSalesHistory.objects.filter(sale_id=sale).update(
                                            paid_amount=sale.grand_total,
                                            tendered_paid_amount=sale.tendered_total,
                                        )

                                    return Response({'status': 'success'}, status=status.HTTP_200_OK)
                                else:
                                    raise ValidationError('Selling price is below the minimum price.')
                            else:
                                raise ValidationError('Quantity exceeds stock.')
                        else:
                            raise ValidationError('Quantity and Price must be greater than zero.')

                # edit single item
                if item_id:
                    items = salesItems.objects
                    item = items.filter(id=item_id)
                    if item.exists():
                        reversed_qty = item.first().product_id.quantity + item.first().qty
                        if quantity > 0 and selling_price > 10:
                            if quantity <= item.first().product_id.quantity:
                                if selling_price >= item.first().product_id.price:
                                    item.update(
                                        qty=quantity,
                                        tendered_price=selling_price,
                                        price=selling_price,
                                        total_tendered_price=quantity * selling_price,
                                        total=quantity * selling_price
                                    )
                                    sale = Sales.objects.filter(id=item.first().sale_id.pk)

                                    if sale.first().status == 1:
                                        Products.objects.filter(id=item.first().product_id.pk).update(
                                            quantity=reversed_qty - quantity
                                        )

                                    new_grand_total = 0
                                    for i in items.filter(sale_id=sale.first()):
                                        new_grand_total += i.total_tendered_price

                                    sale.update(
                                        tendered_amount=selling_price,
                                        tendered_total=new_grand_total,
                                        grand_total=new_grand_total
                                    )

                                    return Response({'status': 'success'}, status=status.HTTP_200_OK)
                                else:
                                    raise ValidationError('Selling price is below the minimum price.')
                            else:
                                raise ValidationError('Quantity exceeds stock.')
                        else:
                            raise ValidationError('Quantity and Price must be greater than zero.')
                    else:
                        raise ValidationError('Item does not exist.')
        except Exception as e:
            return Response({'status': 'failed', 'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)



        # pos products add
        pref = str(datetime.now().year) + str(datetime.now().year)
        i = 1

        # Generate a unique sales code
        while True:
            code = '{:0>5}'.format(i)
            i += 1
            if not Sales.objects.filter(code=str(pref) + str(code)).exists():
                break
        code = str(pref) + str(code)

        try:
            with transaction.atomic():
                customer_id = data.get('customer_id')
                payment_method_code = data.get('payment_method_code')

                method = PaymentMethod.objects.filter(code=payment_method_code).first()

                if not method:
                    return Response({"msg": "Please select payment method."}, status=status.HTTP_400_BAD_REQUEST)

                if not customer_id and payment_method_code == '0002':
                    return Response({"msg": "Please select customer. Can't make a loan to someone you don't know"},
                                    status=status.HTTP_400_BAD_REQUEST)

                if payment_method_code != '0002' and float(data.get('advance_amount', 0)) > 0.0:
                    return Response({"msg": "Advance amount is set for a Due payment Option only"},
                                    status=status.HTTP_400_BAD_REQUEST)

                if data['phone_no'] != "":
                    if len(data['phone_no']) is not 10:
                        raise ValueError(
                            f"Please retype phone number. Must start with Zero and Allows only the length of 10 numbers."
                        )
                # Save Sales record
                sales = Sales.objects.create(
                    code=code,
                    sub_total=data['sub_total'],
                    tax=data['tax'],
                    tax_amount=data['tax_amount'],
                    grand_total=data['grand_total'],
                    tendered_total=data['tendered_total'],
                    tendered_amount=float(data['tendered_amount']),
                    amount_change=float(data['tendered_amount']) - float(data['grand_total']),
                    advance_amount=data['advance_amount'],
                    phone_no=data['phone_no'],
                    customer_id=customer_id,
                    payment_method=method,
                    loan_status=1 if payment_method_code == '0002' else 0,
                    # If payment method is 'Due', set loan_status to 1, else 0
                    user=request.user
                )

                sale_id = sales.pk
                total_of_totals = 0
                total_of_total_tenders = 0
                history = CustomerSalesHistory.objects.filter(customer_id=customer_id)

                # Iterate through each product and save SalesItems record
                for i, prod_id in enumerate(data.get('product_id[]')):
                    print(prod_id)
                    product = Products.objects.get(id=prod_id)
                    qty = int(data.get('qty[]')[i])
                    tendered_price = float(data.get('tendered_price[]')[i]) if data.get('tendered_price[]')[
                        i] else float(data.get('price[]')[i])

                    if tendered_price < product.price:
                        if request.user.is_staff:
                            return Response({
                                                "msg": f"Cannot save! Product {product} 's price ({tendered_price}) is smaller than the selling price ({product.price})."},
                                            status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response(
                                {"msg": "Cannot Save! The price you entered is below the minimum selling price."},
                                status=status.HTTP_400_BAD_REQUEST)

                    if qty > product.quantity:
                        if request.user.is_staff:
                            return Response({
                                                "msg": f"Cannot save! Requested quantity ({qty}) exceeds available stock of ({product.quantity}) for product ({product.name})."},
                                            status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response(
                                {"msg": f"Cannot save! Requested quantity ({qty}) exceeds available stock."},
                                status=status.HTTP_400_BAD_REQUEST)

                    price = float(data.get('price[]')[i])
                    total = qty * price
                    total_of_totals += total

                    total_tendered_price = qty * tendered_price
                    total_of_total_tenders += total_tendered_price

                    # Create SalesItems
                    salesItems.objects.create(
                        sale_id=sales,
                        product_id=product,
                        tendered_price=tendered_price,
                        change=tendered_price - float(product.price),
                        qty=qty,
                        price=price,
                        total=total,
                        total_tendered_price=total_tendered_price
                    )

                    StockMovement.objects.create(
                        product=product,
                        product_name=product.name,
                        customer_id=customer_id,
                        buying_price=product.buying_price,
                        selling_price=product.price,
                        tendered_amount=data['tendered_amount'],
                        quantity_in_past=(product.quantity),
                        quantity_in_stock=product.quantity,
                        quantity_sold=qty,
                        user=request.user
                    )

                    # i += 1

                # Handle payment method and loan
                if payment_method_code == '0002':
                    if customer_id:
                        if float(data['advance_amount']) > 0.0:
                            if 1.0 < float(data['advance_amount']) <= float(data['tendered_amount']):
                                DuePaymentHistory.objects.create(
                                    sale_id=sales,
                                    initial_loan=total_of_total_tenders,
                                    paid_amount=float(data['advance_amount']),
                                    total_paid_amount=float(data['advance_amount']),
                                    disbursed_amount=(total_of_total_tenders - float(data['advance_amount'])),
                                    user=request.user
                                )
                                CustomerSalesHistory.objects.create(
                                    customer_id=customer_id,
                                    code=generate_unique_code(),
                                    sale_id=sales,
                                    payment_method=method,
                                    initial_loan_amount=total_of_totals,
                                    paid_amount=float(data['advance_amount']),
                                    total_paid_amount=(
                                                float(data['advance_amount']) + sum(a.paid_amount for a in history)),
                                    balance=(((history.last().balance if history else 0) + total_of_totals) - float(
                                        data['advance_amount'])),
                                    tendered_initial_loan_amount=total_of_total_tenders,
                                    tendered_paid_amount=float(data['advance_amount']),
                                    tendered_total_paid_amount=(float(data['advance_amount']) + sum(
                                        a.tendered_paid_amount for a in history)),
                                    tendered_balance=(((
                                                           history.last().tendered_balance if history else 0) + total_of_total_tenders) - float(
                                        data['advance_amount'])),
                                    user=request.user
                                )
                                Customer.objects.filter(id=customer_id).update(has_loan=True)
                            elif float(data['advance_amount']) > float(data['tendered_amount']):
                                return Response({
                                                    "msg": "This is not a Due. Ensure the advance amount is not greater than the tendered amount"},
                                                status=status.HTTP_400_BAD_REQUEST)
                        else:
                            DuePaymentHistory.objects.create(
                                sale_id=sales,
                                initial_loan=total_of_total_tenders,
                                paid_amount=0,
                                total_paid_amount=0,
                                disbursed_amount=total_of_total_tenders,
                                user=request.user
                            )
                            CustomerSalesHistory.objects.create(
                                customer_id=customer_id,
                                code=generate_unique_code(),
                                sale_id=sales,
                                initial_loan_amount=total_of_totals,
                                payment_method=method,
                                paid_amount=0,
                                total_paid_amount=sum(a.paid_amount for a in history),
                                balance=((history.last().balance if history else 0) + total_of_totals),
                                tendered_initial_loan_amount=total_of_total_tenders,
                                tendered_paid_amount=0,
                                tendered_total_paid_amount=sum(a.tendered_paid_amount for a in history),
                                tendered_balance=(
                                                     history.last().tendered_balance if history else 0) + total_of_total_tenders,
                                user=request.user
                            )
                            Customer.objects.filter(id=customer_id).update(has_loan=True)
                    else:
                        return Response({"msg": "Please select Customer first"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    CustomerSalesHistory.objects.create(
                        customer_id=customer_id,
                        code=generate_unique_code(),
                        sale_id=sales,
                        initial_loan_amount=0,
                        payment_method=method,
                        paid_amount=total_of_totals,
                        total_paid_amount=total_of_totals if not history else sum(a.paid_amount for a in history),
                        balance=(((history.last().balance if history else 0) + total_of_totals) - total_of_totals),
                        tendered_initial_loan_amount=0,
                        tendered_paid_amount=total_of_total_tenders,
                        tendered_total_paid_amount=total_of_total_tenders if not history else sum(
                            a.tendered_paid_amount for a in history),
                        tendered_balance=(((
                                               history.last().tendered_balance if history else 0) + total_of_total_tenders) - total_of_total_tenders),
                        user=request.user
                    )

                resp = {
                    'status': 'success',
                    'msg': "Sale Created Successfully",
                    'sale_id': sale_id
                }
        except Exception as e:
            return Response({'status': 'failed', 'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        last_check = CustomerSalesHistory.objects.filter(customer_id=customer_id).last()
        if last_check:
            if (
                    last_check.balance if (
                            company and company.is_direct_pricing_method) else last_check.tendered_balance) > 0:
                Customer.objects.filter(id=customer_id).update(has_loan=True)
            else:
                Customer.objects.filter(id=customer_id).update(has_loan=False)
        return Response(resp, status=status.HTTP_201_CREATED)
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Require login
def sales_list_api(request):
    query = request.GET.get('q')
    status_filter = request.GET.get('status')
    per_page = request.GET.get('per_page', 100)

    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    current_day = now.strftime("%d")

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 50  # Fallback to 50 if conversion fails

    if query:
        sales_queryset = Sales.objects.filter(
            Q(id__icontains=query) |
            Q(customer__name__icontains=query)
        )
    else:
        sales_queryset = Sales.objects.all()

    if not request.user.is_staff:
        sales_queryset = sales_queryset.filter(user=request.user).filter(
            date_added__year=current_year,
            date_added__month=current_month,
            date_added__day=current_day
        )

    if status_filter:
        sales_queryset = sales_queryset.filter(status=status_filter)

    paginator = PageNumberPagination()
    paginator.page_size = per_page
    paginated_sales = paginator.paginate_queryset(sales_queryset.order_by('-date_added'), request)

    serializer = SalesSerializer(paginated_sales, many=True)

    return paginator.get_paginated_response({
        'sales': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure the user is authenticated
def view_sold_products_api(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 100)  # Default to 100 items per page
    sale_id = request.GET.get('id')

    # Get the Sale object or return 404
    sale = get_object_or_404(Sales, id=sale_id)

    # Filter the salesItems by sale and query (if provided)
    if query:
        items = salesItems.objects.filter(sale_id=sale).filter(
            Q(product_id__name__icontains=query)
        ).select_related('product_id')
    else:
        items = salesItems.objects.filter(sale_id=sale).select_related('product_id')

    # Get company and due payment history
    company = Company.objects.filter(user=request.user).first()

    total_item_quantity = sum(q.qty for q in items)

    # Calculate product totals based on pricing method
    if company:
        if company.is_direct_pricing_method:
            product_totals = sum(item.total for item in items)
        else:
            product_totals = sum(item.total_tendered_price for item in items)
    else:
        product_totals = sum(item.total_tendered_price for item in items)

    # Pagination for items
    paginator = PageNumberPagination()
    paginator.page_size = per_page
    paginated_items = paginator.paginate_queryset(items, request)

    items_serializer = SalesItemsSerializer(paginated_items, many=True)

    # Prepare the response data
    response_data = {
        # 'sale': SalesSerializer(sale).data,
        'items': items_serializer.data,
        'item_counts': total_item_quantity,
        'product_totals': product_totals,
        'company': company.name if company else None,
        'total_entries': paginator.page.paginator.count
    }

    return paginator.get_paginated_response(response_data)



###################################### end API ##################################################