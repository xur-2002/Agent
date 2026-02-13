from agent.image_provider import provide_cover_image


def test_image_skip():
    material = {'sources': []}
    info = provide_cover_image(material, 'outputs/articles/2026-02-13', 'test-slug')
    assert info['image_status'] == 'skipped'
    assert 'reason' in info
