# Generated manually to align server region field with configurable choices
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("servers", "0004_rename_server_invites_server_created_idx_server_invi_server__30c72f_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="server",
            name="region",
            field=models.CharField(
                choices=[
                    ("us-east", "US East"),
                    ("us-west", "US West"),
                    ("eu-central", "EU Central"),
                    ("asia-pacific", "Asia Pacific"),
                ],
                default="us-east",
                max_length=50,
            ),
        ),
    ]
