from . import views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from .views import CustomLoginView
from .views_api import LoginApi, LogoutApi, products_api, sales_list_api, view_sold_products_api, pos_api, SavePosApi

urlpatterns = [
    # path('redirect-admin', RedirectView.as_view(url="/admin"),name="redirect-admin"),
    path('', views.home, name="home-page"),
    # path('login', auth_views.LoginView.as_view(template_name = 'posApp/login.html',redirect_authenticated_user=True), name="login"),
    path('login', CustomLoginView.as_view(), name="login"),
    path('generate_reset_code', views.generate_reset_code, name="generate-reset-code"),
    path('reset_password', views.reset_password, name="reset-password"),
    path('userlogin', views.login_user, name="login-user"),
    path('set-language/', views.set_language, name='set_language'),
    path('manage_user_profile', views.manage_user_profile, name="manage-user-profile-page"),
    path('update_user_profile', views.update_user_profile, name="update-user-profile"),
    path('logout', views.logoutuser, name="logout"),
    path('category', views.category, name="category-page"),
    path('manage_category', views.manage_category, name="manage_category-page"),
    path('save_category', views.save_category, name="save-category-page"),
    path('delete_category', views.delete_category, name="delete-category"),
    path('products', views.products, name='product-page'),
    path('manage_products', views.manage_products, name="manage_products-page"),
    path('clear-quantities/', views.clear_quantities, name='clear-quantities-url'),
    path('test', views.test, name="test-page"),
    path('save_product', views.save_product, name="save-product-page"),
    path('export_products_csv_file', views.export_products_csv_file, name="export-products-csv-file"),
    path('delete_product', views.delete_product, name="delete-product"),
    path('pos', views.pos, name="pos-page"),
    path('custom_proforma', views.custom_proforma, name="custom-proforma-page"),
    path('checkout-modal', views.checkout_modal, name="checkout-modal"),
    path('save-pos', views.save_pos, name="save-pos"),
    path('manage_pos', views.manage_pos, name="manage_pos_page"),
    path('sales', views.salesList, name="sales-page"),
    path('remove-sales-item', views.remove_item_in_sale, name="remove-product-in-sale"),
    path('loan_repayments_page', views.loan_repayments, name="loan-repayments-page"),
    path('create-sale-invoice', views.create_sale_invoice, name="create-sale-invoice"),
    path('purchase', views.purchase, name="purchase-page"),
    path('save-purchase', views.save_purchase, name="save-purchase"),
    path('manage_purchase', views.manage_purchase, name="manage_purchase_page"),
    path('save-custom-proforma', views.save_custom_proforma, name="save-custom-proforma"),
    path('purchases', views.purchasesList, name="purchases-page"),
    path('remove-purcases-item', views.remove_item_in_purchase, name="remove-product-in-purchase"),
    path('delete_purchase', views.delete_purchase, name="delete-purchase"),
    path('get-purchase-status/', views.get_purchase_status, name='get-purchase-status'),
    path('view-purchase-products/', views.viewPurchasedProducts, name='view-purchased-products'),
    path('process-purchase-payment/', views.process_purchase_payment, name='process-purchase-payment'),
    path('unapprove-payment-purchase/', views.unapprove_purchase, name='unapprove-purchase'),
    path('reject-purchase-payment/', views.reject_purchase_payment, name='reject-purchase-payment'),
    path('create-purchase-invoice', views.create_purchase_invoice, name="create-purchase-invoice"),
    path('proformas', views.proformasList, name="proformas-page"),
    path('view-proforma-products/', views.viewProformaProducts, name='view-proforma-products'),
    path('create-purchase-proforma', views.create_purchase_proforma, name="create-purchase-proforma"),
    path('create-custom-proforma', views.create_custom_proforma, name="create-custom-proforma"),
    path('delete-proforma', views.delete_product, name="delete-proforma"),
    path('create-delivery-note', views.create_delivery_note, name="create-delivery-note"),
    path('process-payment/', views.process_payment, name='process-payment'),
    path('unapprove-payment-sale/', views.unapprove_payment, name='unapprove-sale'),
    path('reject-payment/', views.reject_payment, name='reject-payment'),
    path('loan-payment-modal/', views.loan_repayment, name='loan-repayment-modal'), # Accountant
    path('purchases_loan-payment-modal/', views.purchases_loan_repayment, name='purchases-loan-repayment-modal'),  # Accountant
    path('save-loan-repayment/', views.save_loan_repayment, name='save-loan-repayment-page'),
    path('save-purchases-loan-repayment/', views.save_purchases_loan_repayment, name='save-purchases-loan-repayment-page'),
    path('view-loan-repayment-history/', views.view_loan_repayment_history, name='view-loan-repayment-history'),
    path('view-purchases-loan-repayment-history/', views.view_purchases_loan_repayment_history, name='view-purchases-loan-repayment-history'),
    path('get-sale-status/', views.get_sale_status, name='get-sale-status'),
    path('view-sale-products/', views.viewSoldProducts, name='view-sold-products'),
    path('receipt', views.receipt, name="receipt-modal"),
    path('receipt_without_price', views.receipt_without_price, name="receipt_modal_without_price"),
    path('purchase_receipt', views.purchase_receipt, name="purchases-receipt-modal"),
    path('delete_sale', views.delete_sale, name="delete-sale"),

    # Customers
    path('customers/', views.customers, name='customers-page'),
    path('manage_customer/', views.manage_customer, name='manage-customer-page'),
    path('manage_chap_chap_customer/', views.manage_chapchap_customer, name='manage-chapchap-customer-page'),
    path('save_customer/', views.save_customer, name='save-customer-page'),
    path('delete_customer/', views.delete_customer, name='delete-customer'),
    path('view_customer_sold_history/', views.view_customer_sold_history, name='view-customer-sold-products'),
    path('export_customers_csv_file', views.export_customers_csv_file, name="export-customers-csv-file"),
    # Suppliers
    path('suppliers/', views.suppliers, name='suppliers-page'),
    path('manage_supplier/', views.manage_supplier, name='manage-supplier-page'),
    path('save_supplier/', views.save_supplier, name='save-supplier-page'),
    path('delete_supplier/', views.delete_supplier, name='delete-supplier'),
    path('mailing_supplier_modal/', views.mailing_supplier_modal, name='mailing-supplier-modal'),
    path('send_email_supplier/', views.send_email_supplier, name='send_email_supplier'),
    path('view-supplier-purchased-products/', views.viewSupplierPurchasedProducts,
         name='view-supplier-purchased-products'),
    path('export_suppliers_csv_file', views.export_suppliers_csv_file, name="export-suppliers-csv-file"),
    # Employees
    path('employees/', views.employees, name='employees-page'),
    path('manage_employees/', views.manage_employee, name='manage-employee-page'),
    path('save_employee/', views.save_employee, name='save-employee-page'),
    path('delete_employee/', views.delete_employee, name='delete-employee'),

    # User Roles
    path('groups/', views.group_list, name='group-list'),
    path('manage_groups/', views.manage_group, name='manage-group-page'),
    path('delete_group/', views.delete_group, name='delete-group'),
    path('save_group/', views.save_group, name='save-group-page'),

    # Reports and Dashboards
    path('reports_selection/', views.reports_selection, name='reports-selection-page'),
    path('sales_report_page', views.sales_report_page, name='sales-reports'),
    path('sales-report/', views.sales_report, name='sales-report'),
    path('purchases-report/', views.purchasesreport, name='purchases-report'),
    path('stocks_report_page', views.stock_movement_report, name='stocks-report'),
    path('clear-stockmovement-records/', views.clear_stock_record, name='clear_stock_record'),

    # Settings
    path('settings_page', views.settings_page, name='settings-page'),
    path('manage_paymentmethod_page', views.manage_paymentmethod_page, name='manage-paymentmethod-page'),
    path('save_paymentmethod_page', views.save_paymentmethod_page, name='save-paymentmethod-page'),
    path('delete_payment_method', views.delete_payment_method, name='delete-payment-method'),

    path('manage_productunit_page', views.manage_productunit_page, name='manage-productunit-page'),
    path('save_productunit_page', views.save_productunit_page, name='save-productunit-page'),
    path('delete_product_unit', views.delete_product_unit, name='delete-product-unit'),

    path('manage_company_page', views.manage_company_page, name='manage-company-page'),
    path('save_company_page', views.save_company_page, name='save-company-page'),
    path('delete_company', views.delete_company, name='delete-company'),

    # Credit Or Loan Management
    path('manage_purchases_loan', views.manage_purchases_loan, name="manage_purchases_loan"),
    path('save-supplier-loan-repayment/', views.save_supplier_loan_repayment,
         name='save-supplier-loan-repayment-page'),

    path('manage_sales_loan', views.manage_sales_loan, name="manage_sales_loan"),
    path('save-customer-loan-repayment/', views.save_customer_loan_repayment,
         name='save-customer-loan-repayment-page'),

   # Backup
   path('manual_backup/', views.manual_backup, name='manual_backup'),
]


# For Api's only
urlpatterns += [
    # path('api/register/', RegisterApi.as_view(), name='api-register'),
    path('api/login/', LoginApi.as_view(), name='api-login'),
    path('api/logout/', LogoutApi, name='api-logout'),

    # products
    path('api/products/', products_api, name='api-view-products'),

    # sales
    path('api/manage_pos/', pos_api, name='api-manage-pos'),
    path('api/save_pos/', SavePosApi.as_view(), name='api-save-pos'),
    path('api/sales/', sales_list_api, name='api-view-sales'),
    path('api/sale_items/', view_sold_products_api, name='api-view-sold-products'),
]