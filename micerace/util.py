import os
import pickle
import shutil
import json
import sys
import logging
import math
from datetime import datetime
from collections import OrderedDict
from multiprocessing import Pool

from retry import retry
import requests


_handler = logging.StreamHandler(stream=sys.stdout)
_handler.setLevel(logging.DEBUG)
LOGGER = logging.getLogger('micerace_logger')
LOGGER.addHandler(_handler)

BASE_URL = 'https://micerace.com'
HISTORICAL_RACES_URL = os.path.join(BASE_URL, 'games', 'allgames')
RACE_URL = os.path.join(BASE_URL, 'race')
LEADERBOARD_URL = os.path.join(RACE_URL, 'leaders')
NUM_HTTP_WORKERS = 3


class NoMoreRacesException(Exception):
    pass


def format_timestamp(ts):
    if ts is not None:
        return datetime.strptime(ts[:-1] + '000', '%Y-%m-%dT%H:%M:%S.%f')


# TODO CACHING
@retry(requests.RequestException, tries=3, delay=1, backoff=1, jitter=1)
def get_all_races(use_cache, num_refresh_pages):
    all_races = {}
    # Get the total number of races the site contains.
    latest_races, num_total_races, _ = _get_historical_races_by_page(1)

    # Get the number of races contained in a page.
    page_size = len(latest_races)

    # Derive the number of pages of data:
    num_pages = int(math.ceil((num_total_races / page_size)))

    # For each page, collect the race data from the HTTP endpoint:
    for races, _, page_num in Pool(NUM_HTTP_WORKERS).imap(_get_historical_races_by_page, range(1, num_pages+1)):
        for race in races:
            all_races.update({race['_id']: race})

    return sorted(all_races.values(), key=lambda r: r['eventStart'], reverse=True)


@retry(requests.RequestException, tries=3, delay=1, backoff=1, jitter=1)
def get_historical_races(use_cache=False, num_refresh_pages=5):
    all_races = OrderedDict()

    # # If we are using the cache, only request `num_refresh_pages` from the server, then return the updated cache.
    # if use_cache:
    #     with open('races.pickle', 'rb') as infile:
    #         all_races.update(pickle.load(infile))
    #         for page in range(1, num_refresh_pages+1):
    #             latest_races, _, _ = _get_historical_races_by_page(page)
    #             for race in latest_races:
    #                 all_races.update({race['_id']: clean_race_data(race)})
    #         return all_races

    # Get the total number of races the site contains.
    latest_races, num_total_races, _ = _get_historical_races_by_page(1)

    # Get the number of races contained in a page.
    page_size = len(latest_races)

    # Derive the number of pages of data:
    num_pages = int(math.ceil((num_total_races / page_size)))

    # For each page, collect the race data from the HTTP endpoint:
    for races, _, page_num in Pool(NUM_HTTP_WORKERS).imap(_get_historical_races_by_page, range(1, num_pages+1)):
        for race in races:
            all_races.update({race['_id']: clean_race_data(race)})

    # Write fresh data to the cache.
    if os.path.exists('races.pickle'):
        shutil.copy('races.pickle', 'races.pickle.backup')

    with open('races.pickle', 'wb+') as outfile:
        pickle.dump(all_races, outfile)

    return all_races


@retry(requests.RequestException, tries=3, delay=1, backoff=1, jitter=1)
def _get_historical_races_by_page(page_num):
    LOGGER.info("Request historical races via page {}".format(page_num))
    resp = requests.get(HISTORICAL_RACES_URL, params={'pageIndex': page_num})
    data = json.loads(resp.content.decode('utf-8'))
    if not len(data):
        e = NoMoreRacesException('Cannot find any races on page {}'.format(page_num))
        LOGGER.exception('No races returned', exc_info=e)
    return data['games'], data['total'], page_num


@retry(requests.RequestException, tries=3, delay=1, backoff=1, jitter=1)
def get_mice_data(target_mice_names=None):
    mice_data = json.loads(requests.get(LEADERBOARD_URL).content.decode('utf-8'))['data']
    for mouse_metadata in mice_data:
        mouse_metadata['name'] = mouse_metadata['name'].lower()
    return mice_data


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
