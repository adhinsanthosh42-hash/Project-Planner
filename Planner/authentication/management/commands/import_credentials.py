from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from authentication.models import Profile


class Command(BaseCommand):
    help = 'Import profile records from authentication/credentials.txt.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(Path(settings.BASE_DIR) / 'authentication' / 'credentials.txt'),
            help='Path to the credentials text file.',
        )

    def handle(self, *args, **options):
        source = Path(options['file'])
        if not source.is_file():
            raise CommandError(f'Credentials file not found: {source}')

        records = []
        current = {}
        for line in source.read_text(encoding='utf-8-sig').splitlines() + ['']:
            if not line.strip():
                if 'Username' in current:
                    records.append(current)
                current = {}
                continue

            if ':' not in line:
                continue

            key, value = (part.strip() for part in line.split(':', 1))
            current[key] = value

        required = ('Username', 'First name', 'Last name', 'Email', 'Password', 'Role', 'Tech')
        created = 0
        updated = 0

        for number, record in enumerate(records, start=1):
            missing = [key for key in required if not record.get(key)]
            if missing:
                raise CommandError(
                    f'Record {number} is missing required fields: {", ".join(missing)}'
                )

            username = record['Username']
            profile, was_created = Profile.objects.get_or_create(username=username)
            profile.first_name = record['First name']
            profile.last_name = record['Last name']
            profile.email = record['Email']
            profile.role = record['Role']
            profile.tech = record['Tech'] or None
            profile.set_password(record['Password'])
            profile.save()

            if was_created:
                created += 1
            else:
                updated += 1

        if not records:
            raise CommandError('No profile records were found in the credentials file.')

        self.stdout.write(self.style.SUCCESS(
            f'Imported {len(records)} profile records: {created} created, {updated} updated.'
        ))
