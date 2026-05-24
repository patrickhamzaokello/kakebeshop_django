from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0003_banner_image_imports_and_targets'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                CREATE TABLE IF NOT EXISTS banner_agent_credentials (
                    id uuid NOT NULL PRIMARY KEY,
                    name varchar(120) NOT NULL UNIQUE,
                    token_prefix varchar(12) NOT NULL,
                    token_hash varchar(128) NOT NULL,
                    is_active boolean NOT NULL,
                    last_used_at timestamp with time zone NULL,
                    created_at timestamp with time zone NOT NULL,
                    updated_at timestamp with time zone NOT NULL
                )
                """,
                """
                CREATE INDEX IF NOT EXISTS banner_agent_credentials_token_prefix_idx
                ON banner_agent_credentials (token_prefix)
                """,
                """
                CREATE INDEX IF NOT EXISTS banner_agent_credentials_is_active_idx
                ON banner_agent_credentials (is_active)
                """,
                """
                CREATE TABLE IF NOT EXISTS banner_image_imports (
                    id uuid NOT NULL PRIMARY KEY,
                    source_path varchar(500) NOT NULL UNIQUE,
                    sidecar_path varchar(500) NOT NULL,
                    target_field varchar(20) NOT NULL,
                    status varchar(20) NOT NULL,
                    error_message text NOT NULL,
                    metadata jsonb NOT NULL,
                    processed_at timestamp with time zone NULL,
                    created_at timestamp with time zone NOT NULL,
                    updated_at timestamp with time zone NOT NULL,
                    banner_id uuid NULL,
                    image_asset_id uuid NULL,
                    uploaded_by_agent_id uuid NULL
                )
                """,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'banner_image_imports_banner_id_fk'
                    ) THEN
                        ALTER TABLE banner_image_imports
                        ADD CONSTRAINT banner_image_imports_banner_id_fk
                        FOREIGN KEY (banner_id)
                        REFERENCES promotional_banners(id)
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END
                $$;
                """,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'banner_image_imports_image_asset_id_fk'
                    ) THEN
                        ALTER TABLE banner_image_imports
                        ADD CONSTRAINT banner_image_imports_image_asset_id_fk
                        FOREIGN KEY (image_asset_id)
                        REFERENCES image_assets(id)
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END
                $$;
                """,
                """
                ALTER TABLE banner_image_imports
                ADD COLUMN IF NOT EXISTS uploaded_by_agent_id uuid NULL
                """,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'banner_image_imports_uploaded_by_agent_id_fk'
                    ) THEN
                        ALTER TABLE banner_image_imports
                        ADD CONSTRAINT banner_image_imports_uploaded_by_agent_id_fk
                        FOREIGN KEY (uploaded_by_agent_id)
                        REFERENCES banner_agent_credentials(id)
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END
                $$;
                """,
                """
                CREATE INDEX IF NOT EXISTS banner_image_imports_uploaded_by_agent_id_idx
                ON banner_image_imports (uploaded_by_agent_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS banner_imag_status_2f1215_idx
                ON banner_image_imports (status, created_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS banner_imag_banner__7ea7c1_idx
                ON banner_image_imports (banner_id, target_field)
                """,
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
