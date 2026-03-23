"""seasonal_events_locations_and_conditions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-22 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add conditions columns to seasonal_events
    op.add_column(
        "seasonal_events", sa.Column("conditions_type", sa.Text, nullable=True)
    )
    op.add_column(
        "seasonal_events", sa.Column("conditions_text", sa.Text, nullable=True)
    )

    # 2. Create join table
    op.create_table(
        "seasonal_event_locations",
        sa.Column(
            "event_id",
            sa.Integer,
            sa.ForeignKey("seasonal_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "location_id",
            sa.Integer,
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # 3. Seed conditions (individual statements for asyncpg compat)
    op.execute(
        "UPDATE seasonal_events SET conditions_type = 'moon_phase', "
        "conditions_text = 'Runs occur 4 nights after full/new moon, typically late evening at high tide on sandy beaches' "
        "WHERE slug = 'grunion-runs'"
    )
    op.execute(
        "UPDATE seasonal_events SET conditions_type = 'temperature', "
        "conditions_text = 'Triggered by warm water temperatures and dinoflagellate blooms, most visible at night' "
        "WHERE slug = 'bioluminescence'"
    )
    op.execute(
        "UPDATE seasonal_events SET conditions_type = 'temperature', "
        "conditions_text = 'Aggregates in shallow warm waters (65°F+), best snorkeling conditions midday' "
        "WHERE slug = 'leopard-shark-season'"
    )
    op.execute(
        "UPDATE seasonal_events SET conditions_type = 'tide', "
        "conditions_text = 'Best during negative low tides exposing intertidal zones; check tide charts' "
        "WHERE slug = 'tidepool-low-tides'"
    )
    op.execute(
        "UPDATE seasonal_events SET conditions_type = 'temperature', "
        "conditions_text = 'Spawning aggregations at known reef sites during warmest months; protected — no take' "
        "WHERE slug = 'sea-bass-spawning'"
    )

    # 4. Add new locations
    op.execute(
        "INSERT INTO locations (name, slug, lat, lng, location_type, region, description) "
        "VALUES ('San Miguel Island', 'san_miguel_island', 34.0378, -120.3753, "
        "'island', 'channel_islands', 'Northernmost Channel Island. Major elephant seal rookery at Point Bennett.') "
        "ON CONFLICT (slug) DO NOTHING"
    )
    op.execute(
        "INSERT INTO locations (name, slug, lat, lng, location_type, region, description) "
        "VALUES ('Dockweiler Beach', 'dockweiler_beach', 33.9161, -118.4363, "
        "'beach', 'la_coast', 'State beach in Playa del Rey. Known bioluminescence observation spot near LAX.') "
        "ON CONFLICT (slug) DO NOTHING"
    )

    # 5. Seed event-location mappings using slug subqueries (no hardcoded IDs)
    # Each insert looks up event_id and location_id by slug
    _insert_mapping("gray-whale-south", "point_vicente")
    _insert_mapping("gray-whale-south", "santa_barbara")
    _insert_mapping("gray-whale-south", "morro_bay")

    _insert_mapping("gray-whale-north", "point_vicente")
    _insert_mapping("gray-whale-north", "santa_barbara")
    _insert_mapping("gray-whale-north", "morro_bay")

    _insert_mapping("blue-whale-season", "avalon_catalina")
    _insert_mapping("blue-whale-season", "san_diego")
    _insert_mapping("blue-whale-season", "dana_point")
    _insert_mapping("blue-whale-season", "ventura")
    _insert_mapping("blue-whale-season", "prisoners_harbor")
    _insert_mapping("blue-whale-season", "bechers_bay")

    _insert_mapping("humpback-whale-season", "santa_barbara")
    _insert_mapping("humpback-whale-season", "avalon_catalina")
    _insert_mapping("humpback-whale-season", "santa_monica")
    _insert_mapping("humpback-whale-season", "dana_point")
    _insert_mapping("humpback-whale-season", "ventura")
    _insert_mapping("humpback-whale-season", "prisoners_harbor")
    _insert_mapping("humpback-whale-season", "bechers_bay")

    _insert_mapping("grunion-runs", "newport_beach")
    _insert_mapping("grunion-runs", "zuma_beach")
    _insert_mapping("grunion-runs", "santa_monica")
    _insert_mapping("grunion-runs", "dana_point")

    _insert_mapping("lobster-season", "avalon_catalina")
    _insert_mapping("lobster-season", "shaws_cove")
    _insert_mapping("lobster-season", "san_diego")

    _insert_mapping("bioluminescence", "la_jolla")
    _insert_mapping("bioluminescence", "newport_beach")
    _insert_mapping("bioluminescence", "redondo_beach")
    _insert_mapping("bioluminescence", "dockweiler_beach")

    _insert_mapping("garibaldi-nesting", "la_jolla")
    _insert_mapping("garibaldi-nesting", "shaws_cove")
    _insert_mapping("garibaldi-nesting", "avalon_catalina")

    _insert_mapping("sea-turtle-sightings", "la_jolla")
    _insert_mapping("sea-turtle-sightings", "long_beach")

    _insert_mapping("elephant-seal-pupping", "san_simeon")
    _insert_mapping("elephant-seal-pupping", "san_miguel_island")

    _insert_mapping("sea-lion-pupping", "avalon_catalina")
    _insert_mapping("sea-lion-pupping", "san_nicolas_island")

    _insert_mapping("dolphin-superpods", "la_jolla")
    _insert_mapping("dolphin-superpods", "dana_point")
    _insert_mapping("dolphin-superpods", "santa_monica")

    _insert_mapping("leopard-shark-season", "la_jolla")

    _insert_mapping("tidepool-low-tides", "shaws_cove")
    _insert_mapping("tidepool-low-tides", "la_jolla")
    _insert_mapping("tidepool-low-tides", "morro_bay")

    _insert_mapping("sea-bass-spawning", "la_jolla")
    _insert_mapping("sea-bass-spawning", "avalon_catalina")

    _insert_mapping("halibut-season", "redondo_beach")
    _insert_mapping("halibut-season", "long_beach")
    _insert_mapping("halibut-season", "newport_beach")
    _insert_mapping("halibut-season", "imperial_beach")


def _insert_mapping(event_slug: str, location_slug: str) -> None:
    op.execute(
        f"INSERT INTO seasonal_event_locations (event_id, location_id) "
        f"SELECT e.id, l.id FROM seasonal_events e, locations l "
        f"WHERE e.slug = '{event_slug}' AND l.slug = '{location_slug}' "
        f"ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("seasonal_event_locations")
    op.execute(
        "UPDATE seasonal_events SET conditions_type = NULL, conditions_text = NULL"
    )
    op.drop_column("seasonal_events", "conditions_text")
    op.drop_column("seasonal_events", "conditions_type")
    op.execute(
        "DELETE FROM locations WHERE slug IN ('san_miguel_island', 'dockweiler_beach')"
    )
