# flake8: noqa: W291
import os
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0014_invite_is_collaborator"),
    ]

    if os.environ.get("DJANGO_SETTINGS_MODULE") == "server.settings.production":
        print("Running PRODUCTION migration")
        operations = [
            migrations.RunSQL(
                """
            UPDATE myauth_tier SET name = 'COMMUNITY',
                stripe_flat_price_id = null,
                stripe_storage_price_id = 'price_1JPNxkFauXVlvS5wweWbfiGw',
                stripe_collaborator_price_id = 'price_1JPNytFauXVlvS5waAQC8czE',
                stripe_user_price_id = null,
                stripe_project_price_id = 'price_1JPNyyFauXVlvS5wqfqzkrBS',
                base_collaborator_limit = 2,
                base_project_limit = 1,
                base_storage_limit = 1000,
                base_user_limit = 1 
            WHERE id = 1;

            UPDATE myauth_tier SET name = 'PRO',
                stripe_flat_price_id = 'price_1JPNxxFauXVlvS5wva02Iw90',
                stripe_storage_price_id = 'price_1JjkCuFauXVlvS5w9pot4NWr',
                stripe_collaborator_price_id = 'price_1JPNyAFauXVlvS5wPyAFUOxl',
                stripe_user_price_id = 'price_1JPNyOFauXVlvS5w8eIGos3k',
                stripe_project_price_id = null,
                base_collaborator_limit = 2,
                base_project_limit = null,
                base_storage_limit = 10000,
                base_user_limit = 10 
            WHERE id = 2;

            UPDATE myauth_tier SET name = 'TEAM',
                stripe_flat_price_id = 'price_1JPNyUFauXVlvS5wbefopTwb',
                stripe_storage_price_id = 'price_1JjkDgFauXVlvS5wtbQt4voC',
                stripe_collaborator_price_id = 'price_1JPNynFauXVlvS5wfssg6GST',    
                stripe_user_price_id = 'price_1JPNyjFauXVlvS5w8IiOPJxP',
                stripe_project_price_id = null,
                base_collaborator_limit = 5,
                base_project_limit = null,
                base_storage_limit = 100000,
                base_user_limit = 15 
            WHERE id = 3;
        """
            )
        ]
    else:
        print("Running NON-PRODUCTION migration")
        operations = [
            migrations.RunSQL(
                """
            UPDATE myauth_tier SET name = 'COMMUNITY',
                stripe_flat_price_id = null,
                stripe_storage_price_id = 'price_1JMrOtFauXVlvS5wTLRzIqqu',
                stripe_collaborator_price_id = 'price_1JMrOtFauXVlvS5wTLRzIqqu',
                stripe_user_price_id = null,
                stripe_project_price_id = 'price_1JMrT4FauXVlvS5wtoHCunES',
                base_collaborator_limit = 2,
                base_project_limit = 1,
                base_storage_limit = 1000,
                base_user_limit = 1 
            WHERE id = 1;

            UPDATE myauth_tier SET name = 'PRO',
                stripe_flat_price_id = 'price_1JMrINFauXVlvS5wQxncCCrF',
                stripe_storage_price_id = 'price_1Jjk6xFauXVlvS5wnfx98Ojr',
                stripe_collaborator_price_id = 'price_1JMrJRFauXVlvS5w2WpMI1IK',
                stripe_user_price_id = 'price_1JMrKHFauXVlvS5wYzIX36Rm',
                stripe_project_price_id = null,
                base_collaborator_limit = 2,
                base_project_limit = null,
                base_storage_limit = 10000,
                base_user_limit = 10 
            WHERE id = 2;

            UPDATE myauth_tier SET name = 'TEAM',
                stripe_flat_price_id = 'price_1JMrQGFauXVlvS5wDBOJnJHm',
                stripe_storage_price_id = 'price_1JMrOtFauXVlvS5wKV9LOuw8',
                stripe_collaborator_price_id = 'price_1JMrRtFauXVlvS5w2vMOo1sv',    
                stripe_user_price_id = 'price_1JMrRCFauXVlvS5wQeuL7Z1l',
                stripe_project_price_id = null,
                base_collaborator_limit = 5,
                base_project_limit = null,
                base_storage_limit = 100000,
                base_user_limit = 15 
            WHERE id = 3;
        """
            )
        ]
