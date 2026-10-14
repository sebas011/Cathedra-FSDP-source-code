import csv
from io import StringIO

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.migrations import run_migrations
from app.models import Scholar


def payload(saved):
    return {
        'name': saved['name'],
        'missing_requirements': saved['manual_requirements_follow_up'],
        'department': saved['department'],
        'participations': [{**grant, 'program_name': grant['name']} for grant in saved['participations']],
        'requirements': saved['requirements'],
    }


@pytest.mark.parametrize('field', ['participations', 'requirements', 'both'])
def test_complete_register_replacement_is_one_atomic_save(client, field):
    saved = client.post('/api/v1/fsdp', json={
        'name': 'Replace all', 'participations': [{'program_name': 'Old'}],
        'requirements': [{'requirement_name': 'Old document'}],
    }).json()
    update = payload(saved)
    if field in ('participations', 'both'):
        update['participations'] = [{'program_name': 'New'}]
    if field in ('requirements', 'both'):
        update['requirements'] = [{'requirement_name': 'New document'}]
    response = client.put(f"/api/v1/fsdp/{saved['id']}", json=update,
                          headers={'If-Match': str(saved['revision'])})
    assert response.status_code == 200
    result = response.json()
    assert result['revision'] == saved['revision'] + 1
    assert len(result['participations']) == len(result['requirements']) == 1
    assert result['participations'][0]['name'] == ('NEW' if field != 'requirements' else 'OLD')
    assert result['requirements'][0]['requirement_name'] == (
        'NEW DOCUMENT' if field != 'participations' else 'OLD DOCUMENT')
    assert client.put(f"/api/v1/fsdp/{saved['id']}", json=update,
                      headers={'If-Match': str(saved['revision'])}).status_code == 409
    assert client.get(f"/api/v1/fsdp/{saved['id']}").json() == result


@pytest.mark.parametrize('field', ['participations', 'requirements'])
def test_replacement_cannot_take_another_scholars_child(client, field):
    owner = client.post('/api/v1/fsdp', json={
        'name': 'Owner', 'participations': [{'program_name': 'Owned'}],
        'requirements': [{'requirement_name': 'Owned document'}],
    }).json()
    other = client.post('/api/v1/fsdp', json={'name': 'Other'}).json()
    update = payload(other)
    update[field] = payload(owner)[field]
    assert client.put(f"/api/v1/fsdp/{other['id']}", json=update,
                      headers={'If-Match': str(other['revision'])}).status_code == 409
    assert client.get(f"/api/v1/fsdp/{owner['id']}").json() == owner
    assert client.get(f"/api/v1/fsdp/{other['id']}").json() == other


def test_namesakes_keep_separate_grants_history_and_deletion(client):
    one = client.post('/api/v1/fsdp', json={
        'name': 'Alex Santos', 'department': 'CAS',
        'participations': [{'program_name': 'CAS program'}],
    }).json()
    response = client.post('/api/v1/fsdp', json={
        'name': 'Alex Santos', 'department': 'CCS',
        'participations': [{'program_name': 'CCS program'}],
    })
    assert response.status_code == 201
    two = response.json()
    assert one['id'] != two['id']
    matches = client.get('/api/v1/fsdp/name-matches', params={
        'name': 'Alex Santos', 'exclude_id': two['id'],
    }).json()
    assert matches[0]['id'] == one['id']
    assert client.get('/api/v1/fsdp/page', params={'search': 'Alex Santos'}).json()['total'] == 2
    for scholar in (one, two):
        history = client.get(f"/api/v1/activity/scholars/{scholar['id']}").json()
        assert history['total'] == 2
        assert {(item['record_type'], item['record_id']) for item in history['items']} == {
            ('scholars', scholar['id']),
            ('fsdp_participations', scholar['participations'][0]['id']),
        }
    assert client.delete(f"/api/v1/fsdp/{one['id']}",
                         headers={'If-Match': str(one['revision'])}).status_code == 204
    assert client.get(f"/api/v1/fsdp/{two['id']}").json() == two


