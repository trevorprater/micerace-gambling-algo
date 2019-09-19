import sys
import random
import shutil
import json
from datetime import datetime
from csv import DictWriter
from collections import OrderedDict, defaultdict
from datetime import timedelta
from lazy import lazy

import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

from micerace.mice import Mouse
from micerace import util

NUM_SKIP_INITIAL_RACES = 2000


class Race:
    def __init__(self, **kwargs):
        self.id = kwargs['_id']
        self.log = kwargs['log']
        self.__v = kwargs['__v']

        self._event_starts_at = util.format_timestamp(kwargs.get('eventStart', None))
        self.staging_at = util.format_timestamp(kwargs.get('staging', None))
        self.betting_opens_at = util.format_timestamp(kwargs.get('bettingOpens', None))
        self.starts_at = util.format_timestamp(kwargs.get('raceStarts', None))

        self.completed_at = util.format_timestamp(kwargs.get('raceComplete', None))
        self.reset = kwargs['raceIsReset']
        self.cancelled = kwargs['raceCancelled']

        self.completed = True if self.completed_at and not self.reset and not self.cancelled else False
        if self.completed_at and self.starts_at:
            delta = self.completed_at - self.starts_at
            self.elapsed_time = delta.seconds + delta.microseconds/1000000
        else:
            self.elapsed_time = None

        self.mice_names = [name.lower().replace('-', '_') for name in kwargs['mice']]
        self.winner_name = kwargs.get('winnerName', None)
        if self.winner_name is not None:
            self.winner_name = self.winner_name.lower().replace('-', '_')
            self.winner_name_id = getattr(util.MouseNames, self.winner_name).value
            self.winner_position_ndx = self.mice_names.index(self.winner_name)

        self.runner_up_name = kwargs.get('runnerUpName', None)
        if isinstance(self.runner_up_name, str):
            self.runner_up_name = self.runner_up_name.lower()
            if self.runner_up_name is 'null':
                self.runner_up_name = None


class MouseKeeper(dict):
    def get(self, mouse_name, default=None) -> Mouse:
        return super().get(mouse_name, default)


class MiceRaceSystem:
    def __init__(self,
                 use_cache=False,
                 num_refresh_pages=10,
                 cache_pickle_file='races.pickle',
                 target_mice_names=None,
                 **kwargs):

        self.use_cache = use_cache
        self.cache_pickle_file = cache_pickle_file
        self.num_refresh_pages = num_refresh_pages
        self.dead_mice = set()

        # Get the races
        self.target_mice_names = [name.replace('-', '_') for name in target_mice_names]
        self.mice_metadata = util.get_mice_data()

        # Create a reverse lookup table that allows us to quickly find a mouse by name, because for each race,
        # we must associate it to four different mice (Mouse objects).
        self.mice = MouseKeeper({mouse['name'].replace('-', '_'): Mouse(**mouse) for mouse in self.mice_metadata})
        self.races = []
        http_races = util.get_all_races(use_cache=self.use_cache, num_refresh_pages=self.num_refresh_pages)
        http_races.reverse()
        for race_meta in http_races[NUM_SKIP_INITIAL_RACES:]:
            race = Race(**race_meta)
            self.races.append(race)
            for mouse_name in race.mice_names:
                if mouse_name not in self.mice:
                    self.dead_mice.add(mouse_name)
                else:
                    self.mice[mouse_name].add_race(race)

    @property
    def num_actual_races(self):
        return len(self.races)

    @property
    def latest_race(self):
        return self.races[-1]


class HistoricalMiceRaceSystem:
    def __init__(self, num_primer_races, **kwargs):
        self.mice_metadata = util.get_mice_data()
        self.mice = MouseKeeper({mouse['name']: Mouse(**mouse) for mouse in self.mice_metadata})
        self.dead_mice = set()
        self._true_races = [Race(**race_meta) for race_meta in
                            util.get_all_races(use_cache=False, num_refresh_pages=100)]
        self._true_races = [r for r in self._true_races if r.completed_at and r.winner_name and len(r.winner_name) and not any(mn for mn in r.mice_names if mn in self.dead_mice)]
        self._true_races.sort(key=lambda r: r.completed_at)

        self.num_primer_races = num_primer_races
        self.current_race_offset = 0
        self.races = []

        while self.current_race_offset < self.num_primer_races:
            self.ingest_new_race()

    def ingest_new_race(self):
        self.races.append(self._true_races[self.current_race_offset])
        self.current_race_offset += 1
        for mouse_name in self.races[-1].mice_names:
            if mouse_name not in self.mice:
                self.dead_mice.add(mouse_name)
            else:
                self.mice[mouse_name].add_race(self.races[-1])

    @property
    def num_actual_races(self):
        return len(self._true_races)

    @property
    def latest_race(self):
        return self.races[-1]


