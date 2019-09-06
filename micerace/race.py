import os
import pickle
import shutil
import json
import math
from collections import OrderedDict
from multiprocessing.pool import Pool

import requests
from retry import retry

from utils import clean_race_data
from utils import HISTORICAL_RACES_URL
from utils import LOGGER

NUM_WORKERS = 10


class NoMoreRacesException(Exception):
    pass


def get_historical_races(use_cache=False):
    if use_cache:
        with open('races.pickle', 'rb') as infile:
            return pickle.load(infile)
    all_races = []
    _races, num_total_races, _ = get_historical_races_by_page(1)
    page_size = len(_races)
    num_pages = int(math.ceil((num_total_races / page_size)))
    for races, _, page_num in Pool(NUM_WORKERS).imap(
            get_historical_races_by_page, range(1, num_pages+1)):
        for race in races:
            all_races.append(clean_race_data(race))
    if os.path.exists('races.pickle'):
        shutil.copy('races.pickle', 'races.pickle.backup')
    with open('races.pickle', 'wb+') as outfile:
        pickle.dump(all_races, outfile)

    return all_races


@retry(requests.RequestException, tries=3, delay=1, backoff=1, jitter=1)
def get_historical_races_by_page(page_num):
    LOGGER.info("Request historical races via page {}".format(page_num))
    resp = requests.get(HISTORICAL_RACES_URL, params={'pageIndex': page_num})
    data = json.loads(resp.content.decode('utf-8'))
    if not len(data):
        e = NoMoreRacesException('Cannot find any races on page {}'.format(page_num))
        LOGGER.exception('No races returned', exc_info=e)
    return data['games'], data['total'], page_num


if __name__ == '__main__':
    races = get_historical_races(use_cache=True)
    pass
