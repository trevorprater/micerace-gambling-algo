from enum import Enum
from datetime import datetime
from collections import OrderedDict
import statistics
import json


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


class Mouse:
    def __init__(self, **kwargs):
        self.name = kwargs['name'].lower()
        self.family = int(kwargs['family'])
        self.site_rating = kwargs['rating']
        self.color = kwargs['color'].lower()
        self.color_num = getattr(MouseColors, self.color).value

        self.kwargs = kwargs

        self.all_races = OrderedDict()
        self.winning_races = []
        self.losing_races = []
        self.completed_races = []
        self.reset_races = []
        self.cancelled_races = []

        self.__validate_data_integrity()

    @property
    def total_races_won(self):
        return len(self.winning_races)

    @property
    def total_races_lost(self):
        return len(self.losing_races)

    @property
    def total_races_completed(self):
        return len(self.completed_races)

    @property
    def lifetime_win_ratio(self):
        if self.total_races_won + self.total_races_lost == 0:
            return 0.0

        return round(self.total_races_won / float(self.total_races_lost), 4)

    @property
    def age(self):
        first_race = self.all_races[list(self.all_races.keys())[-1]]
        most_recent_race = self.all_races[list(self.all_races.keys())[0]]
        _age = (most_recent_race._event_starts_at - first_race._event_starts_at).days
        return _age

    def __validate_data_integrity(self):
        if not all([c.isdigit() for c in self.kwargs['family']]):
            raise Exception("Family value is not a number! Modify logic in code!")

    def add_race(self, race):
        if race.id in self.all_races:
            raise Exception(f"Race: {race.id} already associated with {self.name}")

        self.all_races[race.id] = race

        if race.completed:
            self.completed_races.append(race)
            if race.winner_name == self.name:
                self.winning_races.append(race)
            else:
                self.losing_races.append(race)

        if race.reset or race.cancelled:
            if race.reset:
                self.reset_races.append(race)
            if race.cancelled:
                self.cancelled_races.append(race.cancelled)

        if self.total_races_lost + self.total_races_won != self.total_races_completed:
            raise Exception(
                f"total_races_won ({self.total_races_won}) + total_races_lost ({self.total_races_lost}) "
                f"!= completed_races ({self.total_races_completed}) for {self.name}!")

    def _process_races(self):
        for race_id, race in self.all_races.items():

            if race.completed:
                self.completed_races.append(race)
                if race.winner == self.name:
                    self.winning_races.append(race)
                else:
                    self.losing_races.append(race)

            if race.reset:
                self.reset_races.append(race)
                continue

            if race.cancelled:
                self.cancelled_races.append(race.cancelled)
                continue

    def win_ratio_last_n_races(self, n):
        races_won = races_lost = 0
        for _, race in self.all_races.items():
            if n > 0:
                if race.winner_name == self.name:
                    races_won += 1
                else:
                    races_lost += 1
            n -= 1

        return round(races_won / float(races_won + races_lost), 2)

    def lane_win_ratios(self, time_delta=None):
        now = datetime.utcnow()
        if time_delta is None:
            max_race_age = datetime(year=2017, month=1, day=1)
        else:
            max_race_age = now - time_delta

        lane_ctr = [0, 0, 0, 0]
        for race in self.winning_races:
            if race.completed_at >= max_race_age:
                lane_ctr[race.mice_names.index(self.name)] += 1



        ratios = {
            #'blue': round(lane_ctr[0] / float(sum(lane_ctr)), 2),
            #'red': round(lane_ctr[1] / float(sum(lane_ctr)), 2),
            #'green': round(lane_ctr[2] / float(sum(lane_ctr)), 2),
            #'yellow': round(lane_ctr[3] / float(sum(lane_ctr)), 2),
        }

        # Add ratio of current lane
        if sum(lane_ctr) == 0:
            return 0.0
        current_race_lane = self.all_races[list(self.all_races.keys())[0]].mice_names.index(self.name)
        current_lane_ratio = round(lane_ctr[current_race_lane] / float(sum(lane_ctr)), 2)
        #ratios.update({'current_lane': round(lane_ctr[current_race_lane] / float(sum(lane_ctr)), 2)})
        #return ratios
        return current_lane_ratio

    def current_lane_total_win_ratio(self, time_delta=None):
        """In the current lane, what is the wins/total_races ratio?"""
        now = datetime.utcnow()
        if time_delta is None:
            max_race_age = datetime(year=2017, month=1, day=1)
        else:
            max_race_age = now - time_delta

        wins_in_lane = losses_in_lane = 0
        current_race_lane = self.all_races[list(self.all_races.keys())[0]].mice_names.index(self.name)

        for race in self.winning_races + self.losing_races:
            if race.completed_at >= max_race_age:
                if race.mice_names.index(self.name) == current_race_lane:
                    if race.winner_name == self.name:
                        wins_in_lane += 1
                    else:
                        losses_in_lane += 1

        if wins_in_lane + losses_in_lane == 0:
            return 0.0

        return round(wins_in_lane / float(losses_in_lane + wins_in_lane), 2)



    def win_ratio_since(self, time_delta):
        now = datetime.utcnow()
        max_race_age = now - time_delta

        races_won, races_lost = 0, 0

        for race in self.winning_races:
            if race.completed_at >= max_race_age:
                races_won += 1

        for race in self.losing_races:
            if race.completed_at >= max_race_age:
                races_lost += 1

        if races_won == 0:
            return 0.0, races_won, races_lost

        ratio = round(races_won / float(races_won+races_lost), 2)

        return ratio, races_won, races_lost

    def win_times_since(self, time_delta):
        now = datetime.utcnow()
        max_race_age = now - time_delta

        times = []
        for race in self.winning_races:
            if race.completed_at >= max_race_age:
                times.append(race.elapsed_time)

        stats = {
            #'min_t': min(times) if len(times) else None,
            #'max_t': max(times) if len(times) else None,
            'mean_t': round(statistics.mean(times), 2) if len(times) else None,
            'median_t': round(statistics.median(times), 2) if len(times) else None,
        }

        # TODO / NOTE removing None values for human-readability
        return {k: v for k, v in stats.items() if v is not None}

    def interval_stats(self, time_delta):
        win_ratio, races_won, races_lost = self.win_ratio_since(time_delta)
        stats = {
            'win_ratio': win_ratio,
            'win/total': f'{races_won}/{races_won + races_lost}' if races_lost > 0 else 0,
            'win_loss_current_lane': self.current_lane_total_win_ratio(time_delta),

            #'lane_stats': self.lane_win_ratios(time_delta=time_delta),
            **self.win_times_since(time_delta)
        }

        # Filter out zero values
        stats = {
            k: v for k, v in stats.items()
            if (isinstance(v, int) or isinstance(v, float) and v > 0) or isinstance(v, str) or k == 'win_loss_current_lane'}

        return str(stats)