class StatsAgent:
    def __init__(self,
                 use_cache=False,
                 num_refresh_pages=1,
                 training=False,
                 num_primer_races=NUM_SKIP_INITIAL_RACES, **kwargs):

        if training:
            self.system = HistoricalMiceRaceSystem(
                use_cache=use_cache, num_refresh_pages=num_refresh_pages, num_primer_races=num_primer_races)
        else:
            self.system = MiceRaceSystem(
                use_cache=use_cache, num_refresh_pages=num_refresh_pages, target_mice_names=[], **kwargs)

        self.num_primer_races = num_primer_races
        #TODO: ADD BACK#self.model = load_model('models/model-latest.h5')
        self.model = load_model('models/model-latest.h5')

    def predict_current_race(self):
        output_dict = OrderedDict()
        race_stats = self.get_mice_stats(self.system.latest_race.mice_names)

        now = datetime.utcnow()
        output_dict['completed_at_year'] = getattr(self.system.latest_race.completed_at, 'year', now.year)
        output_dict['completed_at_month'] = getattr(self.system.latest_race.completed_at, 'month', now.month)
        output_dict['completed_at_day'] = getattr(self.system.latest_race.completed_at, 'day', now.day)
        if hasattr(self.system.latest_race.completed_at, 'weekday'):
            output_dict['completed_at_weekday'] = self.system.latest_race.completed_at.weekday()
        else:
            output_dict['completed_at_weekday'] = now.weekday()

        output_dict['completed_at_hour'] = getattr(self.system.latest_race.completed_at, 'hour', now.hour)
        output_dict['completed_at_minute'] = getattr(self.system.latest_race.completed_at, 'minute', now.minute)

        for mouse_num, mouse_stats in enumerate(race_stats):
            for k, v in mouse_stats.items():
                output_dict[f"mouse_{mouse_num}_{k}"] = v

        all_stats = [output_dict]
        df = pd.DataFrame(all_stats).fillna(value=0)
        names_1 =\
            [list(df['mouse_0_name'])[0],
             list(df['mouse_1_name'])[0],
             list(df['mouse_2_name'])[0],
             list(df['mouse_3_name'])[0]]

        df = df.drop(
            columns=['mouse_0_name',
                     'mouse_1_name',
                     'mouse_2_name',
                     'mouse_3_name'])

        race_stats_np_arr = df.to_numpy(dtype=float)
        race_stats_np_arr = np.expand_dims(race_stats_np_arr, axis=2)

        predict = self.model.predict(race_stats_np_arr, verbose=0)
        print(dict(zip(self.system.latest_race.mice_names, [round(p, 2) for p in predict[0]]))))

        if self.system.latest_race.completed:
            print(self.system.latest_race.winner_name, self.system.latest_race.winner_position_ndx)


    def build_training_data(self):
        csv_headers_written = False

        shutil.copy('training_data/training-latest.csv', 'training_data/training-data-backup.csv')
        with open(f'training_data/training-latest.csv', 'w+') as csv_out:
            dw = DictWriter(csv_out, fieldnames=[])
            all_stats = []
            for ctr in range(self.num_primer_races, self.system.num_actual_races):
                if ctr % 100 == 0:
                    print(f'processed {ctr} races')
                if not any(mn for mn in self.system.latest_race.mice_names if mn in self.system.dead_mice):
                    output_dict = OrderedDict()
                    race_stats = self.get_mice_stats(self.system.latest_race.mice_names)

                    output_dict['mice'] = self.system.latest_race.mice_names
                    output_dict['winner_name'] = self.system.latest_race.winner_name
                    output_dict['winner_name_id'] = self.system.latest_race.winner_name_id
                    output_dict['winner_position_ndx'] = self.system.latest_race.winner_position_ndx
                    output_dict['race_id'] = self.system.latest_race.id

                    output_dict['completed_at_year'] = self.system.latest_race.completed_at.year
                    output_dict['completed_at_month'] = self.system.latest_race.completed_at.month
                    output_dict['completed_at_day'] = self.system.latest_race.completed_at.day
                    output_dict['completed_at_weekday'] = self.system.latest_race.completed_at.weekday()
                    output_dict['completed_at_hour'] = self.system.latest_race.completed_at.hour
                    output_dict['completed_at_minute'] = self.system.latest_race.completed_at.minute

                    for mouse_num, mouse_stats in enumerate(race_stats):
                        for k, v in mouse_stats.items():
                            output_dict[f"mouse_{mouse_num}_{k}"] = v

                    if not csv_headers_written:
                        dw.fieldnames = list(output_dict.keys())
                        dw.writeheader()
                        dw.writerow(output_dict)
                        csv_headers_written = True
                        all_stats.append(output_dict)
                    else:
                        all_stats.append(output_dict)
                        dw.writerow(output_dict)

                self.system.ingest_new_race()

    def lane_win_ratios(self):
        races_by_lane = defaultdict(int)
        for race in self.system.races:
            if race.completed and race.winner_name is not None:
                if race.mice_names.index(race.winner_name) == 0:
                    races_by_lane['blue'] += 1
                elif race.mice_names.index(race.winner_name) == 1:
                    races_by_lane['red'] += 1
                elif race.mice_names.index(race.winner_name) == 2:
                    races_by_lane['green'] += 1
                else:
                    races_by_lane['yellow'] += 1

        races_by_lane = {k: round(v/float(sum(races_by_lane.values())), 5) for k, v in races_by_lane.items()}
        return races_by_lane

    def get_mice_stats(self, target_mice_names=None):
        intervals = [
            ('1h', timedelta(hours=1)),
            ('2h', timedelta(hours=2)),
            ('3h', timedelta(hours=3)),
            ('4h', timedelta(hours=5)),
            ('6h', timedelta(hours=6)),
            ('8h', timedelta(hours=8)),
            ('12h', timedelta(hours=12)),
            ('18h', timedelta(hours=18)),
            ('24h', timedelta(hours=24)),
            ('36h', timedelta(hours=36)),
            ('2d', timedelta(days=2)),
            ('3d', timedelta(days=3)),
            ('5d', timedelta(days=5)),
            ('7d', timedelta(days=7)),
            ('10d', timedelta(days=10)),
            ('15d', timedelta(days=15)),
            ('30d', timedelta(days=30)),
            ('45d', timedelta(days=45)),
            ('60d', timedelta(days=60)),
            ('75d', timedelta(days=75)),
            ('90d', timedelta(days=90)),
        ]
        if target_mice_names is None:
            target_mice_names = self.system.mice.keys()

        mice_stats = []
        for mouse_name in target_mice_names:
            mouse = self.system.mice.get(mouse_name)
            mouse.populate_global_stats()

            mouse_stats = OrderedDict({
                'name': mouse.name,
                'name_id': mouse.name_id,
                'site_rating': mouse.site_rating,
                'lifetime_win_ratio': mouse.lifetime_win_ratio,
                'win_loss_current_lane': mouse.current_lane_total_win_ratio(),
                'curr_repeat_wins': mouse.current_repeat_wins,
                'average_repeat_wins': mouse.average_repeat_wins,
                'max_repeat_wins': mouse.max_repeat_wins,
                **mouse.lane_win_vs_other_lane_ratio(),
                **dict(zip(['5_race_wins', '5_race_loss'], mouse.win_ratio_last_n_races(5))),
                **dict(zip(['10_race_wins', '10_race_loss'], mouse.win_ratio_last_n_races(10))),
                **dict(zip(['15_race_wins', '15_race_loss'], mouse.win_ratio_last_n_races(15))),
                **dict(zip(['25_race_wins', '25_race_loss'], mouse.win_ratio_last_n_races(25))),
                **dict(zip(['30_race_wins', '30_race_loss'], mouse.win_ratio_last_n_races(30))),
                **dict(zip(['35_race_wins', '35_race_loss'], mouse.win_ratio_last_n_races(35))),
                **dict(zip(['50_race_wins', '50_race_loss'], mouse.win_ratio_last_n_races(50))),
                **dict(zip(['75_race_wins', '75_race_loss'], mouse.win_ratio_last_n_races(75))),
                **dict(zip(['75_race_wins', '75_race_loss'], mouse.win_ratio_last_n_races(75))),
                **dict(zip(['100_race_wins', '100_race_loss'], mouse.win_ratio_last_n_races(100))),
                **dict(zip(['125_race_wins', '125_race_loss'], mouse.win_ratio_last_n_races(125))),
                **dict(zip(['150_race_wins', '150_race_loss'], mouse.win_ratio_last_n_races(150))),
                **dict(zip(['200_race_wins', '200_race_loss'], mouse.win_ratio_last_n_races(200))),
                **dict(zip(['250_race_wins', '250_race_loss'], mouse.win_ratio_last_n_races(250))),
                **dict(zip(['300_race_wins', '300_race_loss'], mouse.win_ratio_last_n_races(300))),
                **dict(zip(['350_race_wins', '350_race_loss'], mouse.win_ratio_last_n_races(350))),
                **dict(zip(['400_race_wins', '400_race_loss'], mouse.win_ratio_last_n_races(400))),
                **dict(zip(['450_race_wins', '450_race_loss'], mouse.win_ratio_last_n_races(450))),
                **dict(zip(['500_race_wins', '500_race_loss'], mouse.win_ratio_last_n_races(500))),
                **dict(zip(['5_race_lane_wins', '5_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=5))),
                **dict(zip(['10_race_lane_wins', '10_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=10))),
                **dict(zip(['15_race_lane_wins', '15_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=15))),
                **dict(zip(['25_race_lane_wins', '25_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=25))),
                **dict(zip(['35_race_lane_wins', '35_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=35))),
                **dict(zip(['50_race_lane_wins', '50_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=50))),
                **dict(zip(['75_race_lane_wins', '75_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=75))),
                **dict(zip(['100_race_lane_wins', '100_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=100))),
                **dict(zip(['150_race_lane_wins', '150_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=150))),
                **dict(zip(['175_race_lane_wins', '175_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=175))),
                **dict(zip(['200_race_lane_wins', '200_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=200))),
                **dict(zip(['250_race_lane_wins', '250_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=250))),
                **dict(zip(['300_race_lane_wins', '300_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=300))),
                **dict(zip(['375_race_lane_wins', '375_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=375))),
                **dict(zip(['500_race_lane_wins', '500_race_lane_loss'], mouse.current_lane_total_win_ratio(num_races=500))),
            })

            for interval_str, interval in intervals:
                interval_stats = mouse.interval_stats(interval)
                for k, v in interval_stats.items():
                    mouse_stats.update({f'{interval_str}_{k}': v})

            mouse_stats.update(self.lane_win_ratios())
            mice_stats.append(mouse_stats)

        return sorted(mice_stats, key=lambda k: k['site_rating'], reverse=True)


def predict_current_race():
    stats_agent = StatsAgent(
        use_cache=True, training=False, num_refresh_pages=20, num_primer_races=NUM_SKIP_INITIAL_RACES)
    stats_agent.predict_current_race()


def build_training_data():
    stats_agent = StatsAgent(use_cache=True, training=True, num_primer_races=NUM_SKIP_INITIAL_RACES)
    stats_agent.build_training_data()


def eyeball_current_race_stats():
    stats_agent = StatsAgent(use_cache=True, training=False, num_primer_races=NUM_SKIP_INITIAL_RACES)
    stats = stats_agent.get_mice_stats(stats_agent.system.races[0].mice_names)
    print(json.dumps(stats, indent=2))
    with open('latest-stats.json', 'w+') as outfile:
        outfile.write(json.dumps(stats, indent=2))


if __name__ == '__main__':
    if sys.argv[0] == 'predict':
        predict_current_race()
    elif sys.argv[1] == 'train':
        build_training_data()
    else:
        eyeball_current_race_stats()

