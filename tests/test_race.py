import race
import json


def test_get_historical_races():
    _, total_races, _ = race.get_historical_races_by_page(1)
    races = race.get_historical_races()
    assert len(races) == total_races
    with open('races.json', 'w+') as outfile:
        outfile.write(json.dumps(races, indent=4))


def test_get_historical_race_page():
    races, total_races, page_num = race.get_historical_races_by_page(1)
    assert len(races) == 500
    assert total_races > 500
    assert page_num == 1
