import logging
import random
import string
from collections import defaultdict

from _decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.mail import send_mail
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction
from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse, BadHeaderError
from django.urls import reverse
from django.utils.translation import activate
from django.views.decorators.http import require_http_methods, require_POST
from flask import jsonify

from posApp.models import Category, Products, Sales, salesItems, Customer, Supplier, DuePaymentHistory, UserProfile, \
    purchasesItems, Purchases, StockMovement, Company, StoreLocations, PaymentMethod, Units, PurchasesDuePaymentHistory, \
    CustomProforma, CustomProformaItems, SupplierPurchasesHistory, CustomerSalesHistory, StockMovementHistory
from django.db.models import Count, Sum, Q, F, OuterRef, Max, Subquery
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect
import json, sys
from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from posApp.permissions import admin_required
from .csv import import_products_csv_files, csv_populater, import_suppliers_customers_csv_files
from django.contrib.auth import views as auth_views
from django.utils import translation
from django.core.management import call_command

from .tasks import update_stock_movement, update_stock_movement_on_unapprove

User = get_user_model()


class CustomLoginView(auth_views.LoginView):
    template_name = 'posApp/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if user.is_authenticated:
            user_profile = UserProfile.objects.filter(user=user).first()
            if user_profile:
                language = user_profile.preferred_language
                self.request.session['preferred_language'] = language
        return response


