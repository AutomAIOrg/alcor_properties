from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

from alembic import context

# ---------------------------------------------------------------------------
# Alembic config object — gives access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None and config.attributes.get('configure_logger', True):
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Build the database URL using SQLAlchemy's URL.create() so that special
# characters in the password (e.g. '@') are handled correctly without
# triggering ConfigParser interpolation issues.
# ---------------------------------------------------------------------------
from config import settings  # noqa: E402

db_url: URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASS,
    host=settings.DB_HOST,
    port=int(settings.DB_PORT),
    database=settings.DB_NAME,
)

# ---------------------------------------------------------------------------
# Import Base and ALL ORM models so Alembic can detect the full schema.
# Every new model added to infrastructure/models/ must be imported here.
# ---------------------------------------------------------------------------
import infrastructure.models.booking  # noqa: E402, F401
from infrastructure.database.base import Base  # noqa: E402

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a live connection)."""
    context.configure(
        url=db_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=False,  # evita generar cambios por tipos de datos (ej. VARCHAR(255) vs TEXT)
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (executes against a live database)."""
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=False,  # evita generar cambios por tipos de datos (ej. VARCHAR(255) vs TEXT)
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

def include_object(object, name, type_, reflected, compare_to):
    """Solo gestiona tablas que tienen un modelo SQLAlchemy definido."""
    if type_ == "table" and name not in target_metadata.tables:
        return False
    return True

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
