import math

import pytest
from fastapi.testclient import TestClient

from app import main, storage
from app.subtitles import normalize_timings, parse_subtitles, translated_srt


def cue(identity, start, end, text='Hello'):
    return dict(id=identity, start=start, end=end, source=text)


def test_overlap_example_keeps_starts_text_and_final_end():
    cues = [cue(1, 35.120, 41), cue(2, 38.120, 43.960), cue(3, 41, 46.520)]
    output = translated_srt(cues, {'1': 'Մեկ', '2': 'Երկու', '3': 'Երեք'})
    parsed = parse_subtitles(output.encode())
    assert [(c['start'], c['end']) for c in parsed] == [(35.120, 38.120), (38.120, 41), (41, 46.520)]
    assert [c['source'] for c in parsed] == ['Մեկ', 'Երկու', 'Երեք']
    assert cues[0]['end'] == 41


def test_equal_starts_merge_in_order_keep_latest_end_and_preserve_gaps():
    cues = [cue(8, 1, 2), cue(9, 1, 5), cue(10, 4, 6), cue(11, 8, 9)]
    output = translated_srt(cues, {'8': 'Ա', '9': 'Բ', '10': 'Գ', '11': 'Դ'})
    parsed = parse_subtitles(output.encode())
    assert [(c['start'], c['end'], c['source']) for c in parsed] == [(1, 4, 'Ա\nԲ'), (4, 6, 'Գ'), (8, 9, 'Դ')]
    assert [block.splitlines()[0] for block in output.strip().split('\n\n')] == ['1', '2', '3']
    final = normalize_timings([cue(1, 2, 3, 'A'), cue(2, 2, 7, 'B')])
    assert final[0]['end'] == 7 and final[0]['source'] == 'A\nB'


@pytest.mark.parametrize('cues', [
    [cue(1, 1, 1)], [cue(1, 2, 1)], [cue(1, -1, 2)],
    [cue(1, math.nan, 2)], [cue(1, 1, math.inf)],
    [cue(1, 2, 3), cue(2, 1, 4)],
    [cue(1, 1, 2), cue(2, 1.0001, 3)],
])
def test_malformed_timing_is_reported(cues):
    with pytest.raises(ValueError, match='cue'):
        translated_srt(cues, {str(c['id']): 'Տեքստ' for c in cues})


def test_zero_duration_source_dialogue_is_not_silently_dropped():
    with pytest.raises(ValueError, match='cue 42'):
        parse_subtitles(b'42\n00:00:01,000 --> 00:00:01,000\nDialogue', allow_empty_cues=True)


def test_existing_library_downloads_are_normalized_on_both_routes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'library.sqlite3')
    text = '8\n00:00:01,000 --> 00:00:05,000\n<b>Հայերեն</b>\n\n9\n00:00:03,000 --> 00:00:06,000\nԵրկու\n'
    storage.save_library_translation(dict(file_identity='old', filename='old.srt', cues=[{}, {}]), text)
    with TestClient(main.app) as client:
        for route in ('/api/library/old/download', '/api/subtitle-files/old/download'):
            response = client.get(route)
            assert response.status_code == 200
            assert response.content.startswith(b'\xef\xbb\xbf')
            parsed = parse_subtitles(response.content, preserve_text=True)
            assert parsed[0]['source'] == '<b>Հայերեն</b>'
            assert all(c['start'] < c['end'] for c in parsed)
            assert all(a['end'] <= b['start'] for a, b in zip(parsed, parsed[1:]))
        with storage.connect() as db:
            db.execute("UPDATE subtitle_library SET srt=? WHERE id='old'", ('1\n00:00:02,000 --> 00:00:01,000\nText',))
        response = client.get('/api/library/old/download')
        assert response.status_code == 422 and 'cue 1' in response.json()['detail']
