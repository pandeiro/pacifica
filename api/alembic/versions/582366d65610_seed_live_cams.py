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
        SELECT cam.name, loc.id, cam.embed_type, cam.embed_url, cam.source_name, cam.is_active, cam.sort_order
        FROM (VALUES
            ('Anacapa Underwater',       'prisoners_harbor',     'youtube', 'OAJF1Ie1m_Q',  'Explore.org / Channel Islands NP',  true::boolean,  0),
            ('Eagle Cam — Catalina Is.', 'avalon_catalina',      'youtube', 'RmmAzrAkKqI',  'Explore.org / Channel Islands NP',  true::boolean,  1),
            ('Santa Monica Pier',        'santa_monica',         'youtube', 'qmE7U1YZPQA',  'Explore.org / Pacific Park',         true::boolean,  2),
            ('Dana Point Harbor',        'dana_point',           'youtube', 'LDNMn4mrKxA',  'HD Beach Cams',                      true::boolean,  3),
            ('Laguna Beach',             'shaws_cove',           'youtube', 'Xvu5imiDOXY',  'SkylineWebcams',                     true::boolean,  4),
            ('King Harbor',              'redondo_beach',        'youtube', 'Ni7v-aIa3bw',  'City of Redondo Beach',              true::boolean,  5),
            ('Redondo Beach Pier',       'redondo_beach',        'youtube', 'TuVOKRP7IBA',  'City of Redondo Beach',              true::boolean,  6),
            ('Scripps Pier',             'la_jolla',             'iframe',  'https://embed.cdn-surfline.com/cams/5834a0733421b20545c4b584/64ba68ebf1c960a93d1faba8f86cc16a3ed05913', 'Surfline / Scripps Oceanography', true::boolean, 7),
            ('La Jolla Shores',          'la_jolla',             'iframe',  'https://embed.cdn-surfline.com/cams/58349b9b3421b20545c4b54d/199ae31e65bf748a7c7d928332998440490cd979', 'Surfline / Scripps Oceanography', true::boolean, 8)
        ) AS cam(name, slug, embed_type, embed_url, source_name, is_active, sort_order)
        JOIN locations loc ON loc.slug = cam.slug
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM live_cams;")