# Login
def login_user(request):
    logout(request)
    resp = {"status": 'failed', 'msg': ''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status'] = 'success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"
    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
def manage_user_profile(request):
    customer = {}
    if request.method == 'GET':
        data = request.GET
        customer_id = ''
        if 'id' in data:
            customer_id = data['id']
        if customer_id.isnumeric() and int(customer_id) > 0:
            customer = Customer.objects.filter(id=customer_id).first()

    context = {
        'customer': customer
    }
    return render(request, 'posApp/manage_user_profile.html', context)


@login_required
def update_user_profile(request):
    if request.method == "POST":
        employee_id = request.POST.get('id')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        passwd = request.POST.get('password')

        if passwd:
            password = make_password(passwd)
            if employee_id and User.objects.filter(id=employee_id).exists():
                user = User.objects.get(id=employee_id)
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.password = password
                user.save()
                messages.success(request, 'You have successfully updated your Account.')
            else:
                messages.success(request, 'No data exists.')
        else:
            if employee_id and User.objects.filter(id=employee_id).exists():
                user = User.objects.get(id=employee_id)
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                messages.success(request, 'You have successfully updated your Account.')
            else:
                messages.error(request, 'No data exists.')
                return JsonResponse({'status': 'failed'})

        return JsonResponse({'status': 'success'})
    print("hapaa")
    return JsonResponse({'status': 'failed'})


def generate_reset_code(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # Validate email (You can use Django's built-in email validation)
        # Generate a random code of 5 characters containing both integers and strings
        code_characters = string.ascii_letters + string.digits
        code = ''.join(random.choices(code_characters, k=5))
        # Store code and email in session
        request.session['reset_code'] = code
        request.session['reset_email'] = email

        # Send code to the user's email (Implement email sending logic here)
        try:
            header = "POS OTP CODE VERIFICATION"
            # Example of sending email to users
            send_mail(
                header,
                f"Your OTP Code is : {code}\n Go use it to reset your password.\n\nThank you.\nRegards,\n{settings.EMAIL_HOST_USER}",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return JsonResponse({'success': True})
        except BadHeaderError as e:
            logging.error(f"Error sending email: {e}")
            return JsonResponse({'success': False, 'message': 'Bad header detected.'})
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return JsonResponse({'success': False, 'message': 'Email not sent.'})
    else:
        return JsonResponse({'success': False})


def reset_password(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        new_password = request.POST.get('newPassword')
        confirm_new_password = request.POST.get('confirmPassword')
        # Compare entered code with the one stored in session
        if 'reset_code' in request.session and request.session['reset_code'] == code:
            # Code matches, proceed with password reset logic
            # Validate new password
            if new_password == confirm_new_password:
                # Passwords match, reset password for the user
                try:
                    email = request.session.get('reset_email')
                    user = User.objects.get(email=email)
                    user.set_password(new_password)
                    user.save()
                    # Clear the code from session
                    del request.session['reset_code']
                    del request.session['reset_email']
                    return JsonResponse({'success': True})
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'User does not exist.'})
            else:
                return JsonResponse({'success': False, 'message': 'Passwords do not match.'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid or expired code.'})
    else:
        return JsonResponse({'success': False})


@login_required
@require_POST
def set_language(request):
    language = request.POST.get('language')
    # print(f"angaa: {language}")
    if language in ['en', 'sw']:
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile:
            user_profile.preferred_language = language
            user_profile.save()
        else:
            UserProfile.objects.create(user=request.user, preferred_language=language)

        request.session['preferred_language'] = language
        activate(language)
        # print(f"angaa: {user_profile}")
        return redirect(request.META.get('HTTP_REFERER', '/'))
        # return redirect(request.POST.get('next', '/'))


# Logout
def logoutuser(request):
    logout(request)
    return redirect('/')


# Create your views here.
@login_required
def home(request):
    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    current_day = now.strftime("%d")
    categories = len(Category.objects.all())
    products = len(Products.objects.all())
    transaction = len(Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    ))
    today_sales = Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    ).all()
    total_sales = sum(today_sales.values_list('grand_total', flat=True))
    context = {
        'page_title': 'Home',
        'categories': categories,
        'products': products,
        'transaction': transaction,
        'total_sales': total_sales,
    }
    return render(request, 'posApp/home.html', context)


def about(request):
    context = {
        'page_title': 'About',
    }
    return render(request, 'posApp/about.html', context)


# Categories
@login_required
@permission_required('posApp.view_category', raise_exception=True)
def category(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    if query:
        category_list = Category.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).order_by('-date_added')
    else:
        category_list = Category.objects.all().order_by('-date_added')

    paginator = Paginator(category_list, per_page)
    page = request.GET.get('page')

    try:
        category_page = paginator.page(page)
    except PageNotAnInteger:
        category_page = paginator.page(1)
    except EmptyPage:
        category_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (category_page.number - 1) * per_page + 1
    end_index = min(category_page.number * per_page, paginator.count)

    context = {
        'page_title': 'Category List',
        'category': category_page,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/category.html', context)


@login_required
@permission_required('posApp.add_category', raise_exception=True)
@permission_required('posApp.change_category', raise_exception=True)
def manage_category(request):
    category = {}
    if request.method == 'GET':
        data = request.GET
        id = ''
        if 'id' in data:
            id = data['id']
        if id.isnumeric() and int(id) > 0:
            category = Category.objects.filter(id=id).first()

    context = {
        'category': category
    }
    return render(request, 'posApp/manage_category.html', context)


@login_required
@permission_required('posApp.add_category', raise_exception=True)
@permission_required('posApp.change_category', raise_exception=True)
def save_category(request):
    data = request.POST
    resp = {'status': 'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0:
            save_category = Category.objects.filter(id=data['id']).update(name=data['name'],
                                                                          description=data['description'],
                                                                          status=data['status'])
        else:
            save_category = Category(name=data['name'], description=data['description'], status=data['status'])
            save_category.save()
        resp['status'] = 'success'
        messages.success(request, 'Category Successfully saved.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@permission_required('posApp.delete_category', raise_exception=True)
def delete_category(request):
    data = request.POST
    resp = {'status': ''}
    try:
        Category.objects.filter(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Category Successfully deleted.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")


# Products
@login_required
@permission_required('posApp.view_products', raise_exception=True)
def products(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 150)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 100  # Fallback to 500 if conversion fails

    if query:
        product_list = Products.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(code__icontains=query) |
            Q(category_id__name__icontains=query)
        ).order_by('-date_added')
    else:
        product_list = Products.objects.all().order_by('-date_added')

    paginator = Paginator(product_list, per_page)
    page = request.GET.get('page')

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    total_price = 0
    for product in product_list:
        total_price += (product.buying_price * (float(product.quantity) + (product.left_pieces / product.max_pieces)))
    # Calculate the range of entries being displayed
    start_index = (products_page.number - 1) * per_page + 1
    end_index = min(products_page.number * per_page, paginator.count)
    context = {
        'page_title': 'Product List (Stock)',
        'products': products_page,
        'total_price': total_price,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/products.html', context)


@login_required
@permission_required('posApp.add_products', raise_exception=True)
@permission_required('posApp.change_products', raise_exception=True)
@login_required
def manage_products(request):
    product = {}
    categories = Category.objects.filter(status=1).all()
    units = Units.objects.all()
    suppliers = Supplier.objects.all()

    if request.method == 'GET':
        data = request.GET
        id = data.get('id', '')
        if id.isnumeric() and int(id) > 0:
            product = Products.objects.filter(id=id).first()

    context = {
        'code': generate_unique_code(),
        'product': product,
        'categories': categories,
        'units': units,
        'suppliers': suppliers
    }
    return render(request, 'posApp/manage_product.html', context)


def generate_unique_code():
    while True:
        code = f"{random.randint(0, 999999):06}"
        if not Products.objects.filter(code=code).exists():
            return code


@login_required
def clear_quantities(request):
    if request.method == 'POST' and request.user.is_staff:
        Products.objects.all().update(quantity=0)
        return JsonResponse({'status': 'success', 'msg': 'Quantities cleared successfully.'})
    else:
        return JsonResponse({'status': 'failed', 'msg': 'Permission denied or invalid request method.'})


@login_required
@permission_required('posApp.view_category', raise_exception=True)
def test(request):
    categories = Category.objects.all().order_by('-date_added')
    context = {
        'categories': categories
    }
    return render(request, 'posApp/test.html', context)


from django.shortcuts import render
from django.http import HttpResponse
import json
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import Products, Category, Supplier


@login_required
@permission_required('posApp.add_products', raise_exception=True)
@permission_required('posApp.change_products', raise_exception=True)
def save_product(request):
    if request.method == 'POST':
        data = request.POST
        resp = {'status': 'failed'}
        id = data.get('id', '')
        # Check if a file is uploaded
        if 'file' in request.FILES:
            # If a file is uploaded, call import_csv_files function
            model = Products  # Specify the model class
            fields = ['category_id', 'name', 'description', 'buying_price', 'price', 'unit_id',
                      'minimum_quantity', 'quantity', 'left_pieces', 'max_pieces',
                      'markup']  # Specify the fields corresponding to CSV columns
            return import_products_csv_files(request, model, fields)

        else:
            # If no file is uploaded, proceed with saving product from form data
            # Your existing code for saving products from form data goes here
            if id.isnumeric() and int(id) > 0:
                check = Products.objects.exclude(id=id).filter(code=data['code']).all()
            else:
                check = Products.objects.filter(code=data['code']).all()

            if float(data['price']) < float(data['buying_price']):
                resp['msg'] = "Selling price can't be smaller than buying price"
                return HttpResponse(json.dumps(resp), content_type="application/json")

            if check.exists():
                resp['msg'] = "Product Code Already Exists in the database"
            else:
                category = Category.objects.filter(id=data['category_id']).first()
                unit = Units.objects.filter(id=data['unit_id']).first()
                total_pieces = 0
                print(f"heere: {data['left_pieces']} {data['max_pieces']}")
                if int(data['left_pieces']) > 0 and int(data['max_pieces']) > 0:
                    total_pieces = (Decimal(data['quantity']) * Decimal(data['max_pieces'])) + Decimal(
                        data['left_pieces'])
                try:
                    if id.isnumeric() and int(id) > 0:
                        product = Products.objects.filter(id=id).first()
                        product.code = data['code']
                        product.category_id = category
                        product.name = data['name']
                        product.description = data['description']
                        product.price = float(data['price'])
                        product.quantity = data['quantity']
                        product.minimum_quantity = int(data['min_quantity'])
                        product.buying_price = float(data['buying_price'])
                        product.markup = data['markup']
                        product.left_pieces = data['left_pieces']
                        product.max_pieces = data['max_pieces']
                        product.total_pieces = total_pieces
                        product.units = unit
                        product.status = data['status']
                        product.save()
                    else:
                        product = Products(
                            code=data['code'],
                            category_id=category,
                            name=data['name'],
                            description=data['description'],
                            price=float(data['price']),
                            buying_price=float(data['buying_price']),
                            markup=data['markup'],
                            left_pieces=data['left_pieces'],
                            max_pieces=data['max_pieces'],
                            total_pieces=total_pieces,
                            units=unit,
                            quantity=int(data['quantity']),
                            minimum_quantity=int(data['min_quantity']),
                            status=data['status'],
                            user=request.user
                        )
                        product.save()
                    StockMovement.objects.create(
                        product=product,
                        product_name=product.name,
                        buying_price=product.buying_price,
                        selling_price=product.price,
                        user=request.user
                    )
                    msg = 'Product Successfully saved.'
                    resp['status'] = 'success'
                    messages.success(request, msg)
                except Exception as e:
                    resp['msg'] = str(e)
                    resp['status'] = 'failed'

            return HttpResponse(json.dumps(resp), content_type="application/json")

    return HttpResponse(json.dumps({'status': 'failed', 'msg': 'Invalid request method'}),
                        content_type="application/json")


@login_required
@permission_required('posApp.view_products', raise_exception=True)
def export_products_csv_file(request):
    if request.method == 'GET':
        return csv_populater(request, "posApp", "products")
    return HttpResponse(json.dumps({'status': 'failed', 'msg': 'Invalid request method'}),
                        content_type="application/json")


@login_required
@permission_required('posApp.delete_products', raise_exception=True)
def delete_product(request):
    data = request.POST
    resp = {'status': ''}
    try:
        Products.objects.filter(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Product Successfully deleted.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@permission_required('posApp.view_products', raise_exception=True)
def pos(request):
    products = Products.objects.filter(status=1).order_by('-date_added')
    customers = Customer.objects.all().order_by('-date_added')  # Fetch all customers
    payment_methods = PaymentMethod.objects.all()
    product_json = []
    for product in products:
        product_json.append(
            {'id': product.id, 'name': product.name, 'price': float(product.price),
             'quantity': float(product.quantity), 'left_pieces': product.left_pieces,
             'max_pieces': product.max_pieces, 'total_pieces': product.total_pieces, 'markup': float(product.markup)})
    context = {
        'page_title': "Point of Sale",
        'customers': customers,  # Pass customers to the template
        'payment_methods': payment_methods,
        'products': products,
        'product_json': json.dumps(product_json)
    }
    # return HttpResponse('')
    return render(request, 'posApp/pos.html', context)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def custom_proforma(request):
    customers = Customer.objects.all().order_by('-date_added')  # Fetch all customers
    products = Products.objects.filter(status=1).order_by('-date_added')
    product_json = []
    for product in products:
        product_json.append({'id': product.id, 'name': product.name, 'price': float(product.buying_price)})
    context = {
        'page_title': "Proforma",
        'customers': customers,  # Pass customers to the template
        'products': products,
        'product_json': json.dumps(product_json)
    }
    # return HttpResponse('')
    return render(request, 'posApp/proforma.html', context)


@login_required
def checkout_modal(request):
    grand_total = 0
    if 'grand_total' in request.GET:
        grand_total = request.GET['grand_total']
    customers = Customer.objects.all()  # Fetch all customers
    context = {
        'grand_total': grand_total,
        'customers': customers,  # Pass customers to the template
    }
    return render(request, 'posApp/checkout.html', context)


@login_required
@permission_required('posApp.add_sales', raise_exception=True)
# @permission_required('posApp.change_sales', raise_exception=True)
def save_pos(request):
    resp = {'status': 'failed', 'msg': ''}
    data = request.POST
    company = Company.objects.filter(user=request.user).first()
    if request.method == "POST":
        # Edit sale items
        try:
            with transaction.atomic():
                sale_id = int(request.POST.get('sale_id', 0))
                item_id = request.POST.get('id', None)
                product_id = request.POST.get('product_id', None)
                quantity = int(request.POST.get('quantity', 0))
                pcs = int(request.POST.get('pcs', 0))
                selling_price = float(request.POST.get('price', 0))

                # Add single item in sale
                if sale_id and sale_id > 0:
                    product = Products.objects.get(id=product_id)
                    quantity_in_past = product.quantity
                    sale = Sales.objects.filter(id=sale_id).first()
                    if sale:  # This is already an instance, no need to call .exists() again
                        if quantity > 0 and selling_price > 10:
                            if quantity <= product.quantity:
                                if selling_price >= product.price:
                                    salesItems.objects.create(
                                        sale_id=sale,  # Directly pass the instance
                                        product_id=product,  # Directly pass the instance
                                        tendered_price=selling_price,
                                        change=selling_price - float(product.price),
                                        qty=quantity,
                                        price=product.price,
                                        total=(product.price * quantity),
                                        total_tendered_price=(selling_price * quantity)
                                    )

                                    # Update product quantity
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

                                    # update sale
                                    new_grand_total = 0
                                    for i in salesItems.objects.filter(sale_id=sale):  # Updated
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

                                    messages.success(request, 'Item successfully Added.')
                                    return JsonResponse({'status': 'success'})
                                else:
                                    if request.user.is_staff:
                                        messages.error(request,
                                                       f'Not Added. Price ({intcomma(selling_price)}) is smaller than the minimum selling price ({intcomma(product.price)}) for product ({product.name}).')
                                    else:
                                        messages.error(request,
                                                       'Not Updated. The price you entered is below the minimum selling price.')

                                    return JsonResponse({'status': 'failed'})

                            else:
                                if request.user.is_staff:
                                    messages.error(request,
                                                   f'Not Added. Quantity ({quantity}) Exceeds stock ({product.quantity}) for product ({product.name}).')
                                else:
                                    messages.error(request, 'Not Added. Quantity Exceeds stock.')

                                return JsonResponse({'status': 'failed'})
                        else:
                            messages.error(request, 'Not Added. Quantity and Price must be greater than zero.')
                            return JsonResponse({'status': 'failed'})

                # Edit items
                if item_id:
                    # Save or update the company information
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

                                    # punguza stock
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
                                    print(f" hii : {sale.first().tendered_total}")
                                    if sale.first().payment_method.code == '0001':
                                        CustomerSalesHistory.objects.filter(sale_id=sale.first()).update(
                                            paid_amount=sale.first().grand_total,
                                            tendered_paid_amount=sale.first().tendered_total,
                                        )

                                    messages.success(request, 'Item successfully updated.')
                                    return JsonResponse({'status': 'success'})
                                else:
                                    if request.user.is_staff:
                                        messages.error(request,
                                                       f'Not Updated. Price ({intcomma(selling_price)}) is smaller than the minimum selling price ({intcomma(item.first().product_id.price)}) for product ({item.first().product_id.name}).')
                                    else:
                                        messages.error(request,
                                                       'Not Updated. The price you entered is below the minimum selling price.')

                                    return JsonResponse({'status': 'failed'})

                            else:
                                if request.user.is_staff:
                                    messages.error(request,
                                                   f'Not Updated. Quantity ({quantity}) Exceeds stock ({item.first().product_id.quantity}) for product ({item.first().product_id.name}).')
                                else:
                                    messages.error(request, 'Not Updated. Quantity Exceeds stock.')

                                return JsonResponse({'status': 'failed'})
                        else:
                            messages.error(request, 'Not updated. Quantity and Price must be greater than zero.')
                            return JsonResponse({'status': 'failed'})
                    else:
                        messages.error(request, 'Not updated. Item not exists.')
                        return JsonResponse({'status': 'failed'})

        except Exception as e:
            print(f" wegoo error: {e} ")
            messages.error(request, f'Not updated/Added. Error. {e}')
            return JsonResponse({'status': 'failed'})

    pref = str(datetime.now().year) + str(datetime.now().year)
    i = 1

    # Generate a unique sales code
    while True:
        code = '{:0>5}'.format(i)
        i += 1
        if not Sales.objects.filter(code=str(pref) + str(code)).exists():
            break
    code = str(pref) + str(code)
    # Save sale
    try:
        with transaction.atomic():
            # Retrieve customer and payment method from the form
            customer_id = request.POST.get('customer')
            payment_method = request.POST.get('payment_method')
            method = PaymentMethod.objects.filter(code=payment_method).first()

            if not method:
                raise ValueError(
                    f"Please select payment method."
                )

            if not customer_id and payment_method == '0002':
                raise ValueError(
                    f"Please select customer. Can't make a loan to someone you don't know"
                )

            if payment_method != '0002' and float(data['advance_amount']) > 0.0:
                raise ValueError(
                    f"Advance amount is set for a Due payment Option only"
                )

            if data['phone_no'] != "":
                if len(data['phone_no']) != 10:
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
                loan_status=1 if payment_method == '0002' else 0,
                # If payment method is 'Due', set loan_status to 1, else 0
                user=request.user
            )

            sale_id = sales.pk
            i = 0
            total_of_totals = 0
            total_of_total_tenders = 0
            history = CustomerSalesHistory.objects.filter(customer_id=customer_id)
            # Iterate through each product and save SalesItems record
            for prod in data.getlist('product_id[]'):
                product = Products.objects.get(id=prod)
                qty = float(data.getlist('qty[]')[i]) if data.getlist('qty[]')[i] else 0
                pcs = (int(data.getlist('pcs[]')[i]) if data.getlist('pcs[]')[i] else 0) if \
                    product.markup > 0 and product.max_pieces > 1 else 0
                price = float(data.getlist('price[]')[i])
                if data.getlist('tendered_price[]')[i] == "":
                    tendered_price = float(data.getlist('price[]')[i])
                else:
                    tendered_price = float(data.getlist('tendered_price[]')[i])

                if tendered_price < product.price:
                    if request.user.is_staff:
                        raise ValueError(
                            f"Cannot save! Product {product} 's price ({intcomma(tendered_price)}) is smaller than the selling price ({intcomma(product.price)})."
                        )
                    else:
                        raise ValueError("Can not Save! The price you entered is below the minimum selling price.")

                if qty > float(product.quantity):
                    if request.user.is_staff:
                        raise ValueError(
                            f"Cannot save! Requested quantity ({qty}) exceeds available stock of ({product.quantity})for product ({product.name})."
                        )
                    else:
                        raise ValueError(
                            f"Cannot save! Requested quantity ({qty}) exceeds available stock, which is less than {qty}"
                        )

                if pcs and (pcs + (qty * float(product.max_pieces))) > product.total_pieces:
                    if request.user.is_staff:
                        raise ValueError(
                            f"Cannot save! Requested pieces ({pcs}) exceeds available stock of ({product.quantity}) and ({product.left_pieces})for product ({product.name})."
                        )
                    else:
                        raise ValueError(
                            f"Cannot save! Requested pieces ({pcs}) exceeds available stock"
                        )

                if pcs and pcs != "" and pcs > 0:
                    individual_price = (price / product.max_pieces) + (
                                (price * float(product.markup)) / (100 * product.max_pieces))
                    individual_tendered_price = (tendered_price / product.max_pieces) + (
                            (tendered_price * float(product.markup)) / (100 * product.max_pieces))
                    total = (qty * price) + (pcs * individual_price)
                    total_tendered_price = (qty * tendered_price) + (pcs * individual_tendered_price)
                else:
                    total = qty * price
                    total_tendered_price = qty * tendered_price

                total_of_totals += total
                total_of_total_tenders += total_tendered_price

                salesItems.objects.create(
                    sale_id=sales,
                    product_id=product,
                    tendered_price=tendered_price,
                    change=tendered_price - float(product.price),
                    qty=qty,
                    pcs=pcs,
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

                # # Update product quantity
                # product.quantity -= qty
                # product.save()
                i += 1

            if payment_method == '0002':
                if customer_id:
                    if float(data['advance_amount']) > 0.0:
                        if 1.0 < float(data['advance_amount']) <= float(data['tendered_amount']):
                            print(
                                f"hereeeee1 : {data['advance_amount']} and {total_of_total_tenders}  and {total_of_total_tenders - float(data['advance_amount'])}")
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
                                total_paid_amount=(float(data['advance_amount']) + sum(a.paid_amount for a in history)),
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
                            resp[
                                'msg'] = f"This is not a DUe.. Makesure the advanced amount is not greater than Saling amount (Tendered Amount)"
                            return HttpResponse(json.dumps(resp), content_type="application/json")

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
                                    (history.last().tendered_balance if history else 0) + total_of_total_tenders),
                            user=request.user
                        )
                        Customer.objects.filter(id=customer_id).update(has_loan=True)
                else:
                    resp['msg'] = f"Please select Customer first"
                    return HttpResponse(json.dumps(resp), content_type="application/json")
            else:
                # if has no loan, create history
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
            resp['status'] = 'success'
            resp['sale_id'] = sale_id
            messages.success(request, "Sale Record has been saved.")

    except Exception as e:
        resp['msg'] = f"An error occurred: {e}"
        print("Unexpected error:", e.with_traceback(None))

    last_check = CustomerSalesHistory.objects.filter(customer_id=customer_id).last()
    if last_check:
        if (last_check.balance if (company and company.is_direct_pricing_method) else last_check.tendered_balance) > 0:
            Customer.objects.filter(id=customer_id).update(has_loan=True)
        else:
            Customer.objects.filter(id=customer_id).update(has_loan=False)
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
@admin_required
def manage_pos(request):
    item = None
    products = []
    data = request.GET
    sale_id = None

    if request.method == 'GET':
        id = data.get('id', '0')
        add_item = data.get('add_item', '0')
        if add_item == '1':
            products = Products.objects.all()
            sale_id = id
        else:
            if id.isnumeric() and int(id) > 0:
                item = salesItems.objects.filter(id=id).first()

    print(sale_id)
    context = {
        'products': products,
        'item': item,
        'sale_id': sale_id
    }

    return render(request, 'posApp/manage_pos_items.html', context)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def salesList(request):
    query = request.GET.get('q')
    # Get the status filter from the request (defaults to None)
    status_filter = request.GET.get('status')
    per_page = request.GET.get('per_page', 100)  # Default to 20 items per page if not specified
    customer = {}
    sales = {}
    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    current_day = now.strftime("%d")

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 50  # Fallback to 20 if conversion fails

    if query:
        sale = Sales.objects.filter(
            Q(id__icontains=query) |
            Q(customer__name__contains=query) |
            Q(phone_no__icontains=query) |
            Q(user__username__contains=query)
            # Q(customer__phone__contains=query) |
            # Q(code__icontains=query) |
            # Q(date_added__icontains=query) |
            # Q(date_updated__icontains=query)
        )
    else:
        sale = Sales.objects.all()

    if request.user.is_staff:
        sales = sale
    else:
        sales = sale.filter(user=request.user).filter(
            date_added__year=current_year,
            date_added__month=current_month,
            date_added__day=current_day
        ).all()

    # Apply filter if a specific status is selected
    if status_filter is not None and status_filter != '':
        sales = sales.filter(status=status_filter)

    paginator = Paginator(sales.order_by('-date_added'), per_page)
    page = request.GET.get('page')

    try:
        sales_page = paginator.page(page)
    except PageNotAnInteger:
        sales_page = paginator.page(1)
    except EmptyPage:
        sales_page = paginator.page(paginator.num_pages)

    sale_data = []
    for sale in sales_page:
        data = {}
        for field in sale._meta.get_fields(include_parents=False):
            if field.related_model is None:
                data[field.name] = getattr(sale, field.name)
        data['items'] = salesItems.objects.filter(sale_id=sale).all()
        data['payment_method'] = sale.payment_method
        # data['item_count'] = sum(q.qty for q in data['items'])
        data['item_count'] = data['items'].count()
        data['customer'] = sale.customer
        data['user'] = sale.user
        data['total_tendered_amount'] = sale.tendered_total
        if 'tax_amount' in data:
            data['tax_amount'] = format(float(data['tax_amount']), '.2f')
        sale_data.append(data)

        # Calculate the range of entries being displayed
    start_index = (sales_page.number - 1) * per_page + 1
    end_index = min(sales_page.number * per_page, paginator.count)
    context = {
        'page_title': 'Sales Transactions',
        'sale_data': sale_data,
        'sales': sales_page,  # Add the paginated sales
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
        'company': Company.objects.filter(user=request.user).first()
    }
    return render(request, 'posApp/sales.html', context)


logger = logging.getLogger(__name__)


@login_required
@admin_required
def remove_item_in_sale(request):
    if request.method == "POST":
        data = request.POST
        resp = {'status': ''}
        try:
            with transaction.atomic():
                sale_item_id = data.get('id')
                sale_item = salesItems.objects.get(id=sale_item_id)
                sale = Sales.objects.get(id=sale_item.sale_id_id)
                all_items_in_sale = salesItems.objects.filter(sale_id=sale).all()

                if len(all_items_in_sale) <= 1:
                    sale.delete()
                    #
                    # for sale_item in all_items_in_sale:
                    #     product_qts = sale_item.product_id.quantity
                    #     reversed_products_qty = product_qts + sale_item.qty
                    #     sale_item.product_id.quantity = reversed_products_qty
                    #     sale_item.product_id.save()

                    messages.success(request, 'Item successfully removed.')
                    resp['status'] = 'success'
                    # resp['redirect'] = 'sales-page'
                else:
                    sale_item.delete()
                    # product_qts = sale_item.product_id.quantity
                    # reversed_products_qty = product_qts + sale_item.qty
                    # sale_item.product_id.quantity = reversed_products_qty
                    # # return stock movement
                    # StockMovement.objects.create(
                    #     product=sale_item.product_id,
                    #     product_name=sale_item.product_id.name,
                    #     buying_price=sale_item.product_id.buying_price,
                    #     selling_price=sale_item.product_id.price,
                    #     quantity_in_past=sale_item.product_id.quantity - sale_item.qty,
                    #     # quantity_in_stock=product.quantity + qty,
                    #     quantity_returned=sale_item.qty,
                    #     user=request.user
                    # )
                    messages.success(request, 'Item successfully removed.')
                    resp['status'] = 'success'

                    # update sale
                    total = 0
                    grand_total = 0
                    total_tendered = 0
                    sale_new = salesItems.objects.filter(sale_id=sale).all()
                    for items in sale_new:
                        total = items.total
                        grand_total += (items.price * items.qty)
                        total_tendered += (items.tendered_price * items.qty)
                    sale.grand_total = grand_total
                    sale.tendered_total = total_tendered
                    sale.sub_total = total
                    sale.tendered_amount = total
                    sale.save()
                # Create History
                if sale:
                    if sale.payment_method.code == '0001':
                        CustomerSalesHistory.objects.filter(sale_id=sale).update(
                            paid_amount=sale.grand_total,
                            tendered_paid_amount=sale.tendered_total,
                        )

                # rudisha store
                if sale.status == 1:
                    product_qts = sale_item.product_id.quantity
                    reversed_products_qty = product_qts + sale_item.qty
                    sale_item.product_id.quantity = reversed_products_qty
                    sale_item.product_id.save()
                    # return stock movement
                    StockMovement.objects.create(
                        product=sale_item.product_id,
                        product_name=sale_item.product_id.name,
                        buying_price=sale_item.product_id.buying_price,
                        selling_price=sale_item.product_id.price,
                        quantity_in_past=sale_item.product_id.quantity - sale_item.qty,
                        # quantity_in_stock=product.quantity + qty,
                        quantity_returned=sale_item.qty,
                        user=request.user
                    )

                    # Get the StockMovementHistory record for the product and date
                update_stock_movement_on_unapprove(sale_item, 0)  # 0 for sale item

        except salesItems.DoesNotExist:
            logger.error(f'SalesItem with id {sale_item_id} does not exist')
            resp['status'] = 'failed'
            resp['msg'] = 'Sale item not found.'
        except Sales.DoesNotExist:
            logger.error(f'Sale with id {sale_item.sale_id_id} does not exist')
            resp['status'] = 'failed'
            resp['msg'] = 'Sale not found.'
        except Exception as e:
            logger.error(f'Error removing item from sale: {e}')
            resp['status'] = 'failed'
            resp['msg'] = str(e)
        return JsonResponse(resp)
    else:
        return JsonResponse({'status': 'failed', 'msg': 'Invalid request method.'})


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def loan_repayments(request):
    history = DuePaymentHistory.objects.all()

    history_data = []
    for hist in history:
        data = {}
        data['id'] = hist.id
        data['customers'] = hist.sale_id.customer
        data['sales'] = hist.sale_id
        data['total_paid_amount'] = hist.total_paid_amount
        data['disbursed_amount'] = hist.outstanding_amount
        history_data.append(data)

    context = {
        'history': history_data,
    }

    return render(request, 'posApp/loan_repayment_page.html', context)


@login_required
def create_sale_invoice(request):
    id = request.GET.get('id')
    sales = Sales.objects.filter(id=id).first()
    transaction = {}
    for field in Sales._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(sales, field.name)
    ItemList = salesItems.objects.filter(sale_id=sales).all()
    context = {
        "sale": sales,
        "transaction": transaction,
        "salesItems": ItemList
    }

    return render(request, 'posApp/sales_invoice.html', context)


@login_required
@permission_required('posApp.view_purchases', raise_exception=True)
def purchase(request):
    products = Products.objects.filter(status=1).order_by('-date_added')
    suppliers = Supplier.objects.filter().order_by('-date_added')
    payment_methods = PaymentMethod.objects.all()
    product_json = []
    for product in products:
        product_json.append({'id': product.id, 'name': product.name, 'price': float(product.buying_price)})
    context = {
        'page_title': "Purchases",
        'payment_methods': payment_methods,
        'products': products,
        'suppliers': suppliers,
        'product_json': json.dumps(product_json)
    }
    # return HttpResponse('')
    return render(request, 'posApp/purchase.html', context)


@login_required
@permission_required('posApp.add_purchases', raise_exception=True)
@permission_required('posApp.change_purchases', raise_exception=True)
def save_purchase(request):
    resp = {'status': 'failed', 'msg': ''}
    data = request.POST

    print(f"anga : {data}")
    print(f"anga : {data}")
    print(f"anga : {data.get('supplier')}")
    print(f"anga : {request.POST.get('payment_method')}")

    if request.method == "POST":
        # Edit sale items
        try:
            with transaction.atomic():
                item_id = request.POST.get('id', None)
                quantity = int(request.POST.get('quantity', 0))
                buying_price = float(request.POST.get('price', 0))
                print("hereeeeeeee")
                # Save or update the company information
                items = purchasesItems.objects
                item = items.filter(id=item_id)
                if item_id:
                    if item.exists():
                        if quantity > 0 and buying_price > 10:
                            reversed_qty = item.first().product_id.quantity - item.first().qty
                            item.update(
                                qty=quantity,
                                price=buying_price,
                                total=quantity * buying_price
                            )
                            Products.objects.filter(id=item.first().product_id.pk).update(
                                quantity=reversed_qty + quantity,
                                total_pieces=((
                                                      reversed_qty + quantity) * item.first().product_id.max_pieces) + item.product_id.left_pieces
                            )
                            purchase = Purchases.objects.filter(id=item.first().purchase_id.pk)
                            new_grand_total = 0
                            for i in items.filter(purchase_id=purchase.first()):
                                new_grand_total += i.total

                            purchase.update(
                                tendered_amount=buying_price,
                                sub_total=quantity * buying_price,
                                grand_total=new_grand_total,
                            )
                            print(purchase.first().grand_total)
                            if purchase.first().payment_method.code == '0001':
                                SupplierPurchasesHistory.objects.filter(purchase_id=purchase.first()).update(
                                    paid_amount=purchase.first().grand_total,
                                )

                            messages.success(request, 'Item successfully updated.')
                            return JsonResponse({'status': 'success'})
                        else:
                            messages.error(request, 'Not updated. Quantity and Price must be greater than zero.')
                            return JsonResponse({'status': 'failure'})
                    else:
                        messages.error(request, 'Not updated. Item not exists.')
                        return JsonResponse({'status': 'failure'})

        except Exception as e:
            item = salesItems.objects.filter(id=item_id)
            print(f" wegoo error: {e} {item.first()}")
            messages.error(request, f'Not updated. Error. {e}')
            return JsonResponse({'status': 'failure'})

        # Edit purchase items
        try:
            with transaction.atomic():
                purchase_id = int(request.POST.get('purchase_id', 0))
                item_id = request.POST.get('id', None)
                product_id = request.POST.get('product_id', None)
                quantity = int(request.POST.get('quantity', 0))
                purchasing_price = float(request.POST.get('price', 0))

                # Add single item in purchase
                if purchase_id:
                    product = Products.objects.get(id=product_id)
                    quantity_in_past = product.quantity
                    purchase = Purchases.objects.filter(id=purchase_id).first()
                    if purchase:  # This is already an instance, no need to call .exists() again
                        if quantity > 0 and purchasing_price > 10:
                            print(f"hii : {purchasing_price} < {product.price}")
                            purchasesItems.objects.create(
                                purchase_id=purchase,  # Directly pass the instance
                                product_id=product,  # Directly pass the instance
                                price=purchasing_price,
                                qty=quantity,
                                total=(purchasing_price * quantity)
                            )

                            # Update product quantity
                            if purchase.status == 1:
                                product.total_pieces += ((quantity * product.max_pieces) + product.left_pieces)
                                product.quantity += quantity
                                product.save()
                                StockMovement.objects.create(
                                    product=product,
                                    product_name=product.name,
                                    supplier_id=purchase.supplier.pk,
                                    buying_price=product.buying_price,
                                    selling_price=purchasing_price,
                                    tendered_amount=purchasing_price,
                                    quantity_in_past=quantity_in_past,
                                    quantity_in_stock=product.quantity,
                                    quantity_sold=quantity,
                                    user=request.user
                                )

                            # update purchase
                            new_grand_total = 0
                            for i in purchasesItems.objects.filter(purchase_id=purchase):  # Updated
                                new_grand_total += i.total

                            purchase.tendered_amount = purchasing_price
                            purchase.grand_total = new_grand_total
                            purchase.save()

                            if purchase.payment_method.code == '0001':
                                SupplierPurchasesHistory.objects.filter(purchase_id=purchase).update(
                                    paid_amount=purchase.grand_total,
                                    total_paid_amount=purchase.grand_total,
                                )

                            messages.success(request, 'Item successfully Added.')
                            return JsonResponse({'status': 'success'})
                        else:
                            messages.error(request, 'Not Added. Quantity and Price must be greater than zero.')
                            return JsonResponse({'status': 'failed'})

                # Edit items
                if item_id:
                    print("hereeeeeeee")
                    # Save or update the company information
                    items = salesItems.objects
                    item = items.filter(id=item_id)
                    if item.exists():
                        reversed_qty = item.first().product_id.quantity + item.first().qty
                        if quantity > 0 and purchasing_price > 10:
                            if quantity <= item.first().product_id.quantity:
                                if purchasing_price >= item.first().product_id.price:
                                    item.update(
                                        qty=quantity,
                                        tendered_price=purchasing_price,
                                        price=purchasing_price,
                                        total_tendered_price=quantity * purchasing_price,
                                        total=quantity * purchasing_price
                                    )

                                    purchase = Sales.objects.filter(id=item.first().sale_id.pk)

                                    # punguza stock
                                    if purchase.first().status == 1:
                                        Products.objects.filter(id=item.first().product_id.pk).update(
                                            quantity=reversed_qty - quantity,
                                            total_pieces=(reversed_qty - quantity) * item.first().product_id.max_pieces
                                        )

                                    new_grand_total = 0
                                    for i in items.filter(sale_id=purchase.first()):
                                        new_grand_total += i.total_tendered_price

                                    purchase.update(
                                        tendered_amount=purchasing_price,
                                        tendered_total=new_grand_total,
                                        grand_total=new_grand_total
                                    )
                                    print(f" hii : {purchase.first().tendered_total}")
                                    if purchase.first().payment_method.code == '0001':
                                        CustomerSalesHistory.objects.filter(sale_id=purchase.first()).update(
                                            paid_amount=purchase.first().grand_total,
                                            tendered_paid_amount=purchase.first().tendered_total,
                                        )

                                    messages.success(request, 'Item successfully updated.')
                                    return JsonResponse({'status': 'success'})
                                else:
                                    if request.user.is_staff:
                                        messages.error(request,
                                                       f'Not Updated. Price ({intcomma(purchasing_price)}) is smaller than the minimum selling price ({intcomma(item.first().product_id.price)}) for product ({item.first().product_id.name}).')
                                    else:
                                        messages.error(request,
                                                       'Not Updated. The price you entered is below the minimum selling price.')

                                    return JsonResponse({'status': 'failed'})

                            else:
                                if request.user.is_staff:
                                    messages.error(request,
                                                   f'Not Updated. Quantity ({quantity}) Exceeds stock ({item.first().product_id.quantity}) for product ({item.first().product_id.name}).')
                                else:
                                    messages.error(request, 'Not Updated. Quantity Exceeds stock.')

                                return JsonResponse({'status': 'failed'})
                        else:
                            messages.error(request, 'Not updated. Quantity and Price must be greater than zero.')
                            return JsonResponse({'status': 'failed'})
                    else:
                        messages.error(request, 'Not updated. Item not exists.')
                        return JsonResponse({'status': 'failed'})

        except Exception as e:
            print(f" wegoo error: {e} ")
            messages.error(request, f'Not updated/Added. Error. {e}')
            return JsonResponse({'status': 'failed'})
    pref = str(datetime.now().year)  # Simplified the prefix
    i = 1

    # Generate a unique purchase code
    while True:
        code = '{:0>5}'.format(i)
        i += 1
        if not Purchases.objects.filter(code=str(pref) + str(code)).exists():
            break
    code = str(pref) + str(code)

    try:
        with transaction.atomic():
            # Retrieve supplier from the form
            supplier_id = request.POST.get('supplier-id')
            supplier = Supplier.objects.get(id=supplier_id)  # Assuming you have a Supplier model

            # Retrieve payment method from the form
            payment_method = request.POST.get('payment_method')
            method = PaymentMethod.objects.filter(code=payment_method).first()

            if not method:
                raise ValueError(
                    f"Please select payment method."
                )

            if not supplier_id and payment_method == '0002':
                raise ValueError(
                    f"Please select supplier. Can't make a loan to supplier you don't know"
                )

            if payment_method != '0002' and float(data['advance_amount']) > 0.0:
                raise ValueError(
                    f"Advance amount is set for a Due payment Option only"
                )

            # Save Purchase record
            purchase = Purchases.objects.create(
                code=code,
                sub_total=data['sub_total'],
                grand_total=data['grand_total'],
                advance_amount=data['advance_amount'],
                car_number=data['car_no'],
                supplier_id=supplier_id,
                payment_method=method,
                loan_status=1 if payment_method == '0002' else 0,
                user=request.user
            )

            purchase_id = purchase.pk
            i = 0
            total_of_totals = 0

            purchase_items = []

            history = SupplierPurchasesHistory.objects.filter(supplier_id=supplier_id)

            # Iterate through each product and save PurchasesItems record
            for prod in data.getlist('product_id[]'):
                product = Products.objects.get(id=prod)
                qty = int(data.getlist('qty[]')[i])
                tendered_price = float(data.getlist('tendered_price[]')[i])
                if qty == 0:
                    raise ValueError(
                        f"Cannot save! Requested quantity ({qty}) can never be zero."
                    )

                price = float(data.getlist('price[]')[i])
                total = qty * tendered_price
                total_of_totals += total

                purchase_item = purchasesItems.objects.create(
                    purchase_id=purchase,
                    product_id=product,
                    qty=qty,
                    price=tendered_price,
                    total=total
                )

                StockMovement.objects.create(
                    product=product,
                    product_name=product.name,
                    supplier_id=supplier_id,
                    buying_price=product.buying_price,
                    selling_price=tendered_price,
                    quantity_in_past=product.quantity,
                    quantity_in_stock=product.quantity + qty,
                    quantity_purchased=qty,
                    user=request.user
                )

                # # Update product quantity
                # product.quantity += qty
                # product.save()
                i += 1

                # Append item details to purchase_items list
                purchase_items.append({
                    'product': product.name,
                    'qty': qty,
                    'price': tendered_price,
                    'subtotal': total
                })

            # if has a loan, create history
            if payment_method == '0002':
                if supplier_id:
                    if float(data['advance_amount']) > 0.0:
                        if 1.0 < float(data['advance_amount']) <= total:
                            print(
                                f"hereeeee1 : {data['advance_amount']} and {total}  and {total - float(data['advance_amount'])}")
                            PurchasesDuePaymentHistory.objects.create(
                                purchase_id=purchase,
                                initial_loan=total_of_totals,
                                paid_amount=float(data['advance_amount']),
                                total_paid_amount=float(data['advance_amount']),
                                disbursed_amount=(total_of_totals - float(data['advance_amount'])),
                                user=request.user
                            )
                            SupplierPurchasesHistory.objects.create(
                                supplier_id=supplier_id,
                                code=generate_unique_code(),
                                purchase_id=purchase,
                                payment_method=method,
                                initial_loan_amount=total_of_totals,
                                paid_amount=float(data['advance_amount']),
                                total_paid_amount=(float(data['advance_amount']) + sum(a.paid_amount for a in history)),
                                balance=(((history.last().balance if history else 0) + total_of_totals) - float(
                                    data['advance_amount'])),
                                user=request.user
                            )
                        elif float(data['advance_amount']) > total:
                            resp[
                                'msg'] = f"This is not a DUe.. Makesure the advanced amount is not greater than the order amount (Tendered Amount)"
                            return HttpResponse(json.dumps(resp), content_type="application/json")

                    else:
                        PurchasesDuePaymentHistory.objects.create(
                            purchase_id=purchase,
                            initial_loan=total_of_totals,
                            paid_amount=0,
                            total_paid_amount=0,
                            disbursed_amount=total_of_totals,
                            user=request.user
                        )
                        SupplierPurchasesHistory.objects.create(
                            supplier_id=supplier_id,
                            code=generate_unique_code(),
                            purchase_id=purchase,
                            initial_loan_amount=total_of_totals,
                            payment_method=method,
                            paid_amount=0,
                            total_paid_amount=sum(a.paid_amount for a in history),
                            balance=((history.last().balance if history else 0) + total_of_totals),
                            user=request.user
                        )
                else:
                    resp['msg'] = f"Please select Supplier first"
                    return HttpResponse(json.dumps(resp), content_type="application/json")
            else:
                # if has no loan, create history
                SupplierPurchasesHistory.objects.create(
                    supplier_id=supplier_id,
                    code=generate_unique_code(),
                    purchase_id=purchase,
                    initial_loan_amount=0,
                    payment_method=method,
                    paid_amount=total_of_totals,
                    total_paid_amount=total_of_totals if not history else sum(a.paid_amount for a in history),
                    balance=(((history.last().balance if history else 0) + total_of_totals) - total_of_totals),
                    user=request.user
                )
            resp['status'] = 'success'
            resp['purchase_id'] = purchase_id
            resp['data'] = {
                'orderNumber': code,
                'orderDate': purchase.date_added.strftime("%Y-%m-%d"),
                'servedBy': request.user.username,
                'supplierName': supplier.name,
                'items': purchase_items,
                'totalItems': len(purchase_items),
                'subtotal': purchase.sub_total,
                'total': purchase.grand_total,
                'totalPaid': purchase.grand_total
            }
            messages.success(request, "Purchase Record has been saved.")

    except Products.DoesNotExist:
        resp['msg'] = "One of the products does not exist."
        print("Product does not exist.")
    except Exception as e:
        resp['msg'] = f"An error occurred: {e}"
        print("Unexpected error:", e)

    last_check = SupplierPurchasesHistory.objects.filter(supplier_id=supplier_id).last()
    if last_check:
        if last_check.balance > 0:
            Supplier.objects.filter(id=supplier_id).update(has_loan=True)
        else:
            Supplier.objects.filter(id=supplier_id).update(has_loan=False)
    return JsonResponse(resp)


@login_required
@admin_required
def manage_purchase(request):
    item = None
    products = []
    data = request.GET
    purchase_id = None

    if request.method == 'GET':
        id = data.get('id', '0')
        add_item = data.get('add_item', '0')
        if add_item == '1':
            products = Products.objects.all()
            purchase_id = id
        else:
            if id.isnumeric() and int(id) > 0:
                item = purchasesItems.objects.filter(id=id).first()

    print(purchase_id)
    context = {
        'products': products,
        'item': item,
        'purchase_id': purchase_id
    }

    return render(request, 'posApp/manage_purchase_items.html', context)


@login_required
def save_custom_proforma(request):
    resp = {'status': 'failed', 'msg': ''}
    data = request.POST

    try:
        with transaction.atomic():

            customer_id = request.POST.get('customer')
            print(f"find {customer_id}")
            if not customer_id:
                raise ValueError(
                    f"Please select customer. Can't make a proforma to someone you don't know"
                )

            pref = str(datetime.now().year)  # Simplified the prefix
            i = 1

            # Generate a unique proforma code
            while True:
                code = '{:0>5}'.format(i)
                i += 1
                if not CustomProforma.objects.filter(code=str(pref) + str(code)).exists():
                    break
            code = str(pref) + str(code)

            # Save Purchase record
            proforma = CustomProforma.objects.create(
                code=code,
                customer_id=customer_id,
                sub_total=data['sub_total'],
                grand_total=data['grand_total'],
                user=request.user
            )
            print(f"proforma : {customer_id}")
            i = 0
            total_of_totals = 0

            proforma_items = []

            # Iterate through each product and save PurchasesItems record
            for prod in data.getlist('product_id[]'):
                product = Products.objects.get(id=prod)
                qty = int(data.getlist('qty[]')[i])
                tendered_price = float(data.getlist('tendered_price[]')[i])
                if qty == 0:
                    raise ValueError(
                        f"Cannot save! Requested quantity ({qty}) can never be zero."
                    )

                price = float(data.getlist('price[]')[i])
                total = qty * tendered_price
                total_of_totals += total

                proforma_item = CustomProformaItems.objects.create(
                    proforma_id=proforma,
                    product_id=product,
                    qty=qty,
                    price=tendered_price,
                    total=total
                )
                i += 1
                # Append item details to purchase_items list
                proforma_items.append({
                    'product': product.name,
                    'qty': qty,
                    'price': tendered_price,
                    'subtotal': total
                })
            resp['status'] = 'success'
            resp['proforma_id'] = proforma.pk
            resp['data'] = {
                'orderDate': proforma.date_added.strftime("%Y-%m-%d"),
                'servedBy': request.user.username,
                'items': proforma_items,
                'totalItems': len(proforma_items),
                'total': data['grand_total'],
            }
            messages.success(request, "Proforma Record has been saved.")

    except Products.DoesNotExist:
        resp['msg'] = "One of the products does not exist."
        print("Product does not exist.")
    except Exception as e:
        resp['msg'] = f"An error occurred: {e}"
        print("Unexpected error:", e)

    return JsonResponse(resp)


@login_required
@permission_required('posApp.view_purchases', raise_exception=True)
def purchasesList(request):
    query = request.GET.get('q')
    # Get the status filter from the request (defaults to None)
    status_filter = request.GET.get('status')
    per_page = request.GET.get('per_page', 100)  # Default to 20 items per page if not specified
    supplier = {}

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 50  # Fallback to 20 if conversion fails

    if query:
        purchases = Purchases.objects.filter(
            Q(id__icontains=query) |
            Q(supplier__name__contains=query)
            # Q(code__icontains=query) |
            # Q(date_added__icontains=query) |
            # Q(date_updated__icontains=query)
        )
    else:
        purchases = Purchases.objects.all()

    # Apply filter if a specific status is selected
    if status_filter is not None and status_filter != '':
        purchases = purchases.filter(status=status_filter)

    paginator = Paginator(purchases.order_by('-date_added'), per_page)
    page = request.GET.get('page')

    try:
        purchases_page = paginator.page(page)
    except PageNotAnInteger:
        purchases_page = paginator.page(1)
    except EmptyPage:
        purchases_page = paginator.page(paginator.num_pages)

    purchases_data = []
    for purchase in purchases_page:
        print(f"pyee : {purchase.payment_method}")
        data = {}
        for field in purchase._meta.get_fields(include_parents=False):
            if field.related_model is None:
                data[field.name] = getattr(purchase, field.name)
        data['items'] = purchasesItems.objects.filter(purchase_id=purchase).all()
        data['payment_method'] = purchase.payment_method
        data['item_count'] = sum(q.qty for q in data['items'])
        data['supplier'] = purchase.supplier
        purchases_data.append(data)

        # Calculate the range of entries being displayed
    start_index = (purchases_page.number - 1) * per_page + 1
    end_index = min(purchases_page.number * per_page, paginator.count)

    context = {
        'page_title': 'Purchases Transactions',
        'purchase_data': purchases_data,
        'purchases': purchases_page,  # Add the paginated sales
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/purchases.html', context)


@login_required
@admin_required
def remove_item_in_purchase(request):
    if request.method == "POST":
        data = request.POST
        resp = {'status': ''}
        try:
            with transaction.atomic():
                purchase_item_id = data.get('id')
                purchase_item = purchasesItems.objects.get(id=purchase_item_id)
                purchase = Purchases.objects.get(id=purchase_item.purchase_id_id)
                all_items_in_purchase = purchasesItems.objects.filter(purchase_id=purchase).all()

                if len(all_items_in_purchase) <= 1:
                    purchase.delete()
                    messages.success(request, 'Item successfully removed.')
                    resp['status'] = 'success'
                    # resp['redirect'] = 'purchases-page'
                else:
                    purchase_item.delete()
                    messages.success(request, 'Item successfully removed.')
                    resp['status'] = 'success'

                    # update purchase
                    total = 0
                    grand_total = 0
                    purchase_new = purchasesItems.objects.filter(purchase_id=purchase).all()
                    for items in purchase_new:
                        grand_total += (items.price * items.qty)
                        total += items.total
                    purchase.grand_total = grand_total
                    purchase.tendered_amount = total
                    purchase.sub_total = total
                    purchase.save()
                    # Create History
                if purchase:
                    if purchase.payment_method.code == '0001':
                        SupplierPurchasesHistory.objects.filter(purchase_id=purchase).update(
                            paid_amount=purchase.grand_total,
                        )

                # rudisha store
                product_qts = purchase_item.product_id.quantity
                reversed_products_qty = product_qts - purchase_item.qty
                purchase_item.product_id.quantity = reversed_products_qty
                purchase_item.product_id.save()

                # Get the StockMovementHistory record for the product and date
                update_stock_movement_on_unapprove(purchase_item, 1)  # 1 for purchase item
        except salesItems.DoesNotExist:
            logger.error(f'Item with id {purchase_item_id} does not exist')
            resp['status'] = 'failed'
            resp['msg'] = 'Purchase item not found.'
        except Sales.DoesNotExist:
            logger.error(f'purchase with id {purchase_item.purchase_id_id} does not exist')
            resp['status'] = 'failed'
            resp['msg'] = 'Purchase not found.'
        except Exception as e:
            logger.error(f'Error removing item from sale: {e}')
            resp['status'] = 'failed'
            resp['msg'] = str(e)
        return JsonResponse(resp)
    else:
        return JsonResponse({'status': 'failed', 'msg': 'Invalid request method.'})


@login_required
@permission_required('posApp.view_purchases', raise_exception=True)
def proformasList(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified
    customer = {}

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    if query:
        proformas = CustomProforma.objects.filter(
            Q(id__icontains=query) |
            Q(customer__name__contains=query) |
            Q(code__icontains=query) |
            Q(date_added__icontains=query) |
            Q(date_updated__icontains=query)
        ).order_by('-date_added')
    else:
        proformas = CustomProforma.objects.all().order_by('-date_added')

    paginator = Paginator(proformas, per_page)
    page = request.GET.get('page')

    try:
        proformas_page = paginator.page(page)
    except PageNotAnInteger:
        proformas_page = paginator.page(1)
    except EmptyPage:
        proformas_page = paginator.page(paginator.num_pages)

    proformas_data = []
    for proforma in proformas_page:
        data = {}
        for field in proforma._meta.get_fields(include_parents=False):
            if field.related_model is None:
                data[field.name] = getattr(proforma, field.name)
        data['items'] = CustomProformaItems.objects.filter(proforma_id=proforma).all()
        data['item_count'] = len(data['items'])
        data['customer'] = proforma.customer
        proformas_data.append(data)

        # Calculate the range of entries being displayed
    start_index = (proformas_page.number - 1) * per_page + 1
    end_index = min(proformas_page.number * per_page, paginator.count)
    print(f" prof : {proformas_data}")
    context = {
        'page_title': 'Stock MOVEMENTS',
        'proformas_data': proformas_data,
        'proformas': proformas_page,  # Add the paginated sales
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/proformas-page.html', context)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def viewProformaProducts(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    proforma_id = request.GET.get('id')

    print(f'proforma : {proforma_id}')

    # Get the Sale object if it exists, otherwise return 404
    proforma = get_object_or_404(CustomProforma, id=proforma_id)

    items = CustomProformaItems.objects.filter(proforma_id=proforma).filter(
        Q(proforma_id__code__icontains=query) |
        Q(proforma_id__customer__name__icontains=query) | Q(proforma_id__name__icontains=query)
    ).select_related('product_id') if query else CustomProformaItems.objects.filter(
        proforma_id=proforma).select_related('product_id')

    # Calculate overall total for each product
    product_totals = sum(item.total for item in items)

    paginator = Paginator(items, per_page)
    page = request.GET.get('page')

    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (items_page.number - 1) * per_page + 1
    end_index = min(items_page.number * per_page, paginator.count)
    context = {
        'proforma': proforma,
        'items': items_page,
        'product_totals': product_totals,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/view_custom_proformer_products.html', context)


@login_required
@permission_required('posApp.delete_purchases', raise_exception=True)
def delete_purchase(request):
    resp = {'status': 'failed', 'msg': ''}
    id = request.POST.get('id')
    try:
        with transaction.atomic():
            purchase = Purchases.objects.get(id=id)
            purchase_items = purchasesItems.objects.filter(purchase_id=purchase)
            if purchase_items.exists():
                if purchase.status == 1:
                    for purchase_item in purchase_items:
                        print(f"sale_item : {purchase_item.product_id.name}")
                        print(f"sale_item_qty : {purchase_item.qty}")

                        product_qts = purchase_item.product_id.quantity
                        print(f"product_qts : {product_qts}")

                        reversed_products_qty = product_qts - purchase_item.qty
                        print(f"reversed_products_qty : {reversed_products_qty}")

                        purchase_item.product_id.quantity = reversed_products_qty
                        purchase_item.product_id.save()

                        # Get the StockMovementHistory record for the product and date
                        update_stock_movement_on_unapprove(purchase_item, 1)  # 1 for purchase item

                purchase.delete()
            else:
                resp['status'] = 'success'
                resp['msg'] = "Error : That purchase is no longer exist"

            resp['status'] = 'success'
            messages.success(request, 'Purchase Record has been deleted.')

    except:
        resp['msg'] = "An error occured"
        print("Unexpected error:", sys.exc_info()[0])
    return HttpResponse(json.dumps(resp), content_type='application/json')


@require_http_methods(["GET"])
def get_purchase_status(request):
    purchase_id = request.GET.get('id')
    try:
        purchase = Purchases.objects.get(pk=purchase_id)
        response = {
            'status': purchase.status,
        }
        return JsonResponse(response)
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Purchase not found'})


@login_required
@permission_required('posApp.view_purchases', raise_exception=True)
def viewPurchasedProducts(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 100)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 50  # Fallback to 20 if conversion fails

    purchase_id = request.GET.get('id')

    print(f'sale : {purchase_id}')

    # Get the Purchase object if it exists, otherwise return 404
    purchase = get_object_or_404(Purchases, id=purchase_id)

    items = purchasesItems.objects.filter(purchase_id=purchase).filter(Q(product_id__name__icontains=query)
                                                                       ).select_related(
        'product_id') if query else purchasesItems.objects.filter(purchase_id=purchase).select_related(
        'product_id')

    total_due_payment_history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase)
    overall_total_paid_amount = sum(ff.paid_amount for ff in total_due_payment_history)
    due_payment_history = total_due_payment_history.first()
    # Calculate overall total for each product
    product_totals = sum(item.total for item in items)
    total_item_quantity = sum(q.qty for q in items)
    new_disbursement = 0
    # if purchase.loan_status == 1:
    #     new_disbursement = total_due_payment_history.last().outstanding_amount

    paginator = Paginator(items, per_page)
    page = request.GET.get('page')

    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (items_page.number - 1) * per_page + 1
    end_index = min(items_page.number * per_page, paginator.count)

    context = {
        'purchase': purchase,
        'items': items_page,
        "item_counts": total_item_quantity,
        'histories': due_payment_history,
        'overall_total': overall_total_paid_amount,
        'new_disbursement': new_disbursement,
        'product_totals': product_totals,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/view_purchase_products.html', context)


@require_http_methods(["POST"])
def process_purchase_payment(request):
    purchase_id = request.POST.get('id')
    try:
        purchase = Purchases.objects.get(pk=purchase_id)
        items = purchasesItems.objects.filter(purchase_id_id=purchase_id)
        for item in items:
            Products.objects.filter(id=item.product_id.pk).update(
                quantity=item.product_id.quantity + item.qty,
                total_pieces=((
                                      item.product_id.quantity + item.qty) * item.product_id.max_pieces) + item.product_id.left_pieces
            )
            update_stock_movement(item.product_id.id, item.purchase_id.date_added.date())
        purchase.status = 1  # Update status to 'Success' or other appropriate status
        purchase.save()
        messages.success(request, f'Approved successfully')
        return JsonResponse({'status': 'success', 'message': 'Payment confirmed successfully!'})
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Purchase not found'})


@require_http_methods(["POST"])
def unapprove_purchase(request):
    purchase_id = request.POST.get('id')
    try:
        purchase = Purchases.objects.get(pk=purchase_id)
        items = purchasesItems.objects.filter(purchase_id_id=purchase_id)
        for item in items:
            Products.objects.filter(id=item.product_id.pk).update(
                quantity=item.product_id.quantity - item.qty,
                total_pieces=((
                                      item.product_id.quantity - item.qty) * item.product_id.max_pieces) - item.product_id.left_pieces
            )
            update_stock_movement_on_unapprove(item, 1)  # 1 for purchase item
        purchase.status = 0  # Update status to 'Rejected' or other appropriate status
        purchase.save()
        messages.success(request, f'Unpproved successfully')
        return JsonResponse({'status': 'success', 'message': 'Payment Unapproved successfully!'})
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Purchase not found'})


@require_http_methods(["POST"])
def reject_purchase_payment(request):
    purchase_id = request.POST.get('id')
    try:
        purchase = Purchases.objects.get(pk=purchase_id)
        purchase.status = 2  # Update status to 'Rejected' or other appropriate status
        purchase.save()
        return JsonResponse({'status': 'success', 'message': 'Payment rejected successfully!'})
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Purchase not found'})


@login_required
def create_purchase_invoice(request):
    id = request.GET.get('id')
    purchases = Purchases.objects.filter(id=id).first()
    transaction = {}
    for field in Purchases._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(purchases, field.name)
    ItemList = purchasesItems.objects.filter(purchase_id=purchases).all()
    context = {
        "purchase": purchases,
        "transaction": transaction,
        "purchasesItems": ItemList
    }

    return render(request, 'posApp/purchases_invoice.html', context)


@login_required
def create_purchase_proforma(request):
    id = request.GET.get('id')
    purchases = Purchases.objects.filter(id=id).first()
    transaction = {}
    for field in Purchases._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(purchases, field.name)
    ItemList = purchasesItems.objects.filter(purchase_id=purchases).all()
    context = {
        "purchase": purchases,
        "transaction": transaction,
        "purchasesItems": ItemList
    }

    return render(request, 'posApp/purchases_proforma.html', context)


@login_required
def create_custom_proforma(request):
    id = request.GET.get('id')
    proformas = CustomProforma.objects.filter(id=id).first()
    transaction = {}
    for field in CustomProforma._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(proformas, field.name)
    ItemList = CustomProformaItems.objects.filter(proforma_id=proformas).all()
    context = {
        "proforma": proformas,
        "transaction": transaction,
        "proformaItems": ItemList
    }

    return render(request, 'posApp/custom_proforma.html', context)


@login_required
@admin_required
def delete_product(request):
    data = request.POST
    resp = {'status': ''}
    try:
        CustomProforma.objects.filter(id=data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Proforma Successfully deleted.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def create_delivery_note(request):
    id = request.GET.get('id')
    purchases = Purchases.objects.filter(id=id).first()
    transaction = {}
    for field in Purchases._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(purchases, field.name)
    ItemList = purchasesItems.objects.filter(purchase_id=purchases).all()
    context = {
        "total_quantity": sum(i.qty for i in ItemList),
        "purchase": purchases,
        "transaction": transaction,
        "purchasesItems": ItemList
    }

    return render(request, 'posApp/purchases_delivery_note.html', context)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def viewSoldProducts(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 100)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 50  # Fallback to 20 if conversion fails

    sale_id = request.GET.get('id')

    print(f'sale : {sale_id}')

    # Get the Sale object if it exists, otherwise return 404
    sale = get_object_or_404(Sales, id=sale_id)

    items = salesItems.objects.filter(sale_id=sale).filter(
        Q(product_id__name__icontains=query)
    ).select_related('product_id') if query else salesItems.objects.filter(sale_id=sale).select_related('product_id')
    company = Company.objects.filter(user=request.user).first()
    due_payment_history = DuePaymentHistory.objects.filter(sale_id=sale).first()

    total_due_payment_history = DuePaymentHistory.objects.filter(sale_id=sale)
    overall_total_paid_amount = sum(ff.paid_amount for ff in total_due_payment_history)
    # Calculate overall total for each product
    if company:
        if company.is_direct_pricing_method:
            product_totals = sum(item.total for item in items)
        else:
            product_totals = sum(item.total_tendered_price for item in items)
    else:
        product_totals = sum(item.total_tendered_price for item in items)
    total_item_quantity = sum(q.qty for q in items)
    total_item_pieces = sum(q.pcs for q in items)
    new_disbursement = 0
    # if sale.loan_status == 1:
    # new_disbursement = total_due_payment_history.last().outstanding_amount
    # if total_due_payment_history.count() > 1:  # Angalau hashawahi kulipa, history inaexist
    #     new_disbursement = total_due_payment_history.last().disbursed_amount
    # else:
    #     # new_disbursement = sale.tendered_amount
    #     new_disbursement = total_due_payment_history.last().disbursed_amount

    paginator = Paginator(items, per_page)
    page = request.GET.get('page')

    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (items_page.number - 1) * per_page + 1
    end_index = min(items_page.number * per_page, paginator.count)
    print(new_disbursement)
    context = {
        'sale': sale,
        'items': items_page,
        "item_counts": total_item_quantity,
        "item_pieces_count": total_item_pieces,
        'histories': due_payment_history,
        'overall_total': overall_total_paid_amount,
        'new_disbursement': new_disbursement,
        'product_totals': product_totals,
        'company': company,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/view_sold_products.html', context)


@require_http_methods(["POST"])
def process_payment(request):
    sale_id = request.POST.get('id')
    try:
        with transaction.atomic():
            sale = Sales.objects.get(pk=sale_id)
            items = salesItems.objects.filter(sale_id_id=sale_id)
            for item in items:
                # Calculations for both Boxes and Pieces
                quantity_sold_in_pieces = (item.qty * item.product_id.max_pieces) + item.pcs
                remaining_pieces_in_stock = item.product_id.total_pieces - quantity_sold_in_pieces
                Products.objects.filter(id=item.product_id.pk).update(
                    # quantity=item.product_id.quantity - item.qty,
                    quantity=remaining_pieces_in_stock // item.product_id.max_pieces,
                    left_pieces=remaining_pieces_in_stock % item.product_id.max_pieces,
                    total_pieces=remaining_pieces_in_stock,
                )
                update_stock_movement(item.product_id.id, item.sale_id.date_added.date())
            sale.status = 1  # Update status to 'Success' or other appropriate status
            sale.save()
            messages.success(request, f'Approved successfully')
            return JsonResponse({'status': 'success', 'message': 'Payment confirmed successfully!'})

    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sale not found'})


@require_http_methods(["POST"])
def unapprove_payment(request):
    sale_id = request.POST.get('id')
    try:
        with transaction.atomic():
            sale = Sales.objects.get(pk=sale_id)
            items = salesItems.objects.filter(sale_id_id=sale_id)
            for item in items:
                # Calculations for both Boxes and Pieces
                quantity_sold_in_pieces = (item.qty * item.product_id.max_pieces) + item.pcs
                remaining_pieces_in_stock = item.product_id.total_pieces + quantity_sold_in_pieces
                Products.objects.filter(id=item.product_id.pk).update(
                    # quantity=item.product_id.quantity + item.qty
                    quantity=remaining_pieces_in_stock // item.product_id.max_pieces,
                    left_pieces=remaining_pieces_in_stock % item.product_id.max_pieces,
                    total_pieces=remaining_pieces_in_stock,
                )
                update_stock_movement_on_unapprove(item, 0)  # 1 for sales
            sale.status = 0  # Update status to 'Rejected' or other appropriate status
            sale.save()
            messages.success(request, f'Unpproved successfully')
            return JsonResponse({'status': 'success', 'message': 'Payment Unapproved successfully!'})

    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sale not found'})


@require_http_methods(["POST"])
def reject_payment(request):
    sale_id = request.POST.get('id')
    try:
        sale = Sales.objects.get(pk=sale_id)
        sale.status = 2  # Update status to 'Rejected' or other appropriate status
        sale.save()
        return JsonResponse({'status': 'success', 'message': 'Payment rejected successfully!'})
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sale not found'})


@login_required
@permission_required('posApp.view_order_confirmation', raise_exception=True)
@permission_required('posApp.view_delete_order_button', raise_exception=True)
def loan_repayment(request):
    history = {}
    # categories = Sales.objects.filter(loan_status=1).all()
    sale = {}
    if request.method == 'GET':
        data = request.GET
        id = data.get('id', '')
        if id.isnumeric() and int(id) > 0:
            sale = Sales.objects.filter(id=id).first()
        history = DuePaymentHistory.objects.filter(sale_id=sale)
    context = {
        'sale': sale,
        'history': history,
        'total_paid_loan': sum(hist.paid_amount for hist in history),
        'total_disbursed_amount': history.last()
    }
    return render(request, 'posApp/loan_repayment_modal.html', context)


@login_required
@permission_required('posApp.view_order_confirmation', raise_exception=True)
@permission_required('posApp.view_delete_order_button', raise_exception=True)
def purchases_loan_repayment(request):
    history = {}
    # categories = Sales.objects.filter(loan_status=1).all()
    purchase = {}
    if request.method == 'GET':
        data = request.GET
        id = data.get('id', '')
        if id.isnumeric() and int(id) > 0:
            purchase = Purchases.objects.filter(id=id).first()
        history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase)
    context = {
        'purchase': purchase,
        'history': history,
        'total_paid_loan': sum(hist.paid_amount for hist in history),
        'total_disbursed_amount': history.last()
    }
    return render(request, 'posApp/purchases_loan_repayment_modal.html', context)


@login_required
@permission_required('posApp.view_order_confirmation', raise_exception=True)
@permission_required('posApp.view_delete_order_button', raise_exception=True)
def save_loan_repayment(request):
    data = request.POST
    resp = {'status': 'failed'}
    id = data.get('id', '')
    initial_loan = data.get('initial_loan', '')
    total_paid_amount = data.get('total_paid_amount', '')
    disbursed_amount = data.get('disbursed_amount', '')
    new_pay = data.get('new_pay', 0)

    print(f"data : {data}")

    try:
        with transaction.atomic():
            sale = Sales.objects.get(id=id)
            history = DuePaymentHistory.objects.filter(sale_id=sale)

            # Remove commas from the numeric values
            initial_loan = float(initial_loan.replace(',', ''))
            total_paid_amount = float(total_paid_amount.replace(',', ''))
            disbursed_amount = float(disbursed_amount.replace(',', ''))
            new_pay = float(new_pay.replace(',', ''))
            print(f"data : {disbursed_amount}")

            if new_pay > 50:
                total_paid_loan = sum(hist.paid_amount for hist in history)
                if new_pay >= disbursed_amount:
                    change = disbursed_amount - new_pay
                    rejesho = new_pay + total_paid_loan
                    sale.loan_status = 2
                    sale.status = 1
                    sale.save()
                    DuePaymentHistory.objects.create(sale_id=sale, initial_loan=initial_loan,
                                                     total_paid_amount=rejesho, paid_amount=new_pay,
                                                     disbursed_amount=change, user=request.user)
                    resp['status'] = 'success'
                    messages.success(request, 'Repayment Completed Successfully.')
                if new_pay < disbursed_amount:
                    change = disbursed_amount - new_pay
                    rejesho = new_pay + total_paid_loan
                    sale.loan_status = 1
                    sale.status = 0
                    sale.save()
                    DuePaymentHistory.objects.create(sale_id=sale, initial_loan=initial_loan,
                                                     total_paid_amount=rejesho, paid_amount=new_pay,
                                                     disbursed_amount=change, user=request.user)
                    resp['status'] = 'success'
                    messages.success(request, f'Have Reduced the loan to : {intcomma(change)} TZS')


            else:
                resp['msg'] = "Value can't be less than 50 Tsh."
                resp['status'] = 'failed'
    except Exception as e:
        resp['msg'] = str(e)
        resp['status'] = 'failed'

    return JsonResponse(resp)


@login_required
@permission_required('posApp.view_order_confirmation', raise_exception=True)
@permission_required('posApp.view_delete_order_button', raise_exception=True)
def save_purchases_loan_repayment(request):
    data = request.POST
    resp = {'status': 'failed'}
    id = data.get('id', '')
    initial_loan = data.get('initial_loan', '')
    total_paid_amount = data.get('total_paid_amount', '')
    disbursed_amount = data.get('disbursed_amount', '')
    new_pay = data.get('new_pay', 0)

    print(f"data : {data}")

    try:
        with transaction.atomic():
            purchase = Purchases.objects.get(id=id)
            history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase)

            # Remove commas from the numeric values
            initial_loan = float(initial_loan.replace(',', ''))
            total_paid_amount = float(total_paid_amount.replace(',', ''))
            disbursed_amount = float(disbursed_amount.replace(',', ''))
            new_pay = float(new_pay.replace(',', ''))
            print(f"data : {disbursed_amount}")

            if new_pay > 50:
                total_paid_loan = sum(hist.paid_amount for hist in history)
                if new_pay >= disbursed_amount:
                    change = disbursed_amount - new_pay
                    rejesho = new_pay + total_paid_loan
                    purchase.loan_status = 2
                    purchase.status = 1
                    purchase.save()
                    PurchasesDuePaymentHistory.objects.create(purchase_id=purchase, initial_loan=initial_loan,
                                                              total_paid_amount=rejesho, paid_amount=new_pay,
                                                              disbursed_amount=change, user=request.user)
                    resp['status'] = 'success'
                    messages.success(request, 'Repayment Completed Successfully.')
                if new_pay < disbursed_amount:
                    change = disbursed_amount - new_pay
                    rejesho = new_pay + total_paid_loan
                    purchase.loan_status = 1
                    purchase.status = 0
                    purchase.save()
                    PurchasesDuePaymentHistory.objects.create(purchase_id=purchase, initial_loan=initial_loan,
                                                              total_paid_amount=rejesho, paid_amount=new_pay,
                                                              disbursed_amount=change, user=request.user)
                    resp['status'] = 'success'
                    messages.success(request, f'Have Reduced the loan to : {intcomma(change)} TZS')


            else:
                resp['msg'] = "Value can't be less than 50 Tsh."
                resp['status'] = 'failed'
    except Exception as e:
        resp['msg'] = str(e)
        resp['status'] = 'failed'

    return JsonResponse(resp)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def view_loan_repayment_history(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    sale_id = request.GET.get('id')

    # Get the Sale object if it exists, otherwise return 404
    sale = get_object_or_404(Sales, id=sale_id)

    total_due_payment_history = DuePaymentHistory.objects.filter(sale_id=sale).filter(
        Q(sale_id__code__icontains=query) |
        Q(sale_id__customer__name__icontains=query) | Q(date_added__icontains=query)
    ) if query else DuePaymentHistory.objects.filter(sale_id=sale)

    due_payment_history = DuePaymentHistory.objects.filter(sale_id=sale).first()

    overall_total_paid_amount = sum(ff.paid_amount for ff in total_due_payment_history)
    print(f"here :{overall_total_paid_amount}")
    # Calculate overall total for each product
    new_disbursement = 0
    if sale.loan_status == 1:
        new_disbursement = total_due_payment_history.last().outstanding_amount
        # if total_due_payment_history.count() > 1:  # Angalau hashawahi kulipa, history inaexist
        #     new_disbursement = total_due_payment_history.last().disbursed_amount
        # else:
        #     # new_disbursement = sale.tendered_amount
        #     new_disbursement = total_due_payment_history.last().disbursed_amount

    paginator = Paginator(total_due_payment_history, per_page)
    page = request.GET.get('page')

    try:
        due_payment_history_page = paginator.page(page)
    except PageNotAnInteger:
        due_payment_history_page = paginator.page(1)
    except EmptyPage:
        due_payment_history_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (due_payment_history_page.number - 1) * per_page + 1
    end_index = min(due_payment_history_page.number * per_page, paginator.count)

    context = {
        'sale': sale,
        'due_payment_history_page': due_payment_history_page,
        'histories': due_payment_history,
        'overall_total': overall_total_paid_amount,
        'new_disbursement': new_disbursement,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/view-loan-repayment-history.html', context)


@login_required
@permission_required('posApp.view_purchases', raise_exception=True)
def view_purchases_loan_repayment_history(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    purchase_id = request.GET.get('id')

    # Get the Purchases object if it exists, otherwise return 404
    purchase = get_object_or_404(Purchases, id=purchase_id)

    total_due_payment_history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase).filter(
        Q(purchase_id__code__icontains=query) |
        Q(purchase_id__customer__name__icontains=query) | Q(date_added__icontains=query)
    ) if query else PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase)

    due_payment_history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase).first()

    overall_total_paid_amount = sum(ff.paid_amount for ff in total_due_payment_history)
    print(f"here :{overall_total_paid_amount}")
    # Calculate overall total for each product
    new_disbursement = 0
    if purchase.loan_status == 1:
        new_disbursement = total_due_payment_history.last().outstanding_amount
        # if total_due_payment_history.count() > 1:  # Angalau hashawahi kulipa, history inaexist
        #     new_disbursement = total_due_payment_history.last().disbursed_amount
        # else:
        #     # new_disbursement = sale.tendered_amount
        #     new_disbursement = total_due_payment_history.last().disbursed_amount

    paginator = Paginator(total_due_payment_history, per_page)
    page = request.GET.get('page')

    try:
        due_payment_history_page = paginator.page(page)
    except PageNotAnInteger:
        due_payment_history_page = paginator.page(1)
    except EmptyPage:
        due_payment_history_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (due_payment_history_page.number - 1) * per_page + 1
    end_index = min(due_payment_history_page.number * per_page, paginator.count)

    context = {
        'purchase': purchase,
        'due_payment_history_page': due_payment_history_page,
        'histories': due_payment_history,
        'overall_total': overall_total_paid_amount,
        'new_disbursement': new_disbursement,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/view-purchases-loan-repayment-history.html', context)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def view_customer_sold_history(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 500)

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 300  # Fallback to 20 if conversion fails

    customer_id = request.GET.get('id')

    # Get the Sale object if it exists, otherwise return 404
    customer = get_object_or_404(Customer, id=customer_id)

    company = Company.objects.filter(user=request.user).first()
    if query:
        histories = CustomerSalesHistory.objects.filter(customer_id=customer_id).filter(
            Q(code__icontains=query) |
            Q(sale_id__customer__name__icontains=query) |
            Q(date_added__icontains=query) |
            Q(sale_id__id__icontains=query)
        )
    else:
        histories = CustomerSalesHistory.objects.filter(customer_id=customer_id)
    paginator = Paginator(histories, per_page)
    page = request.GET.get('page')
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (items_page.number - 1) * per_page + 1
    end_index = min(items_page.number * per_page, paginator.count)

    # Initialize balance
    previous_balance = 0
    current_total_sale = 0
    last_balance = 0
    # for history in items_page:
    for history in histories:
        if history.sale_id:
            history.items = salesItems.objects.filter(sale_id=history.sale_id.id)

            # Calculate total items sold
            if company:
                if company.is_direct_pricing_method:
                    history.total_items_sold = history.items.aggregate(total=Sum('total'))['total'] or 0
                else:
                    history.total_items_sold = history.items.aggregate(total=Sum('total_tendered_price'))['total'] or 0
            else:
                history.total_items_sold = history.items.aggregate(total=Sum('total_tendered_price'))['total'] or 0

            # Calculate current balance
            current_total_sale = history.total_items_sold

        if company:
            if company.is_direct_pricing_method:
                current_payment = history.paid_amount
                history.balance = (previous_balance + (current_total_sale if history.sale_id else 0)) - current_payment

                # Update previous balance for the next iteration
                previous_balance = history.balance
                last_balance = previous_balance
            else:
                current_payment = history.tendered_paid_amount
                history.tendered_balance = (previous_balance + (
                    current_total_sale if history.sale_id else 0)) - current_payment

                # Update previous balance for the next iteration
                previous_balance = history.tendered_balance
                last_balance = previous_balance
        else:
            current_payment = history.tendered_paid_amount
            history.tendered_balance = (previous_balance + (
                current_total_sale if history.sale_id else 0)) - current_payment

            # Update previous balance for the next iteration
            previous_balance = history.tendered_balance
            last_balance = previous_balance

    # for history in items_page:
    #     if history.sale_id:
    #         history.items = salesItems.objects.filter(sale_id=history.sale_id.id)
    #         # Calculate total items sold
    #         history.total_items_sold = history.items.aggregate(total=Sum('total'))['total'] or 0
    context = {
        'customer': customer,
        # 'histories': items_page,
        'histories': histories,
        'last_balance': last_balance,
        'is_direct_pricing': True if company and company.is_direct_pricing_method else False,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'reports/view_customer_sales_history.html', context)


@login_required
@permission_required('posApp.view_customer', raise_exception=True)
def export_customers_csv_file(request):
    if request.method == 'GET':
        return csv_populater(request, "posApp", "customer")
    return HttpResponse(json.dumps({'status': 'failed', 'msg': 'Invalid request method'}),
                        content_type="application/json")


@require_http_methods(["GET"])
def get_sale_status(request):
    sale_id = request.GET.get('id')
    try:
        sale = Sales.objects.get(pk=sale_id)
        response = {
            'status': sale.status,
            'loan_status': sale.loan_status
        }
        return JsonResponse(response)
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sale not found'})


@require_http_methods(["GET"])
def get_purchase_status(request):
    id = request.GET.get('id')
    try:
        purchase = Purchases.objects.get(pk=id)
        response = {
            'status': purchase.status,
            'loan_status': purchase.loan_status
        }
        return JsonResponse(response)
    except Sales.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Purchase not found'})


@login_required
@permission_required('posApp.add_sales', raise_exception=True)
@permission_required('posApp.change_sales', raise_exception=True)
def receipt_without_price(request):
    id = request.GET.get('id')
    sales = Sales.objects.filter(id=id).first()
    transaction = {}
    for field in Sales._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(sales, field.name)
    if 'tax_amount' in transaction:
        transaction['tax_amount'] = format(float(transaction['tax_amount']))
    ItemList = salesItems.objects.filter(sale_id=sales).all()
    context = {
        "item_counts": sum(q.qty for q in ItemList),
        "total_price": sum(q.total for q in ItemList),
        "sale": sales,
        "transaction": transaction,
        "salesItems": ItemList
    }

    return render(request, 'posApp/receipt_without_price.html', context)


@login_required
@permission_required('posApp.add_sales', raise_exception=True)
@permission_required('posApp.change_sales', raise_exception=True)
def receipt(request):
    id = request.GET.get('id')
    sales = Sales.objects.filter(id=id).first()
    transaction = {}
    for field in Sales._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(sales, field.name)
    if 'tax_amount' in transaction:
        transaction['tax_amount'] = format(float(transaction['tax_amount']))
    ItemList = salesItems.objects.filter(sale_id=sales).all()
    context = {
        "item_counts": sum(q.qty for q in ItemList),
        "total_price": sum(q.total_tendered_price for q in ItemList),
        "sale": sales,
        "transaction": transaction,
        "salesItems": ItemList
    }

    return render(request, 'posApp/receipt.html', context)


@login_required
@permission_required('posApp.add_purchases', raise_exception=True)
@permission_required('posApp.change_purchases', raise_exception=True)
def purchase_receipt(request):
    id = request.GET.get('id')
    purchases = Purchases.objects.filter(id=id).first()
    transaction = {}
    for field in Purchases._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(purchases, field.name)
    if 'tax_amount' in transaction:
        transaction['tax_amount'] = format(float(transaction['tax_amount']))
    ItemList = purchasesItems.objects.filter(purchase_id=purchases).all()
    context = {
        "purchase": purchases,
        "transaction": transaction,
        "purchaseItems": ItemList
    }

    return render(request, 'posApp/purchase_receipt.html', context)


@login_required
@permission_required('posApp.delete_sales', raise_exception=True)
def delete_sale(request):
    resp = {'status': 'failed', 'msg': ''}
    id = request.POST.get('id')
    try:
        with transaction.atomic():
            sale = Sales.objects.get(id=id)
            sale_items = salesItems.objects.filter(sale_id=sale)
            if sale_items.exists():
                if sale.status == 1:
                    for sale_item in sale_items:
                        print(f"sale_item : {sale_item.product_id.name}")
                        print(f"sale_item_qty : {sale_item.qty}")

                        product_qts = sale_item.product_id.quantity
                        print(f"product_qts : {product_qts}")

                        reversed_products_qty = product_qts + sale_item.qty
                        print(f"reversed_products_qty : {reversed_products_qty}")

                        sale_item.product_id.quantity = reversed_products_qty
                        sale_item.product_id.save()

                        update_stock_movement_on_unapprove(sale_item, 0)  # 0 for sale item

                has_loan = DuePaymentHistory.objects.filter(sale_id=sale)

                if has_loan.exists():
                    has_loan.delete()
                sale.delete()
            else:
                resp['status'] = 'success'
                resp['msg'] = "Error : That sale is no longer exist"

            resp['status'] = 'success'
            messages.success(request, 'Sale Record has been deleted.')

    except:
        resp['msg'] = "An error occured"
        print("Unexpected error:", sys.exc_info()[0])
    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
@permission_required('posApp.view_customer', raise_exception=True)
def customers(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
    ).order_by('-date_added') if query else Customer.objects.all().order_by('-date_added')

    paginator = Paginator(customers, per_page)
    page = request.GET.get('page')

    try:
        customers_page = paginator.page(page)
    except PageNotAnInteger:
        customers_page = paginator.page(1)
    except EmptyPage:
        customers_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (customers_page.number - 1) * per_page + 1
    end_index = min(customers_page.number * per_page, paginator.count)

    context = {
        'page_title': 'Customer List',
        'customers': customers_page,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/customers.html', context)


@login_required
@permission_required('posApp.add_customer', raise_exception=True)
@permission_required('posApp.change_customer', raise_exception=True)
def manage_customer(request):
    customer = {}
    if request.method == 'GET':
        data = request.GET
        customer_id = ''
        if 'id' in data:
            customer_id = data['id']
        if customer_id.isnumeric() and int(customer_id) > 0:
            customer = Customer.objects.filter(id=customer_id).first()

    context = {
        'customer': customer
    }
    return render(request, 'posApp/manage_customer.html', context)


@login_required
def manage_chapchap_customer(request):
    customer = {}
    if request.method == 'GET':
        data = request.GET
        customer_id = ''
        if 'id' in data:
            customer_id = data['id']
        if customer_id.isnumeric() and int(customer_id) > 0:
            customer = Customer.objects.filter(id=customer_id).first()

    context = {
        'customer': customer
    }
    return render(request, 'posApp/manage_chapchap_customer.html', context)


@login_required
@permission_required('posApp.add_customer', raise_exception=True)
@permission_required('posApp.change_customer', raise_exception=True)
def save_customer(request):
    if request.method == "POST":
        customer_id = request.POST.get('id')
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        # Check if a file is uploaded
        if 'file' in request.FILES:
            # If a file is uploaded, call import_csv_files function
            model = Customer  # Specify the model class
            fields = ['name', 'address', 'phone', 'email']  # Specify the fields corresponding to CSV columns
            return import_suppliers_customers_csv_files(request, model, fields)

        # no file attached
        if customer_id and Customer.objects.filter(id=customer_id).exists():
            Customer.objects.filter(id=customer_id).update(name=name, address=address, phone=phone, email=email)
            messages.success(request, 'Customer successfully updated.')
        else:
            Customer.objects.create(name=name, address=address, phone=phone, email=email)
            messages.success(request, 'Customer successfully created.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@permission_required('posApp.delete_customer', raise_exception=True)
def delete_customer(request):
    if request.method == "POST":
        customer_id = request.POST.get('id')
        Customer.objects.filter(id=customer_id).delete()
        messages.success(request, 'Customer successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@permission_required('posApp.view_supplier', raise_exception=True)
def suppliers(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    suppliers = Supplier.objects.filter(
        Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
    ).order_by('-date_added') if query else Supplier.objects.all().order_by('-date_added')

    paginator = Paginator(suppliers, per_page)
    page = request.GET.get('page')

    try:
        suppliers_page = paginator.page(page)
    except PageNotAnInteger:
        suppliers_page = paginator.page(1)
    except EmptyPage:
        suppliers_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (suppliers_page.number - 1) * per_page + 1
    end_index = min(suppliers_page.number * per_page, paginator.count)

    context = {
        'page_title': 'Supplier List',
        'suppliers': suppliers_page,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/suppliers.html', context)


@login_required
@permission_required('posApp.add_supplier', raise_exception=True)
@permission_required('posApp.change_supplier', raise_exception=True)
def manage_supplier(request):
    supplier = {}
    if request.method == 'GET':
        data = request.GET
        supplier_id = ''
        if 'id' in data:
            supplier_id = data['id']
        if supplier_id.isnumeric() and int(supplier_id) > 0:
            supplier = Supplier.objects.filter(id=supplier_id).first()

    context = {
        'supplier': supplier
    }
    return render(request, 'posApp/manage_supplier.html', context)


@login_required
@permission_required('posApp.add_supplier', raise_exception=True)
@permission_required('posApp.change_supplier', raise_exception=True)
def save_supplier(request):
    if request.method == "POST":
        supplier_id = request.POST.get('id')
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        # Check if a file is uploaded
        if 'file' in request.FILES:
            # If a file is uploaded, call import_csv_files function
            model = Supplier  # Specify the model class
            fields = ['name', 'address', 'phone', 'email']  # Specify the fields corresponding to CSV columns
            return import_suppliers_customers_csv_files(request, model, fields)

        # if no file attached
        if supplier_id and Supplier.objects.filter(id=supplier_id).exists():
            Supplier.objects.filter(id=supplier_id).update(name=name, address=address, phone=phone, email=email)
            messages.success(request, 'Supplier successfully updated.')
        else:
            Supplier.objects.create(name=name, address=address, phone=phone, email=email)
            messages.success(request, 'Supplier successfully created.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@permission_required('posApp.delete_supplier', raise_exception=True)
def delete_supplier(request):
    if request.method == "POST":
        supplier_id = request.POST.get('id')
        Supplier.objects.filter(id=supplier_id).delete()
        messages.success(request, 'Supplier successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@permission_required('posApp.view_supplier', raise_exception=True)
def mailing_supplier_modal(request):
    supplier = {}
    if request.method == 'GET':
        data = request.GET
        supplier_id = ''
        if 'id' in data:
            supplier_id = data['id']
        if supplier_id.isnumeric() and int(supplier_id) > 0:
            supplier = Supplier.objects.filter(id=supplier_id).first()

    context = {
        'supplier': supplier
    }
    return render(request, 'posApp/mailing_supplier_modal.html', context)


from django.conf import settings
from django.core.mail import EmailMessage
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Supplier  # Adjust the import according to your project structure
import logging


@login_required
@permission_required('posApp.view_supplier', raise_exception=True)
def send_email_supplier(request):
    if request.method == "POST":
        supplier_id = request.POST.get('id')
        header = request.POST.get('header')
        my_address = request.POST.get('my_address')
        body = request.POST.get('body')
        email = request.POST.get('email')
        attachment = request.FILES.get('attachment')

        if supplier_id and Supplier.objects.filter(id=supplier_id).exists():
            try:
                email_message = EmailMessage(
                    subject=header,
                    body=f"\n{body} \n\nRegards,\n {request.user.first_name} {request.user.last_name}\n {my_address}",
                    from_email=request.user.email,
                    to=[email],
                )

                if attachment:
                    email_message.attach(attachment.name, attachment.read(), attachment.content_type)

                email_message.send(fail_silently=False)
                messages.success(request, 'Supplier email sent successfully.')
                return JsonResponse({'status': 'success'})
            except BadHeaderError as e:
                logging.error(f"Error sending email: {e}")
                messages.error(request, 'Bad header detected. Email not sent.')
                return JsonResponse({'status': 'failed'})
            except Exception as e:
                logging.error(f"Error sending email: {e}")
                messages.error(request, 'Email not sent.')
                return JsonResponse({'status': 'failed'})
        else:
            messages.error(request, 'Supplier does not exist.')
            return JsonResponse({'status': 'failed'})
    return JsonResponse({'status': 'failed'})


# @login_required
# @permission_required('posApp.view_sales', raise_exception=True)
# def viewSupplierPurchasedProducts(request):
#     query = request.GET.get('q')
#     per_page = request.GET.get('per_page', 10)
#
#     try:
#         per_page = int(per_page)
#     except ValueError:
#         per_page = 10  # Fallback to 20 if conversion fails
#
#     supplier_id = request.GET.get('id')
#
#     print(f'supplier : {supplier_id}')
#
#     # Get the Sale object if it exists, otherwise return 404
#     supplier = get_object_or_404(Supplier, id=supplier_id)
#
#     if query:
#         purchases = Purchases.objects.filter(supplier=supplier).filter(
#             Q(id__icontains=query) |
#             Q(supplier__name__icontains=query) |
#             Q(date_added__icontains=query) |
#             Q(grand_total__icontains=query)
#         )
#         # .order_by('-date_added')
#     else:
#         purchases = Purchases.objects.filter(supplier=supplier)
#         # .order_by('-date_added')
#
#     paginator = Paginator(purchases, per_page)
#     page = request.GET.get('page')
#     try:
#         items_page = paginator.page(page)
#     except PageNotAnInteger:
#         items_page = paginator.page(1)
#     except EmptyPage:
#         items_page = paginator.page(paginator.num_pages)
#
#     # Calculate the range of entries being displayed
#     start_index = (items_page.number - 1) * per_page + 1
#     end_index = min(items_page.number * per_page, paginator.count)
#
#     # Initialize cumulative balance
#     cumulative_balance = 0
#
#     for purchase in items_page:
#         # Fetch loan repayment history and items for the current purchase
#         purchase.loan_repayment_history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase.id)
#         purchase.items = purchasesItems.objects.filter(purchase_id=purchase.id)
#
#         # Calculate total items sold
#         purchase.total_items_sold = purchase.items.aggregate(total=Sum('total'))['total'] or 0
#
#         # Total loan paid
#         purchase.total_loan_paid = sum(t.paid_amount for t in purchase.loan_repayment_history)
#
#         # Calculate balance for the current purchase
#         purchase.balance = purchase.total_items_sold - purchase.total_loan_paid
#
#         # Update cumulative balance
#         cumulative_balance += purchase.balance
#
#         # Set the total balance for the current purchase
#         purchase.total_balance = cumulative_balance
#     loan_outstanding_data = []
#     data = {}
#     total_outstands = 0
#     total_price = 0
#     for purchase in purchases:
#         items = purchasesItems.objects.filter(purchase_id=purchase)
#         total_price += sum(it.total for it in items)
#         payment_history = PurchasesDuePaymentHistory.objects.filter(purchase_id=purchase)
#         if payment_history:
#             total_outstands += payment_history.last().disbursed_amount
#
#         # for j in payment_history:
#         #     print(payment_history.disbursed_amount.last())
#         #     tt+=j.disbursed_amount
#         data['payment_history'] = payment_history
#         loan_outstanding_data.append(data)
#
#     context = {
#         'overall_total_price': total_price,
#         'overall_total_outstanding': total_outstands,
#         'supplier': supplier,
#         'purchases': items_page,
#         'per_page': per_page,
#         'start_index': start_index,
#         'end_index': end_index,
#         'total_entries': paginator.count,
#     }
#
#     return render(request, 'posApp/view_supplier_purchases_history.html', context)


@login_required
@permission_required('posApp.view_sales', raise_exception=True)
def viewSupplierPurchasedProducts(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 500)

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 300  # Fallback to 20 if conversion fails

    supplier_id = request.GET.get('id')

    print(f'supplier : {supplier_id}')

    # Get the Sale object if it exists, otherwise return 404
    supplier = get_object_or_404(Supplier, id=supplier_id)
    print(query)

    if query:
        histories = SupplierPurchasesHistory.objects.filter(supplier_id=supplier).filter(
            Q(code__icontains=query) |
            Q(purchase_id__supplier__name__icontains=query) |
            Q(date_added__icontains=query) |
            Q(purchase_id__id__icontains=query) |
            Q(supplier__purchases__car_number=query)
        )
    else:
        histories = SupplierPurchasesHistory.objects.filter(supplier_id=supplier)
    paginator = Paginator(histories, per_page)
    page = request.GET.get('page')
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (items_page.number - 1) * per_page + 1
    end_index = min(items_page.number * per_page, paginator.count)

    # Initialize balance
    previous_balance = 0
    current_total_purchase = 0
    last_balance = 0
    # for history in items_page:
    for history in histories:
        if history.purchase_id:
            history.items = purchasesItems.objects.filter(purchase_id=history.purchase_id.id)
            # Calculate total items sold
            history.total_items_sold = history.items.aggregate(total=Sum('total'))['total'] or 0
            # Calculate current balance
            current_total_purchase = history.total_items_sold

        current_payment = history.paid_amount
        history.balance = (previous_balance + (current_total_purchase if history.purchase_id else 0)) - current_payment

        # Update previous balance for the next iteration
        previous_balance = history.balance
        last_balance = previous_balance

    # for history in items_page:
    #     if history.purchase_id:
    #         history.items = purchasesItems.objects.filter(purchase_id=history.purchase_id.id)
    #         # Calculate total items sold
    #         history.total_items_sold = history.items.aggregate(total=Sum('total'))['total'] or 0
    context = {
        'supplier': supplier,
        # 'histories': items_page,
        'histories': histories,
        'last_balance': last_balance,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }

    return render(request, 'reports/view_supplier_purchases_history.html', context)


@login_required
@permission_required('posApp.view_supplier', raise_exception=True)
def export_suppliers_csv_file(request):
    if request.method == 'GET':
        return csv_populater(request, "posApp", "supplier")
    return HttpResponse(json.dumps({'status': 'failed', 'msg': 'Invalid request method'}),
                        content_type="application/json")


# Empolyees
@login_required
@permission_required('posApp.view_employees', raise_exception=True)
def employees(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    employees = User.objects.filter(
        Q(username__icontains=query)
        | Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
    ).order_by('-date_joined') if query else User.objects.all().order_by('-date_joined')

    paginator = Paginator(employees, per_page)
    page = request.GET.get('page')

    try:
        employees_page = paginator.page(page)
    except PageNotAnInteger:
        employees_page = paginator.page(1)
    except EmptyPage:
        employees_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (employees_page.number - 1) * per_page + 1
    end_index = min(employees_page.number * per_page, paginator.count)

    context = {
        'page_title': 'Employees List',
        'users': employees_page,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/employees.html', context)


@login_required
@permission_required('posApp.add_employees', raise_exception=True)
@permission_required('posApp.change_employees', raise_exception=True)
@admin_required
def manage_employee(request):
    employee = {}
    groups = Group.objects.all()  # Retrieve all groups from the database

    if request.method == 'GET':
        data = request.GET
        employee_id = ''
        if 'id' in data:
            employee_id = data['id']
        if employee_id.isnumeric() and int(employee_id) > 0:
            employee = User.objects.filter(id=employee_id).first()

    context = {
        'user': employee,
        'groups': groups  # Pass the groups to the context
    }
    return render(request, 'posApp/manage_employee.html', context)


@login_required
@permission_required('posApp.add_employees', raise_exception=True)
@permission_required('posApp.change_employees', raise_exception=True)
def save_employee(request):
    if request.method == "POST":
        employee_id = request.POST.get('id')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        passwd = request.POST.get('password')
        group_id = request.POST.get('group')
        is_staff = request.POST.get('is_staff') == 'on'  # Convert checkbox value to boolean
        is_active = request.POST.get('is_active') == 'on'  # Convert checkbox value to boolean

        if passwd:
            password = make_password(passwd)
            if employee_id and User.objects.filter(id=employee_id).exists():
                user = User.objects.get(id=employee_id)
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.password = password
                user.is_staff = is_staff  # Update is_staff field
                user.is_active = is_active  # Update is_active field
                user.save()
                if group_id:
                    group = Group.objects.get(id=group_id)
                    user.groups.set([group])
                messages.success(request, 'Employee successfully updated.')
            else:
                user = User.objects.create(username=username, first_name=first_name, is_active=True,
                                           last_name=last_name,
                                           email=email, password=password)
                user.is_staff = is_staff  # Set is_staff field
                if group_id:
                    group = Group.objects.get(id=group_id)
                    user.groups.set([group])
                messages.success(request, 'Employee successfully created.')
        else:
            if employee_id and User.objects.filter(id=employee_id).exists():
                user = User.objects.get(id=employee_id)
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.is_staff = is_staff  # Update is_staff field
                user.is_active = is_active  # Update is_active field
                user.save()
                if group_id:
                    group = Group.objects.get(id=group_id)
                    user.groups.set([group])
                messages.success(request, 'Employee successfully updated.')
            else:
                messages.error(request, 'Password Field is required.')
                return JsonResponse({'status': 'failed'})

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@permission_required('posApp.delete_employees', raise_exception=True)
@admin_required
def delete_employee(request):
    if request.method == "POST":
        employee_id = request.POST.get('id')
        User.objects.filter(id=employee_id).delete()
        messages.success(request, 'Employee successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


# User roles
@login_required
@admin_required
def group_list(request):
    query = request.GET.get('q')
    per_page = request.GET.get('per_page', 10)  # Default to 20 items per page if not specified

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10  # Fallback to 20 if conversion fails

    group_list = Group.objects.filter(
        Q(name__icontains=query)
    ) if query else Group.objects.all()

    paginator = Paginator(group_list, per_page)
    page = request.GET.get('page')

    try:
        groups_page = paginator.page(page)
    except PageNotAnInteger:
        groups_page = paginator.page(1)
    except EmptyPage:
        groups_page = paginator.page(paginator.num_pages)

    # Calculate the range of entries being displayed
    start_index = (groups_page.number - 1) * per_page + 1
    end_index = min(groups_page.number * per_page, paginator.count)

    context = {
        'page_title': 'Roles List',
        'groups': groups_page,
        'per_page': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'total_entries': paginator.count,
    }
    return render(request, 'posApp/group_list.html', context)


@login_required
@admin_required
def save_group(request):
    if request.method == "POST":
        group_id = request.POST.get('id')
        name = request.POST.get('name')
        permissions = request.POST.getlist('permissions')

        if group_id and Group.objects.filter(id=group_id).exists():
            group = Group.objects.get(id=group_id)
            group.name = name
            group.save()
            group.permissions.set(permissions)  # Update group permissions
            messages.success(request, 'Role successfully updated.')
        else:
            group = Group.objects.create(name=name)
            group.permissions.set(permissions)  # Set group permissions
            messages.success(request, 'Role successfully created.')

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def manage_group(request):
    group = None
    permissions = Permission.objects.all()
    grouped_permissions = defaultdict(list)

    # Group permissions by their content type (model name)
    for permission in permissions:
        model_name = permission.content_type.model.capitalize()
        grouped_permissions[model_name].append(permission)

    if request.method == 'GET':
        data = request.GET
        group_id = data.get('id', None)
        if group_id and group_id.isdigit():
            group = Group.objects.filter(id=group_id).first()

    context = {
        'group': group,
        'grouped_permissions': dict(grouped_permissions)
    }
    return render(request, 'posApp/manage_group.html', context)


@login_required
@admin_required
def delete_group(request):
    if request.method == "POST":
        group_id = request.POST.get('id')
        Group.objects.filter(id=group_id).delete()
        messages.success(request, 'Role successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
def reports_selection(request):
    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    current_day = now.strftime("%d")
    categories = len(Category.objects.all())
    products = len(Products.objects.all())
    transaction = len(Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    ))
    today_sales = Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    ).all()
    total_sales = sum(today_sales.values_list('grand_total', flat=True))
    context = {
        'page_title': 'Home',
        'categories': categories,
        'products': products,
        'transaction': transaction,
        'total_sales': total_sales,
    }
    return render(request, 'posApp/view_reports_selection.html', context)


@login_required
def sales_report_page(request):
    sales = Sales.objects.all().order_by('-date_added')
    customers = Customer.objects.all().order_by('-date_added')
    employees = User.objects.all().order_by('-date_joined')
    products = Products.objects.all().order_by('-date_added')
    context = {
        'sales': sales,
        'customers': customers,
        'employees': employees,
        'products': products,
    }
    return render(request, 'reports/sales_report.html', context)


@login_required
def sales_report(request):
    # Fetch related objects for filtering options
    customers = Customer.objects.all().order_by('-date_added')
    employees = User.objects.all().order_by('-date_joined')
    products = Products.objects.all().order_by('-date_added')

    # Get filter criteria from the request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    client = request.GET.get('client')
    employee = request.GET.get('employee')
    product = request.GET.get('product')
    last_10_sales = request.GET.get('last_10_sales')

    # By default, aggregate sales data by product
    if not any([product]):
        # Get all sales and apply filters if provided
        sales = Sales.objects.all().order_by('-date_added')
        if from_date:
            sales = sales.filter(date_added__gte=from_date)
        if to_date:
            sales = sales.filter(date_added__lte=to_date)
        if client:
            sales = sales.filter(customer_id=client)
        if employee:
            sales = sales.filter(user_id=employee)

        # Subquery to get the latest date_added for each product
        latest_date_added_subquery = salesItems.objects.filter(
            product_id=OuterRef('product_id'),  # Match by product_id
            sale_id__in=sales  # Only consider the filtered sales
        ).values(
            'product_id'  # Group by product_id
        ).annotate(
            latest_date_added=Max('sale_id__date_added')  # Get the max date_added for each product
        ).values('latest_date_added')

        # Aggregate related SalesItems by product name and include the latest date_added
        sales_items = salesItems.objects.filter(sale_id__in=sales).values(
            'product_id__name'  # Group by product name
        ).annotate(
            total_pcs=Sum('pcs'),  # Aggregate total pcs
            total_quantity=Sum('qty'),  # Aggregate total quantity
            total_sales=Sum('total'),  # Aggregate total sales
            latest_date_added=Subquery(latest_date_added_subquery)  # Annotate with the latest date_added
        ).order_by('-total_sales')

        # Calculate overall total price from the aggregated sales items
        overall_total_price = sum(item['total_sales'] for item in sales_items)

        # Prepare context for the template
        context = {
            'sales': sales_items,
            'overall_total_price': overall_total_price,
            'customers': customers,
            'employees': employees,
            'products': products,
        }

        return render(request, 'reports/sales_report.html', context)
    else:
        # Base query for sales
        sales1 = Sales.objects.all().order_by('-date_added')
        # Apply filters if provided
        if from_date:
            sales1 = sales1.filter(date_added__gte=from_date)
        if to_date:
            sales1 = sales1.filter(date_added__lte=to_date)
        if client:
            sales1 = sales1.filter(customer_id=client)
        if employee:
            sales1 = sales1.filter(user_id=employee)
        if product:
            sales1 = sales1.filter(salesitems__product_id=product)
            sales1 = sales1.annotate(product_name=F('salesitems__product_id__name'),
                                     salesitems_qty=F('salesitems__qty'),
                                     salesitems_pcs=F('salesitems__pcs'),
                                     salesitems_price=F('salesitems__price'),
                                     salesitems_total=F('salesitems__total')
                                     )
        context = {
            'sales_details': sales1,
            'overall_total_price': sum(sale.salesitems_total for sale in sales1),
            'customers': customers,
            'employees': employees,
            'products': products,
        }
        return render(request, 'reports/sales_report.html', context)


@login_required
def purchasesreport(request):
    suppliers = Supplier.objects.all().order_by('-date_added')
    employees = User.objects.all().order_by('-date_joined')
    products = Products.objects.all().order_by('-date_added')

    # Get filter criteria from the request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    client = request.GET.get('client')
    employee = request.GET.get('employee')
    product = request.GET.get('product')
    last_10_purchases = request.GET.get('last_10_purchases')

    # By default, aggregate sales data by product
    if not any([product]):
        # Get all sales and apply filters if provided
        purchases = Purchases.objects.all().order_by('-date_added')
        if from_date:
            purchases = purchases.filter(date_added__gte=from_date)
        if to_date:
            purchases = purchases.filter(date_added__lte=to_date)
        if client:
            purchases = purchases.filter(supplier_id=client)
        if employee:
            purchases = purchases.filter(user_id=employee)

        # Subquery to get the latest date_added for each product
        latest_date_added_subquery = purchasesItems.objects.filter(
            product_id=OuterRef('product_id'),  # Match by product_id
            purchase_id__in=purchases  # Only consider the filtered sales
        ).values(
            'product_id'  # Group by product_id
        ).annotate(
            latest_date_added=Max('purchase_id__date_added')  # Get the max date_added for each product
        ).values('latest_date_added')

        # Aggregate related purchaseItems by product name and include the latest date_added
        purchases_items = purchasesItems.objects.filter(purchase_id__in=purchases).values(
            'product_id__name'  # Group by product name
        ).annotate(
            total_quantity=Sum('qty'),  # Aggregate total quantity
            total_purchases=Sum('total'),  # Aggregate total purchase
            latest_date_added=Subquery(latest_date_added_subquery)  # Annotate with the latest date_added
        ).order_by('-total_purchases')

        # Calculate overall total price from the aggregated purchase items
        overall_total_price = sum(item['total_purchases'] for item in purchases_items)

        # Add sale_id_id to each result
        for item in purchases_items:
            # Find all sale_id_ids related to the current product
            purchase_ids = purchasesItems.objects.filter(
                product_id__name=item['product_id__name'],
                purchase_id__in=purchases
            ).values_list('purchase_id_id', flat=True).distinct()

            # Add sale_ids to the existing item dictionary
            item['purchase_ids'] = list(purchase_ids)

        # Prepare context for the template
        context = {
            'purchases': purchases_items,
            'overall_total_price': overall_total_price,
            'suppliers': suppliers,
            'employees': employees,
            'products': products,
        }

        return render(request, 'reports/purchases_report.html', context)
    else:
        # Base query for sales
        purchases1 = Purchases.objects.all().order_by('-date_added')
        # Apply filters if provided
        if from_date:
            purchases1 = purchases1.filter(date_added__gte=from_date)
        if to_date:
            purchases1 = purchases1.filter(date_added__lte=to_date)
        if client:
            purchases1 = purchases1.filter(supplier_id=client)
        if employee:
            purchases1 = purchases1.filter(user_id=employee)
        if product:
            purchases1 = purchases1.filter(purchasesitems__product_id=product)
            purchases1 = purchases1.annotate(product_name=F('purchasesitems__product_id__name'),
                                             purchasesitems_qty=F('purchasesitems__qty'),
                                             purchasesitems_price=F('purchasesitems__price'),
                                             purchasesitems_total=F('purchasesitems__total')
                                             )
            # purchases1 = purchases1.annotate(purchasesitems_qty=F('purchasesitems__qty'))
        context = {
            'purchases_details': purchases1,
            'overall_total_price': sum(purchase.purchasesitems_total for purchase in purchases1),
            'suppliers': suppliers,
            'employees': employees,
            'products': products,
        }
        return render(request, 'reports/purchases_report.html', context)


# @login_required
# def stocks_report_page(request):
#     query = request.GET.get('q')
#     per_page = request.GET.get('per_page', 100)  # Default to 100 items per page if not specified
#
#     try:
#         per_page = int(per_page)
#     except ValueError:
#         per_page = 50  # Fallback to 50 if conversion fails
#
#     suppliers = Supplier.objects.all().order_by('-name')
#     customers = Customer.objects.all().order_by('-name')
#     employees = User.objects.all().order_by('-date_joined')
#     products = Products.objects.all().order_by('-date_added')
#
#     # Filter parameters from request
#     from_date = request.GET.get('from_date')
#     to_date = request.GET.get('to_date')
#     product_filter = request.GET.get('product')
#
#     # Get all sales and purchases and apply filters if provided
#     sales = Sales.objects.all().order_by('date_added')
#     purchases = Purchases.objects.all().order_by('date_added')
#
#     if from_date:
#         sales = sales.filter(date_added__gte=from_date)
#         purchases = purchases.filter(date_added__gte=from_date)
#
#     if to_date:
#         sales = sales.filter(date_added__lte=to_date)
#         purchases = purchases.filter(date_added__lte=to_date)
#
#     if product_filter:
#         sales = sales.filter(salesitems__product_id=product_filter)
#         purchases = purchases.filter(purchasesitems__product_id=product_filter)
#
#     # Aggregate sales and purchase quantities per day for each product
#     sales_per_day = salesItems.objects.filter(sale_id__in=sales).values('sale_id__date_added', 'product_id__name').annotate(
#         total_sales_qty=Sum('qty')
#     ).order_by('sale_id__date_added')
#
#     purchases_per_day = purchasesItems.objects.filter(purchase_id__in=purchases).values('purchase_id__date_added', 'product_id__name').annotate(
#         total_purchases_qty=Sum('qty')
#     ).order_by('purchase_id__date_added')
#
#     # Merge sales and purchase data by day and product
#     stock_movements = []
#     balance = 0
#     current_day = None
#
#     for product in products:
#         product_sales = sales_per_day.filter(product_id__name=product.name)
#         product_purchases = purchases_per_day.filter(product_id__name=product.name)
#
#         # Collect all dates where sales or purchases happened
#         all_dates = sorted(set([item['sale_id__date_added'] for item in product_sales] + [item['purchase_id__date_added'] for item in product_purchases]))
#
#         for date in all_dates:
#             daily_sales_qty = next((item['total_sales_qty'] for item in product_sales if item['sale_id__date_added'] == date), 0)
#             daily_purchases_qty = next((item['total_purchases_qty'] for item in product_purchases if item['purchase_id__date_added'] == date), 0)
#
#             # Calculate the daily balance (cumulative)
#             balance += daily_purchases_qty - daily_sales_qty
#
#             stock_movements.append({
#                 'product': product.name,
#                 'date': date,
#                 'sales_qty': daily_sales_qty,
#                 'purchases_qty': daily_purchases_qty,
#                 'balance': balance,
#             })
#
#     # Context to pass to the template
#     for i in stock_movements:
#         print(i)
#
#     context = {
#         'suppliers': suppliers,
#         'customers': customers,
#         'employees': employees,
#         'stock_movements': stock_movements,
#         'products': products,
#         'defaultDates': {'start': from_date or '', 'end': to_date or ''},
#         'per_page': per_page,
#     }
#
#     return render(request, 'reports/stock_movement_report.html', context)


@login_required
@login_required
def stock_movement_report(request):
    # Default filter criteria
    default_start_date = datetime.now().replace(day=1)  # First day of the current month
    default_end_date = datetime.now()  # Current date

    # Get filter parameters from request
    from_date = request.GET.get('from_date', default_start_date.strftime('%Y-%m-%d'))
    to_date = request.GET.get('to_date', default_end_date.strftime('%Y-%m-%d'))
    product_id = request.GET.get('product')
    supplier_id = request.GET.get('supplier')
    customer_id = request.GET.get('client')
    employee_id = request.GET.get('employee')
    query = request.GET.get('q')

    # Filter stock movements based on the provided criteria
    stock_movements = StockMovementHistory.objects.filter(date__range=[from_date, to_date]).filter(
        Q(product__name__icontains=query)
    ) if query else StockMovementHistory.objects.filter(date__range=[from_date, to_date])

    if product_id:
        stock_movements = stock_movements.filter(product__id=product_id)
    if supplier_id:
        stock_movements = stock_movements.filter(product__supplier__id=supplier_id)
    if customer_id:
        stock_movements = stock_movements.filter(sales__customer__id=customer_id)
    if employee_id:
        stock_movements = stock_movements.filter(employee__id=employee_id)

    # Calculate totals for each stock movement (example: multiplying quantities)
    for movement in stock_movements:
        movement.initial_pieces = movement.initial_stock_pieces - (movement.initial_stock * movement.product.max_pieces)
        movement.balance_pieces = movement.balance_pieces - (movement.balance * movement.product.max_pieces)

    # Pass data to the template
    context = {
        'stock_movements': stock_movements,
        'total_remained': sum(i.balance for i in stock_movements),
        'products': Products.objects.all(),
        'suppliers': Supplier.objects.all(),
        'customers': Customer.objects.all(),
        'employees': User.objects.all(),
        'defaultDates': {'start': from_date, 'end': to_date},
    }

    return render(request, 'reports/stock_movement_report.html', context)


@login_required
def clear_stock_record(request):
    if request.method == 'DELETE' and request.user.is_staff:
        StockMovement.objects.all().delete()
        return JsonResponse({'status': 'success', 'msg': 'Stock movement records cleared successfully.'})
    else:
        return JsonResponse({'status': 'failed', 'msg': 'Permission denied or invalid request method.'})


# User roles
@login_required
@admin_required
def settings_page(request):
    try:
        companies = Company.objects.all().order_by("-date_added")
        stores = StoreLocations.objects.all().order_by("-date_added")
        payment_method = PaymentMethod.objects.all().order_by("-date_added")
        units = Units.objects.all().order_by("-date_added")
    except Exception as e:
        raise ValueError(f"Error : {e}")

    context = {
        'is_companies_length': len(companies.filter(user=request.user)) > 0,
        'user': request.user,
        'companies': companies,
        'stores': stores,
        'payment_methods': payment_method,
        'units': units,
    }
    return render(request, 'posApp/settings_page.html', context)


@login_required
@admin_required
def manage_paymentmethod_page(request):
    method = {}
    if request.method == 'GET':
        data = request.GET
        method_id = ''
        if 'id' in data:
            method_id = data['id']
        if method_id.isnumeric() and int(method_id) > 0:
            method = PaymentMethod.objects.filter(id=method_id).first()

    context = {
        'code': generate_unique_pm_code(),
        'payment_method': method
    }
    return render(request, 'posApp/manage_paymentmethod.html', context)


def generate_unique_pm_code():
    while True:
        code = f"{random.randint(0, 9999):04}"
        if not PaymentMethod.objects.filter(code=code).exists():
            return code


@login_required
@admin_required
def save_paymentmethod_page(request):
    if request.method == "POST":
        pm_id = request.POST.get('id')
        name = request.POST.get('name')
        code = request.POST.get('code')

        # Check if a file is uploaded
        if 'file' in request.FILES:
            # If a file is uploaded, call import_csv_files function
            model = PaymentMethod  # Specify the model class
            fields = ['code', 'name']  # Specify the fields corresponding to CSV columns
            return import_suppliers_customers_csv_files(request, model, fields)
        # no file attached
        if pm_id.isnumeric() and int(pm_id) > 0:
            check = PaymentMethod.objects.exclude(id=pm_id).filter(code=code).all()
        else:
            check = PaymentMethod.objects.filter(code=code).all()

        if check.exists():
            messages.error(request, 'Payment Method Code Already Exists in the database.')
        else:
            if pm_id and PaymentMethod.objects.filter(id=pm_id).exists():
                PaymentMethod.objects.filter(id=pm_id).update(code=code, name=name)
                messages.success(request, 'Payment Method successfully updated.')
            else:
                PaymentMethod.objects.create(code=code, name=name)
                messages.success(request, 'Payment Method successfully created.')
            return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def delete_payment_method(request):
    if request.method == "POST":
        pm_id = request.POST.get('id')
        PaymentMethod.objects.filter(id=pm_id).delete()
        messages.success(request, 'Payment Method successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def manage_productunit_page(request):
    unit = {}
    if request.method == 'GET':
        data = request.GET
        unit_id = ''
        if 'id' in data:
            unit_id = data['id']
        if unit_id.isnumeric() and int(unit_id) > 0:
            unit = Units.objects.filter(id=unit_id).first()

    context = {
        'unit': unit
    }
    return render(request, 'posApp/manage_product_unit.html', context)


@login_required
@admin_required
def save_productunit_page(request):
    if request.method == "POST":
        pu_id = request.POST.get('id')
        name = request.POST.get('name')

        # Check if a file is uploaded
        if 'file' in request.FILES:
            # If a file is uploaded, call import_csv_files function
            model = Units  # Specify the model class
            fields = ['name']  # Specify the fields corresponding to CSV columns
            return import_suppliers_customers_csv_files(request, model, fields)

        # no file attached
        if pu_id and Units.objects.filter(id=pu_id).exists():
            Units.objects.filter(id=pu_id).update(name=name)
            messages.success(request, 'Unit successfully updated.')
        else:
            Units.objects.create(name=name)
            messages.success(request, 'Unit successfully created.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def delete_product_unit(request):
    if request.method == "POST":
        unit_id = request.POST.get('id')
        Units.objects.filter(id=unit_id).delete()
        messages.success(request, 'Unit successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def manage_company_page(request):
    company = {}
    if request.method == 'GET':
        data = request.GET
        company_id = ''
        if 'id' in data:
            company_id = data['id']
        if company_id.isnumeric() and int(company_id) > 0:
            company = Company.objects.filter(id=company_id).first()

    context = {
        'company': company
    }
    return render(request, 'posApp/manage_company.html', context)


@login_required
@admin_required
def save_company_page(request):
    if request.method == "POST":
        company_id = request.POST.get('id')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        logo = request.FILES.get('logo')
        is_direct_pricing_method = request.POST.get('is_direct_pricing_method') == 'on'  # Convert to boolean
        logo_data = None

        # Check if a file is uploaded
        if logo:
            # Check if the uploaded file is a PNG
            if logo.content_type != 'image/png':
                return JsonResponse({'status': 'failed', 'msg': 'Only PNG format is allowed for the logo.'})

            logo_data = logo.read()

        # Save or update the company information
        if company_id and Company.objects.filter(id=company_id).exists():
            Company.objects.filter(id=company_id).update(
                user=request.user,
                name=name,
                phone=phone,
                email=email,
                address=address,
                logo=logo_data,
                is_direct_pricing_method=is_direct_pricing_method,
                configured=True
            )
            messages.success(request, 'Company successfully updated.')
        else:
            company = Company.objects.filter(name=name).first()
            if company:
                if company.configured:
                    messages.success(request, "Company Can't be created. You already have the settings")
                    return JsonResponse({'status': 'failed'})

            Company.objects.create(
                user=request.user,
                name=name,
                phone=phone,
                email=email,
                address=address,
                logo=logo_data,
                is_direct_pricing_method=is_direct_pricing_method,
                configured=True
            )
            messages.success(request, 'Company successfully created.')

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def delete_company(request):
    if request.method == "POST":
        company_id = request.POST.get('id')
        Company.objects.filter(id=company_id).delete()
        messages.success(request, 'Company successfully deleted.')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'})


@login_required
@admin_required
def manage_purchases_loan(request):
    suppliers = Supplier.objects.all()
    payment_methods = PaymentMethod.objects.all().exclude(code='0002')
    context = {
        'code': generate_unique_code(),
        'payment_methods': payment_methods,
        'suppliers': suppliers
    }
    return render(request, 'posApp/manage_purchases_loan_page.html', context)


@login_required
@admin_required
def save_supplier_loan_repayment(request):
    data = request.POST
    resp = {'status': 'failed'}
    total_paid_amount = data.get('total_paid_amount', '')
    outstanding_amount = data.get('disbursed_amount', '')
    code = data.get('code', 0)
    new_pay = data.get('new_pay', 0)
    supplier_id = data.get('supplier', 0)
    payment_method = data.get('payment_method', 0)

    print(f"data : {data}")

    try:
        with transaction.atomic():
            history = SupplierPurchasesHistory.objects.filter(supplier_id=supplier_id)

            #
            # # Remove commas from the numeric values
            initial_loan = (history.last().initial_loan_amount if history else 0)
            # total_paid_amount = float(total_paid_amount.replace(',', ''))
            new_pay = float(new_pay.replace(',', ''))
            new_balance = (history.last().balance if history else 0) - new_pay
            new_total_paid_amount = (history.last().total_paid_amount if history else 0) + new_pay

            if new_pay > 50:
                SupplierPurchasesHistory.objects.create(code=code, supplier_id=supplier_id,
                                                        initial_loan_amount=initial_loan,
                                                        payment_method_id=payment_method,
                                                        total_paid_amount=new_total_paid_amount, paid_amount=new_pay,
                                                        balance=new_balance, user=request.user)

                histories = SupplierPurchasesHistory.objects.filter(supplier_id=supplier_id)
                # Initialize balance
                previous_balance = 0
                current_total_purchase = 0
                last_balance = 0
                for history in histories:
                    if history.purchase_id:
                        history.items = purchasesItems.objects.filter(purchase_id=history.purchase_id.id)
                        # Calculate total items sold
                        history.total_items_sold = history.items.aggregate(total=Sum('total'))['total'] or 0
                        # Calculate current balance
                        current_total_purchase = history.total_items_sold

                    current_payment = history.paid_amount
                    history.balance = (previous_balance + (
                        current_total_purchase if history.purchase_id else 0)) - current_payment

                    # Update previous balance for the next iteration
                    previous_balance = history.balance
                    last_balance = previous_balance
                if last_balance > 0:
                    Supplier.objects.filter(id=supplier_id).update(has_loan=True)
                else:
                    Supplier.objects.filter(id=supplier_id).update(has_loan=False)
                history_to_update = histories.last()
                history_to_update.balance = last_balance
                history_to_update.save()
                resp['status'] = 'success'
                messages.success(request, 'Repayment Completed Successfully.')
            else:
                resp['msg'] = "Value can't be less than 50 Tsh."
                resp['status'] = 'failed'
    except Exception as e:
        resp['msg'] = str(e)
        resp['status'] = 'failed'

    return JsonResponse(resp)


@login_required
@admin_required
def manage_sales_loan(request):
    customers = Customer.objects.all()
    payment_methods = PaymentMethod.objects.all().exclude(code='0002')
    context = {
        'code': generate_unique_code(),
        'payment_methods': payment_methods,
        'customers': customers
    }
    return render(request, 'posApp/manage_sales_loan_page.html', context)


@login_required
@admin_required
def save_customer_loan_repayment(request):
    data = request.POST
    resp = {'status': 'failed'}
    total_paid_amount = data.get('total_paid_amount', '')
    outstanding_amount = data.get('disbursed_amount', '')
    code = data.get('code', 0)
    new_pay = data.get('new_pay', 0)
    customer_id = data.get('customer', 0)
    payment_method = data.get('payment_method', 0)

    print(f"data : {data}")

    try:
        with transaction.atomic():
            history = CustomerSalesHistory.objects.filter(customer_id=customer_id)
            company = Company.objects.filter(user=request.user).first()
            #
            # # Remove commas from the numeric values
            initial_loan = (history.last().initial_loan_amount if history else 0)
            # total_paid_amount = float(total_paid_amount.replace(',', ''))
            new_pay = float(new_pay.replace(',', ''))
            new_balance = (history.last().balance if history else 0) - new_pay
            new_total_paid_amount = (history.last().total_paid_amount if history else 0) + new_pay

            tendered_initial_loan = (history.last().tendered_initial_loan_amount if history else 0)
            new_tendered_balance = (history.last().tendered_balance if history else 0) - new_pay
            new_tendered_total_paid_amount = (history.last().tendered_total_paid_amount if history else 0) + new_pay

            if new_pay > 50:
                CustomerSalesHistory.objects.create(code=code, customer_id=customer_id,
                                                    initial_loan_amount=initial_loan, payment_method_id=payment_method,
                                                    total_paid_amount=new_total_paid_amount, paid_amount=new_pay,
                                                    balance=new_balance, tendered_balance=new_tendered_balance,
                                                    tendered_paid_amount=new_pay,
                                                    tendered_initial_loan_amount=tendered_initial_loan,
                                                    tendered_total_paid_amount=new_tendered_total_paid_amount,
                                                    user=request.user)
                histories = CustomerSalesHistory.objects.filter(customer_id=customer_id)
                # Initialize balance
                tendered_previous_balance = 0
                tendered_last_balance = 0
                tendered_current_total_sale = 0
                previous_balance = 0
                last_balance = 0
                current_total_sale = 0
                for history in histories:
                    if history.sale_id:
                        history.items = salesItems.objects.filter(sale_id=history.sale_id.id)
                        # Calculate total items sold
                        history.total_items_sold = history.items.aggregate(total=Sum('total_tendered_price'))[
                                                       'total'] or 0
                        # Calculate current balance
                        current_total_sale = history.items.aggregate(total=Sum('total'))[
                                                 'total'] or 0
                        tendered_current_total_sale = history.total_items_sold

                    current_payment = history.paid_amount
                    history.balance = (previous_balance + (
                        current_total_sale if history.sale_id else 0)) - current_payment

                    history.tendered_balance = (tendered_previous_balance + (
                        tendered_current_total_sale if history.sale_id else 0)) - history.tendered_paid_amount

                    # Update previous balance for the next iteration
                    previous_balance = history.balance
                    last_balance = previous_balance

                    tendered_previous_balance = history.tendered_balance
                    tendered_last_balance = tendered_previous_balance
                if (last_balance if (company and company.is_direct_pricing_method) else last_balance) > 0:
                    Customer.objects.filter(id=customer_id).update(has_loan=True)
                else:
                    Customer.objects.filter(id=customer_id).update(has_loan=False)
                history_to_update = histories.last()
                history_to_update.balance = last_balance
                history_to_update.tendered_balance = tendered_last_balance
                history_to_update.save()
                resp['status'] = 'success'
                messages.success(request, 'Repayment Completed Successfully.')
            else:
                resp['msg'] = "Value can't be less than 50 Tsh."
                resp['status'] = 'failed'

    except Exception as e:
        print(f"error : {e}")
        resp['msg'] = str(e)
        resp['status'] = 'failed'

    return JsonResponse(resp)


def manual_backup(request):
    if request.method == 'POST':
        try:
            call_command('backup_database')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            messages.error(request, e, False)
            return JsonResponse({'status': 'fail'})
    return JsonResponse({'status': 'failed'}, status=400)
