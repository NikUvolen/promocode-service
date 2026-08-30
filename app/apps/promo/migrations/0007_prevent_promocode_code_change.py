from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('promo', '0006_translate_admin_labels'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION promo_prevent_promocode_code_change()
                RETURNS trigger
                AS $$
                BEGIN
                    IF NEW.code IS DISTINCT FROM OLD.code THEN
                        RAISE EXCEPTION 'Promo code cannot be changed after creation.'
                            USING ERRCODE = '23514';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER promo_code_immutable
                BEFORE UPDATE OF code ON promo_promocode
                FOR EACH ROW
                EXECUTE FUNCTION promo_prevent_promocode_code_change();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS promo_code_immutable ON promo_promocode;
                DROP FUNCTION IF EXISTS promo_prevent_promocode_code_change();
            """,
        ),
    ]
