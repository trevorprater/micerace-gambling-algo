import os
import pickle
import json
import sys
import logging
import math
from enum import Enum
from datetime import datetime
from multiprocessing import Pool
from random import randint

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


class MouseColors(Enum):
    brown = 1
    black = 2
    grey = 3
    gray = 3
    yellow = 4
    white = 5
    orange = 6
    silver = 7
    red = 8


class MouseNames(Enum):
    mario = 0
    gold = 1
    bulp = 2
    toast = 3
    scratch = 4
    mickey = 5
    robin = 6
    zeus = 7
    ester = 8
    bubu = 9
    greg = 10
    vinnie = 11
    cheddar = 12
    desperaux = 13
    fluffy = 14
    levi = 15
    nibbles = 16
    flamengo = 17
    bella = 18
    dagi = 19
    minnie = 20
    mama_mia = 21
    merlin = 22
    silver = 23
    york = 24
    scruffy = 25
    barbie = 26
    papa_grey = 27
    whiskers = 28
    coco = 29
    fortuna = 30
    snow = 31
    laila = 32
    hamish = 33
    mione = 34
    catnip = 35
    squeak = 36


def calc_elo_win_prob(opponent_elos, winner_elo):
    numerator = 0
    for elo in opponent_elos:
        numerator += 1/(1 + 10**(elo - winner_elo))
    denominator = ((len(opponent_elos)+1)*(len(opponent_elos)))/2)
    return numerator/denominator


@retry(requests.RequestException, tries=3, delay=1, backoff=1, jitter=1)
def get_all_races(use_cache, num_refresh_pages=5):
    all_races = {}
    # Get the total number of races the site contains.
    latest_races, num_total_races, _ = _get_historical_races_by_page(1)

    # Get the number of races contained in a page.
    page_size = len(latest_races)

    # Derive the number of pages of data:
    num_pages = int(math.ceil((num_total_races / page_size)))

    num_races_seen = 0
    if use_cache:
        all_races = pickle.load(open('pickles/races.pickle', 'rb'))
        for page_num in range(num_refresh_pages):
            races, _, _ = _get_historical_races_by_page(page_num)
            for race in races:

                if race['_id'] in all_races:
                    num_races_seen += 1
                all_races.update({race['_id']: race})

            if num_races_seen >= page_size:
                break

    else:
        # For each page, collect the race data from the HTTP endpoint:
        for races, _, page_num in Pool(NUM_HTTP_WORKERS).imap(_get_historical_races_by_page, range(1, num_pages+1)):
            for race in races:
                all_races.update({race['_id']: race})

    # Keep a backup ~5% of the time.
    if randint(1, 20) == 5:
        with open('pickles/races-{}.pickle'.format(datetime.strftime(datetime.utcnow(), '%Y-%m-%d-%H-%M-%S')), 'wb+') as outfile:
            pickle.dump(all_races, outfile)

    with open('pickles/races.pickle', 'wb+') as outfile:
        pickle.dump(all_races, outfile)

    return sorted(all_races.values(), key=lambda r: r['eventStart'], reverse=True)


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

