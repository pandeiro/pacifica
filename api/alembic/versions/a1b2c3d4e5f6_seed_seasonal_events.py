"""seed_seasonal_events

Revision ID: a1b2c3d4e5f6
Revises: 582366d65610
Create Date: 2026-03-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "582366d65610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO seasonal_events
            (name, slug, description, typical_start_month, typical_start_day,
             typical_end_month, typical_end_day, species, category)
        VALUES
            ('Gray Whale Southbound Migration', 'gray-whale-south',
             'Gray whales heading south to Baja calving lagoons. Peak viewing from Point Vicente and Palos Verdes cliffs.',
             12, 1, 2, 28, 'Eschrichtius robustus', 'migration'),

            ('Gray Whale Northbound Migration', 'gray-whale-north',
             'Mothers with calves pass close to shore heading north. Best viewing late March through April.',
             3, 1, 5, 15, 'Eschrichtius robustus', 'migration'),

            ('Blue Whale Season', 'blue-whale-season',
             'Blue whales feed on krup aggregations off Santa Catalina and San Diego. Peak July–August.',
             5, 15, 10, 15, 'Balaenoptera musculus', 'migration'),

            ('Humpback Whale Season', 'humpback-whale-season',
             'Humpbacks seen year-round but peak feeding activity spring through fall.',
             4, 1, 11, 15, 'Megaptera novaeangliae', 'migration'),

            ('Grunion Runs', 'grunion-runs',
             'Silvery fish spawn on sandy beaches 4 nights after full/new moon, March through August.',
             3, 1, 8, 31, 'Leuresthes tenuis', 'spawning'),

            ('Lobster Season', 'lobster-season',
             'California spiny lobster sport and commercial season. Hot spots: Catalina, Laguna, Point Loma.',
             10, 1, 3, 15, 'Panulirus interruptus', 'season'),

            ('Bioluminescence Events', 'bioluminescence',
             'Red tide dinoflagellates and Lingulodinium polyedra create electric-blue surf. Unpredictable but peaks spring.',
             3, 1, 6, 30, 'Lingulodinium polyedra', 'bloom'),

            ('Garibaldi Nesting Season', 'garibaldi-nesting',
             'California state marine fish. Males guard bright orange nests in rocky reef areas.',
             4, 1, 8, 31, 'Hypsypops rubicundus', 'breeding'),

            ('Sea Turtle Sightings', 'sea-turtle-sightings',
             'Green sea turtles and occasional leatherbacks forage off La Jolla and Long Beach.',
             5, 1, 11, 30, 'Chelonia mydas', 'migration'),

            ('Elephant Seal Pupping', 'elephant-seal-pupping',
             'Año Nuevo and Piedras Blancas colonies. Pups born December–February, weaned by March.',
             12, 15, 3, 15, 'Mirounga angustirostris', 'breeding'),

            ('Sea Lion Pupping Season', 'sea-lion-pupping',
             'California sea lion pups born on Channel Islands and haul-out sites. Peak June–July.',
             6, 1, 9, 30, 'Zalophus californianus', 'breeding'),

            ('Dolphin Superpods', 'dolphin-superpods',
             'Common dolphins form massive superpods (1000+) offshore. Best chances spring and fall.',
             3, 1, 5, 31, 'Delphinus delphis', 'migration'),

            ('Leopard Shark Season', 'leopard-shark-season',
             'Leopard sharks aggregate in shallow La Jolla Cove for warm-water pupping. Snorkel-friendly.',
             6, 1, 10, 15, 'Triakis semifasciata', 'migration'),

            ('Tidepool Low Tides', 'tidepool-low-tides',
             'Negative low tides expose rich intertidal zones. Best at Point Loma, Crystal Cove, Leo Carrillo.',
             5, 1, 9, 30, NULL, 'tidal'),

            ('Sea Bass Spawning', 'sea-bass-spawning',
             'Giant sea bass aggregate at known reef sites for spawning. Protected — no take.',
             6, 1, 9, 30, 'Stereolepis gigas', 'spawning'),

            ('Halibut Season', 'halibut-season',
             'California halibut peak fishing. Sandy bottoms off Huntington, Redondo, Mission Bay.',
             3, 1, 10, 31, 'Paralichthys californicus', 'season')
        ON CONFLICT (slug) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM seasonal_events;")
