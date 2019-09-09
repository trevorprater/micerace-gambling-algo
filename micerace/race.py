import json
from collections import OrderedDict, defaultdict
from datetime import timedelta

from micerace.mice import Mouse
from micerace import util


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

        self.mice_names = [name.lower() for name in kwargs['mice']]
        self.winner_name = kwargs.get('winnerName', None)
        if self.winner_name is not None:
            self.winner_name = self.winner_name.lower()

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
        self.target_mice_names = target_mice_names
        self.mice_metadata = util.get_mice_data()

        # Create a reverse lookup table that allows us to quickly find a mouse by name, because for each race,
        # we must associate it to four different mice (Mouse objects).
        self.mice = MouseKeeper({mouse['name']: Mouse(**mouse) for mouse in self.mice_metadata})
        self.races = []
        for race_meta in util.get_all_races(use_cache=self.use_cache, num_refresh_pages=self.num_refresh_pages):
            race = Race(**race_meta)
            self.races.append(race)
            for mouse_name in race.mice_names:
                if mouse_name not in self.mice:
                    self.dead_mice.add(mouse_name)
                else:
                    self.mice[mouse_name].add_race(race)


class StatsAgent:
    def __init__(self, use_cache=False, num_refresh_pages=10, **kwargs):
        self.system = MiceRaceSystem(
            use_cache=use_cache, num_refresh_pages=num_refresh_pages, **kwargs)

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
            ('8h', timedelta(hours=8)),
            ('12h', timedelta(hours=12)),
            ('24h', timedelta(hours=24)),
            ('2d', timedelta(days=2)),
            ('3d', timedelta(days=3)),
            ('6d', timedelta(days=5)),
            ('10d', timedelta(days=10)),
            ('30d', timedelta(days=30)),
            ('60d', timedelta(days=60)),
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
                'site_rating': mouse.site_rating,
                'lifetime_win_ratio': mouse.lifetime_win_ratio,
                'wins_in_lane_vs_others': mouse.lane_win_vs_other_lane_ratio(),
                'win_loss_current_lane': mouse.current_lane_total_win_ratio(),
                'curr_repeat_wins': mouse.current_repeat_wins,
                'average_repeat_wins': mouse.average_repeat_wins,
                'max_repeat_wins': mouse.max_repeat_wins,
                '5_race_win_ratio': mouse.win_ratio_last_n_races(5),
                '10_race_win_ratio': mouse.win_ratio_last_n_races(10),
                '25_race_win_ratio': mouse.win_ratio_last_n_races(25),
                '50_race_win_ratio': mouse.win_ratio_last_n_races(50),
                '100_race_win_ratio': mouse.win_ratio_last_n_races(100),
                '5_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=5),
                '10_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=10),
                '25_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=25),
                '50_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=50),
                '100_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=100),
                '250_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=250),
                '500_race_lane_win_ratio': mouse.current_lane_total_win_ratio(num_races=500),
            })

            for interval_str, interval in intervals:
                mouse_stats.update({interval_str: mouse.interval_stats(interval)})

            mouse_stats.update(self.lane_win_ratios())

            mice_stats.append(mouse_stats)

        return sorted(mice_stats, key=lambda k: k['site_rating'], reverse=True)


if __name__ == '__main__':
    stats_agent = StatsAgent(use_cache=False)
    stats = stats_agent.get_mice_stats(stats_agent.system.races[0].mice_names)
    print(json.dumps(stats, indent=2))
    with open('latest-stats.json', 'w+') as outfile:
        outfile.write(json.dumps(stats, indent=2))
