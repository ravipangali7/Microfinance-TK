from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from app.models import User


class Command(BaseCommand):
    help = 'Seeds the database with default groups and admin user'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting seed data process...'))

        # Create default groups
        groups = ['Admin', 'Board', 'Staff', 'Member']
        created_groups = []
        existing_groups = []

        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups.append(group_name)
                self.stdout.write(self.style.SUCCESS(f'✓ Created group: {group_name}'))
            else:
                existing_groups.append(group_name)
                self.stdout.write(self.style.WARNING(f'→ Group already exists: {group_name}'))

        # Create admin user
        admin_phone = '977'
        admin_name = 'Admin'
        admin_password = '12345678'

        try:
            admin_user, user_created = User.objects.get_or_create(
                phone=admin_phone,
                defaults={
                    'name': admin_name,
                    'email': 'admin@example.com',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )

            if user_created:
                admin_user.set_password(admin_password)
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Created admin user: {admin_name} (phone: {admin_phone})'))
            else:
                # Update password if user already exists
                admin_user.set_password(admin_password)
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.is_active = True
                admin_user.save()
                self.stdout.write(self.style.WARNING(f'→ Admin user already exists, updated password and permissions: {admin_name} (phone: {admin_phone})'))

            # Assign admin user to Admin group
            admin_group = Group.objects.get(name='Admin')
            if admin_group not in admin_user.groups.all():
                admin_user.groups.add(admin_group)
                self.stdout.write(self.style.SUCCESS(f'✓ Assigned {admin_name} to Admin group'))
            else:
                self.stdout.write(self.style.WARNING(f'→ {admin_name} is already in Admin group'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error creating admin user: {str(e)}'))
            return

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Seed data process completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Groups created: {len(created_groups)}')
        self.stdout.write(f'Groups existing: {len(existing_groups)}')
        self.stdout.write(f'Admin user: {"Created" if user_created else "Updated"}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('You can now login with:'))
        self.stdout.write(self.style.SUCCESS(f'  Phone: {admin_phone}'))
        self.stdout.write(self.style.SUCCESS(f'  Password: {admin_password}'))

