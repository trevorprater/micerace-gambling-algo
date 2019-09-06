from pprint import pprint
import json
from datetime import datetime, timedelta
from collections import OrderedDict

import requests
from retry import retry

from micerace.race import get_historical_races
from utils.util import LEADERBOARD_URL


#@retry(requests.RequestException, tries=5, delay=1, backoff=1, jitter=1)
def get_mice(target_mice=None, use_cache=False):
    r = requests.get(LEADERBOARD_URL)
    mice = json.loads(r.content.decode('utf-8'))['data']
    for m in mice:
        m.update({'name': m['name'].lower()})

    if target_mice is not None:
        mice = [OrderedDict(m) for m in mice if m['name'] in target_mice]
    else:
        mice = [OrderedDict(m) for m in mice if m['name']]

    for mouse in mice:
        mouse.update(
            OrderedDict({
                'name': mouse['name'].lower(),
                'win_ratio': round(mouse['countWinner']/float(mouse['totalGames']), 4),
                '1h_win_ratio': get_win_ratio_over_time(mouse, timedelta(hours=1), use_cache=use_cache),
                '2h_win_ratio': get_win_ratio_over_time(mouse, timedelta(hours=2), use_cache=use_cache),
                '3h_win_ratio': get_win_ratio_over_time(mouse, timedelta(hours=3), use_cache=use_cache),
                '6h_win_ratio': get_win_ratio_over_time(mouse, timedelta(hours=6), use_cache=use_cache),
                '12h_win_ratio': get_win_ratio_over_time(mouse, timedelta(hours=12), use_cache=use_cache),
                '24h_win_ratio': get_win_ratio_over_time(mouse, timedelta(hours=24), use_cache=use_cache),
                '30d_win_ratio': get_win_ratio_over_time(mouse, timedelta(days=30), use_cache=use_cache),
                '3m_win_ratio': get_win_ratio_over_time(mouse, timedelta(days=30*3), use_cache=use_cache),
                '6m_win_ratio': get_win_ratio_over_time(mouse, timedelta(days=30*6), use_cache=use_cache),
                '1y_win_ratio': get_win_ratio_over_time(mouse, timedelta(days=365), use_cache=use_cache),
            })
        )

    return mice


def get_win_ratio_over_time(mouse, delta, use_cache=False):
    now = datetime.utcnow()
    max_age = now - delta
    races_won = 0
    races_lost = 0
    races = get_historical_races(use_cache=use_cache)
    races_with_mouse = list(filter(lambda r: mouse['name'] in r['mice'], races))
    for race in races_with_mouse:
        # If race successfully completed:
        if race['completed'] and race['raceIsReset'] is False and race['raceCancelled'] is False:
            # If time criteria is met:
            if race['raceComplete'] >= max_age:
                # If mouse in race:
                if mouse['name'] in race['mice']:
                    if race['winnerName'] == mouse['name']:
                        races_won += 1
                    else:
                        races_lost += 1
    if races_won + races_lost == 0:
        return 0.0, 0
    return round((races_won/float(races_lost + races_won)), 2), races_won + races_lost


if __name__ == '__main__':
    mice = get_mice(['fluffy', 'zeus', 'merlin', 'gold'], use_cache=True)
    with open('calculations.json', 'w+') as outfile:
        outfile.write(json.dumps(mice, indent=4))
    pprint(mice)
    pass
