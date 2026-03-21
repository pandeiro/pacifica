"""seed_live_cams

Revision ID: 582366d65610
Revises: 601d51e14d1d
Create Date: 2026-03-21 20:45:30.760778

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "582366d65610"
down_revision: Union[str, Sequence[str], None] = "601d51e14d1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO live_cams (name, location_id, embed_type, embed_url, source_name, is_active, sort_order)
        VALUES
            ('Anacapa Underwater',       17, 'youtube', 'OAJF1Ie1m_Q',  'Explore.org / Channel Islands NP',  true,  0),
            ('Eagle Cam — Catalina Is.', 16, 'youtube', 'RmmAzrAkKqI',  'Explore.org / Channel Islands NP',  true,  1),
            ('Santa Monica Pier',         3, 'youtube', 'qmE7U1YZPQA',  'Explore.org / Pacific Park',         true,  2),
            ('Dana Point Harbor',         1, 'youtube', 'LDNMn4mrKxA',  'HD Beach Cams',                      true,  3),
            ('Morro Bay Harbor',          5, 'youtube', 'ItClzVqLb4Q',  '805 Webcams',                        true,  4),
            ('Laguna Beach',              6, 'youtube', 'Xvu5imiDOXY',  'SkylineWebcams',                     true,  5),
            ('King Harbor',              12, 'youtube', 'Ni7v-aIa3bw',  'City of Redondo Beach',              true,  6),
            ('Redondo Beach Pier',       12, 'youtube', 'TuVOKRP7IBA',  'City of Redondo Beach',              true,  7),
            ('Scripps Pier Underwater',   2, 'iframe',  '//portal.hdontap.com/s/embed?stream=scripps_pier-underwater-CUST&ratio=16:9&fluid=true', 'HDOnTap / Scripps Oceanography', true, 8),
            ('Scripps Pier',              2, 'iframe',  'https://embed.cdn-surfline.com/cams/5834a0733421b20545c4b584/64ba68ebf1c960a93d1faba8f86cc16a3ed05913', 'Surfline / Scripps Oceanography', true, 9),
            ('La Jolla Shores',           2, 'iframe',  'https://embed.cdn-surfline.com/cams/58349b9b3421b20545c4b54d/199ae31e65bf748a7c7d928332998440490cd979', 'Surfline / Scripps Oceanography', true, 10)
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM live_cams;")
