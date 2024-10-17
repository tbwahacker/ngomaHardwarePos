from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from posApp.models import PaymentMethod


class Command(BaseCommand):
    help = 'Seeding data'

    def handle(self, *args, **options):
        if PaymentMethod.objects.filter(code='0001').exists() \
                and PaymentMethod.objects.filter(code='0002').exists():  #Due
            print("Data already exists. Skipp seeding Status Type.")
        else:
            PaymentMethod.objects.create(name='Cash', code='0001')
            PaymentMethod.objects.create(name='Credit', code='0002')
        # Your data seeding logic here

        self.stdout.write(self.style.SUCCESS('Data seeded successfully.'))

        return
