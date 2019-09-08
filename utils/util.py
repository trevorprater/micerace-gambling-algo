import os
import sys
import logging
from datetime import datetime

_handler = logging.StreamHandler(stream=sys.stdout)
_handler.setLevel(logging.DEBUG)
LOGGER = logging.getLogger('micerace_logger')
LOGGER.addHandler(_handler)

BASE_URL = 'https://micerace.com'
HISTORICAL_RACES_URL = os.path.join(BASE_URL, 'games', 'allgames')
RACE_URL = os.path.join(BASE_URL, 'race')
LEADERBOARD_URL = os.path.join(RACE_URL, 'leaders')


def clean_race_data(race):
    race.update({'mice': [mouse.strip().lower() for mouse in race['mice']]})
    for k, v in list(race.items()):
        if isinstance(v, str) and v.endswith('Z'):
            pass
        else:
            continue
        try:
            race[k] = \
                datetime.strptime(race[k][:-1] + '000', '%Y-%m-%dT%H:%M:%S.%f')
        except Exception as e:
            raise e
        race['mice'] = [m.lower() for m in race['mice']]
        race['completed'] = True if 'raceComplete' in race.keys() else False
        if 'winnerName' in race and race['winnerName'] is not None:
            race['winnerName'] = race['winnerName'].lower()

        if race[k] == 'none':
            race[k] = None

    return race
#
# def calc_elo_win_prob(opponent_elos, winner_elo):
#     numerator = 0
#     for elo in opponent_elos:
#         numerator += 1/(1 + 10**(elo - winner_elo))
#     denominator = ((len(opponent_elos)+1)*(len(opponent_elos)))/2)
#     return numerator/denominator
#
#
# if __name__ == '__main__':
#     base_mouse_elo = 1416
#     opponent_elos = [1614, 1504, 1456]
#     print(round(calc_elo_win_prob(opponent_elos, base_mouse_elo),2))
#
