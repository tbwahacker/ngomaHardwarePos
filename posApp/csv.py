import csv
import json
import random

from _decimal import Decimal
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponse
from .models import StockMovement, Category, Units


# csv excel data populater
def csv_populater(request, app_name, model_name):
    try:
        # Get the model
        model = apps.get_model(app_label=app_name, model_name=model_name)
        if not model:
            return HttpResponse(json.dumps({'status': 'failed', 'msg': 'Invalid table name'}),
                                content_type="application/json")

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model_name}_data.csv"'

        # Create a CSV writer
        csv_writer = csv.writer(response)

        # Write the headers (field names)
        header_row = [field.name for field in model._meta.fields]
        csv_writer.writerow(header_row)

        # Write the data rows
        for obj in model.objects.all():
            data_row = [getattr(obj, field) for field in header_row]
            csv_writer.writerow(data_row)

        return response
    except Exception as e:
        return HttpResponse(json.dumps({'status': 'failed', 'msg': f'{e}'}),
                            content_type="application/json")


def import_products_csv_files(request, model, fields):
    resp = {'status': 'failed'}
    if 'file' in request.FILES:
        csv_file = request.FILES['file']
        decoded_file = csv_file.read().decode('utf-8')
        csv_reader = csv.reader(decoded_file.splitlines(), delimiter=',')
        # Skip the header row
        next(csv_reader, None)

        errors = []
        success_count = 0

        # Iterate over rows and create model instances
        for row_number, row in enumerate(csv_reader, start=2):  # Start counting from row 2
            data_dict = {field: value for field, value in zip(fields, row)}

            # Fetch the Category instance based on the provided category ID
            unit_id = data_dict.pop('unit_id')  # Remove category_id from data_dict
            unit = Units.objects.filter(id=unit_id).first()

            if not unit:
                errors.append({'row': row_number, 'error': f'Product Unit with ID {unit_id} not found.'})
                continue

            # Fetch the Category instance based on the provided category ID
            category_id = data_dict.pop('category_id')  # Remove category_id from data_dict
            category = Category.objects.filter(id=category_id).first()

            if not category:
                errors.append({'row': row_number, 'error': f'Category with ID {category_id} not found.'})
                continue

            total_pieces = Decimal(0)
            # Get 'left_pieces' and 'max_pieces' safely
            left_pieces = data_dict.get('left_pieces')  # Default to 0 if not present
            max_pieces = data_dict.get('max_pieces')  # Default to 0 if not present
            markup = data_dict.get('markup', 0)  # Default to 0 if not present

            if not markup:
                markup = Decimal(0)

            print(f"angaaa : left:{left_pieces} max:{max_pieces} markup:{markup}")
            print(f"{data_dict}")

            try:
                if left_pieces and max_pieces:
                    data_dict['left_pieces'] = int(left_pieces)
                    data_dict['max_pieces'] = int(max_pieces)
                    total_pieces = (Decimal(data_dict.get('quantity')) * Decimal(max_pieces)) + Decimal(left_pieces)
                else:
                    data_dict['left_pieces'] = 0
                    data_dict['max_pieces'] = 1
            except ValueError as e:
                errors.append({'row': row_number, 'error': f'Invalid value for pieces: {e}'})
                continue

            data_dict['total_pieces'] = Decimal(total_pieces)
            data_dict['markup'] = Decimal(markup)
            data_dict['category_id'] = category  # Assign the Category instance to category_id field
            data_dict['units_id'] = unit.id
            data_dict['status'] = 1

            try:
                # Check if a record with the same values already exists
                existing_record = model.objects.filter(**data_dict).first()
            except Exception as e:
                errors.append({'error': f'{e}'})
                continue

            if existing_record:
                errors.append({'row': row_number, 'error': f'Duplicate data for row {row_number}.'})
            else:
                try:
                    # Create model instance
                    data_dict['code'] = generate_unique_code(model)
                    instance = model(**data_dict)
                    instance.save()

                    # Create stock movement
                    StockMovement.objects.create(
                        product=instance,
                        product_name=instance.name,
                        buying_price=instance.buying_price,
                        selling_price=instance.price,
                        user=request.user
                    )

                    success_count += 1
                except Exception as e:
                    print(f"hh : {e}")
                    errors.append({'row': row_number, 'error': str(e)})

        if errors:
            resp['msg'] = str(errors[0])
            resp['status'] = 'failed'
            return HttpResponse(json.dumps(resp), content_type="application/json")
        else:
            resp['msg'] = f' {success_count} Imported successfully'
            resp['status'] = 'success'
            return HttpResponse(json.dumps(resp), content_type="application/json")


def import_suppliers_customers_csv_files(request, model, fields):
    resp = {'status': 'failed'}
    if 'file' in request.FILES:
        csv_file = request.FILES['file']
        decoded_file = csv_file.read().decode('utf-8')
        csv_reader = csv.reader(decoded_file.splitlines(), delimiter=',')
        # Skip the header row
        next(csv_reader, None)

        errors = []
        success_count = 0

        # Iterate over rows and create model instances
        for row_number, row in enumerate(csv_reader, start=2):  # Start counting from row 2
            data_dict = {field: value for field, value in zip(fields, row)}

            # Check if a record with the same values already exists
            existing_record = model.objects.filter(**data_dict).first()

            if existing_record:
                errors.append({'row': row_number, 'error': f'Duplicate data for row {row_number}.'})
            else:
                try:
                    instance = model(**data_dict)
                    instance.save()
                    success_count += 1
                except Exception as e:
                    print(f"hh : {e}")
                    errors.append({'row': row_number, 'error': str(e)})

        if errors:
            resp['msg'] = str(errors[0])
            resp['status'] = 'failed'
            return HttpResponse(json.dumps(resp), content_type="application/json")
        else:
            resp['msg'] = f' {success_count} Imported successfully'
            resp['status'] = 'success'
            return HttpResponse(json.dumps(resp), content_type="application/json")


def generate_unique_code(products):
    while True:
        code = f"{random.randint(0, 999999):06}"
        if not products.objects.filter(code=code).exists():
            return code
