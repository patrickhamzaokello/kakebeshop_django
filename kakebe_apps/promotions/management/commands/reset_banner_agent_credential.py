from django.core.management.base import BaseCommand

from kakebe_apps.promotions.models import BannerAgentCredential


class Command(BaseCommand):
    help = 'Create or reset a banner AI agent upload credential.'

    def add_arguments(self, parser):
        parser.add_argument('--name', default='default-ai-banner-agent')
        parser.add_argument('--secret', default='')
        parser.add_argument('--inactive', action='store_true')

    def handle(self, *args, **options):
        credential, _ = BannerAgentCredential.objects.get_or_create(
            name=options['name'],
            defaults={'is_active': not options['inactive']},
        )

        secret = options['secret'] or credential.issue_secret()
        if options['secret']:
            credential.set_secret(secret)

        credential.is_active = not options['inactive']
        credential.save(update_fields=['token_prefix', 'token_hash', 'is_active', 'updated_at'])

        self.stdout.write(self.style.SUCCESS(f'Credential: {credential.name}'))
        self.stdout.write(f'Secret: {secret}')
        self.stdout.write('Store this secret now; it cannot be recovered from the database.')
