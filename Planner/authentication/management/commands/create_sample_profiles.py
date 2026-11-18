import secrets
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from authentication.models import Profile, RoleChoices, TechChoices


class Command(BaseCommand):
    help = "Create 18 sample profiles and save their credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            "--credentials-only",
            action="store_true",
            help="Generate credentials.txt without creating database records.",
        )

    def handle(self, *args, **options):
        auth_dir = Path(__file__).resolve().parents[2]
        credentials_path = auth_dir / "credentials.txt"
        profiles = self.build_profiles()

        if credentials_path.exists():
            profiles = self.read_credentials(credentials_path, profiles)
        else:
            for profile in profiles:
                profile["password"] = secrets.token_urlsafe(24)
            self.write_credentials(credentials_path, profiles)

        if options["credentials_only"]:
            self.stdout.write(self.style.SUCCESS(
                f"Credentials saved to {credentials_path}. No database records were created."
            ))
            return

        usernames = [profile["username"] for profile in profiles]
        existing = list(
            Profile.objects.filter(username__in=usernames).values_list("username", flat=True)
        )
        if existing:
            raise CommandError(
                "Profiles already exist; no records were created: " + ", ".join(existing)
            )

        with transaction.atomic():
            for profile in profiles:
                Profile.objects.create_user(
                    username=profile["username"],
                    password=profile["password"],
                    first_name=profile["first_name"],
                    last_name=profile["last_name"],
                    email=profile["email"],
                    role=profile["role"],
                    tech=profile["tech"],
                )

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(profiles)} profiles. Credentials saved to {credentials_path}."
        ))

    @staticmethod
    def build_profiles():
        profiles = []
        groups = (
            (
                (("priya", "nair"), ("ethan", "brooks"), ("sofia", "martinez")),
                RoleChoices.COORDINATOR,
                None,
            ),
            (
                (("arjun", "menon"), ("chloe", "nguyen"), ("marcus", "reed")),
                RoleChoices.DEVELOPER,
                TechChoices.BACKEND,
            ),
            (
                (("aisha", "khan"), ("lucas", "bennett"), ("mei", "tanaka")),
                RoleChoices.DEVELOPER,
                TechChoices.FRONTEND,
            ),
            (
                (("daniel", "kim"), ("isabella", "rossi"), ("noah", "patel")),
                RoleChoices.DEVELOPER,
                TechChoices.FULLSTACK,
            ),
            (
                (("maya", "thompson"), ("omar", "hassan"), ("grace", "liu")),
                RoleChoices.DEVELOPER,
                TechChoices.UI_UX,
            ),
            (
                (("elena", "garcia"), ("samuel", "okafor"), ("anika", "sharma")),
                RoleChoices.DEVELOPER,
                TechChoices.TESTER,
            ),
        )

        for people, role, tech in groups:
            for first_name, last_name in people:
                profiles.append({
                    "username": f"{first_name}_{last_name}",
                    "first_name": first_name.title(),
                    "last_name": last_name.title(),
                    "email": f"{first_name}.{last_name}@example.test",
                    "role": role,
                    "tech": tech,
                    "password": "",
                })
        return profiles

    @staticmethod
    def write_credentials(path, profiles):
        lines = ["Sample profile credentials", "==========================", ""]
        for profile in profiles:
            lines.extend((
                f'Username: {profile["username"]}',
                f'First name: {profile["first_name"]}',
                f'Last name: {profile["last_name"]}',
                f'Email: {profile["email"]}',
                f'Password: {profile["password"]}',
                f'Role: {profile["role"]}',
                f'Tech: {profile["tech"] or "N/A"}',
                "",
            ))
        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def read_credentials(path, profiles):
        credentials = {}
        for block in path.read_text(encoding="utf-8").split("\n\n"):
            fields = {}
            for line in block.splitlines():
                key, separator, value = line.partition(": ")
                if separator and key in {"Username", "Password"}:
                    fields[key] = value
            if fields:
                if set(fields) != {"Username", "Password"} or not fields["Password"]:
                    raise CommandError(f"Invalid credentials format in {path}.")
                username = fields["Username"]
                if username in credentials:
                    raise CommandError(f"Duplicate username in {path}: {username}")
                credentials[username] = fields["Password"]

        expected_usernames = {profile["username"] for profile in profiles}
        if credentials.keys() != expected_usernames:
            raise CommandError(
                f"{path} must contain credentials for exactly the expected profile usernames."
            )
        for profile in profiles:
            profile["password"] = credentials[profile["username"]]
        return profiles