@pytest.mark.parametrize('manual,count', [(True, 0), (False, 1), (False, 2), (True, 2), (False, 0)])
def test_follow_up_report_counts_scholars_and_preserves_manual_actions(client, manual, count):
    saved = client.post('/api/v1/fsdp', json={
        'name': 'Follow-up', 'department': 'CAS', 'missing_requirements': manual,
        'requirements': [{'requirement_name': f'Document {i}'} for i in range(count)],
    }).json()
    report = client.get('/api/v1/fsdp/report').json()
    needs_follow_up = int(manual or count > 0)
    assert report['missing_requirements'] == needs_follow_up
    assert report['department_totals'][0]['requirements_follow_up'] == needs_follow_up
    assert len(report['action_items']) == count + int(manual)
    manual_actions = [a for a in report['action_items'] if a['attention'] == 'Manual follow-up']
    assert len(manual_actions) == int(manual)
    if manual:
        assert manual_actions[0]['scholar_id'] == saved['id']
    analytics = client.get('/api/v1/fsdp/analytics').json()
    assert analytics['requirements_follow_up'] == needs_follow_up
    rows = list(csv.reader(StringIO(client.get('/api/v1/fsdp/report.csv').text)))
    header = rows.index(['Department', 'Scholars', 'On-going', 'Completed', 'Payback',
                         'Withdrawn', 'Did Not Avail', 'Transferred', 'Payback pending contract', 'Requirements follow-up (scholars)'])
    assert rows[header + 1][-1] == str(needs_follow_up)
    assert sum(bool(row) and row[-1] == 'Manual follow-up' for row in rows) == int(manual)


def test_filtered_department_follow_up_reconciles_with_report(client):
    for name, department, manual, count in [('Manual', 'CAS', True, 0),
                                           ('Register', 'CAS', False, 2),
                                           ('Other', 'CCS', True, 0)]:
        assert client.post('/api/v1/fsdp', json={
            'name': name, 'department': department, 'missing_requirements': manual,
            'requirements': [{'requirement_name': f'Document {i}'} for i in range(count)],
        }).status_code == 201
    report = client.get('/api/v1/fsdp/report', params={
        'department': 'CAS', 'missing_requirements': 'true',
    }).json()
    assert report['total'] == report['missing_requirements'] == 2
    assert sum(row['requirements_follow_up'] for row in report['department_totals']) == 2
    assert {item['scholar_name'] for item in report['action_items']} == {'MANUAL', 'REGISTER'}


def test_namesake_migration_preserves_rows_and_search_index(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'namesakes.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            run_migrations(conn)
            conn.exec_driver_sql('DELETE FROM schema_migrations WHERE version >= 5')
            conn.exec_driver_sql('CREATE UNIQUE INDEX uq_scholars_name ON scholars(name)')
            conn.execute(Scholar.__table__.insert().values(id=9, name='Existing', department='CAS', revision=3))
            before = conn.exec_driver_sql('SELECT * FROM scholars').fetchall()
            run_migrations(conn)
            run_migrations(conn)
            after = conn.exec_driver_sql('SELECT * FROM scholars').fetchall()
            old, new = tuple(before[0]), tuple(after[0])
            columns = [row[1] for row in conn.exec_driver_sql('PRAGMA table_info(scholars)')]
            for field, old_value, new_value in zip(columns, old, new, strict=True):
                assert new_value == ("Faculty" if field == "personnel_type" else old_value + 1 if field == "revision" else old_value)
            names = {row[1] for row in conn.exec_driver_sql('PRAGMA index_list(scholars)')}
            assert 'uq_scholars_name' not in names and 'ix_scholars_name' in names
            conn.execute(Scholar.__table__.insert().values(id=10, name='Existing'))
            assert conn.exec_driver_sql('PRAGMA foreign_key_check').fetchall() == []
            assert conn.exec_driver_sql('SELECT high_water FROM scholar_id_counter').scalar() == 10
    finally:
        engine.dispose()


