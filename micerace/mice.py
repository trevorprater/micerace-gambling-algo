import statistics
from datetime import datetime

from .util import MouseNames, MouseColors
from datetime import timedelta


class Mouse:
    def __init__(self, **kwargs):
        self.name = kwargs['name'].lower().replace('-', '_')
        self.name_id = getattr(MouseNames, self.name).value
        self.family = int(kwargs['family'])
        self.site_rating = kwargs['rating']
        self.color = kwargs['color'].lower()
        self.color_num = getattr(MouseColors, self.color).value

        self.kwargs = kwargs

        self.all_races = []
        self.winning_races = []
        self.losing_races = []
        self.completed_races = []
        self.reset_races = []
        self.cancelled_races = []

        self.max_repeat_wins = 0
        self.average_repeat_wins = 0
        self.median_repeat_wins = 0
        self.current_repeat_wins = 0

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

        return self.total_races_won / float(self.total_races_won + self.total_races_lost)

    @property
    def age(self):
        first_race = self.all_races[0]
        most_recent_race = self.all_races[-1]
        _age = (most_recent_race._event_starts_at - first_race._event_starts_at).days
        return _age

    def __validate_data_integrity(self):
        if not all([c.isdigit() for c in self.kwargs['family']]):
            raise Exception("Family value is not a number! Modify logic in code!")

    def add_race(self, race):
        self.all_races.append(race)

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

    def win_ratio_last_n_races(self, n):
        races_won = races_lost = 0
        for race in self.all_races[::-1]:
            if n > 0:
                if race.winner_name == self.name:
                    races_won += 1
                else:
                    races_lost += 1
            n -= 1

        return races_won, races_lost

    def lane_win_vs_other_lane_ratio(self, time_delta=None):
        now = self.all_races[-1]._event_starts_at
        if time_delta is None:
            max_race_age = datetime(year=2017, month=1, day=1)
        else:
            max_race_age = now - time_delta

        lane_ctr = [0, 0, 0, 0]
        for race in self.winning_races[::-1]:
            if race.completed_at >= max_race_age:
                lane_ctr[race.mice_names.index(self.name)] += 1

        ratios = {
            'blue_lane_ratio': lane_ctr[0] / float(max(sum(lane_ctr), 1)),
            'red_lane_ratio': lane_ctr[1] / float(max(sum(lane_ctr), 1)),
            'green_lane_ratio': lane_ctr[2] / float(max(sum(lane_ctr), 1)),
            'yellow_lane_ratio': lane_ctr[3] / float(max(sum(lane_ctr), 1)),
        }
        current_race_lane = self.all_races[-1].mice_names.index(self.name)
        ratios.update({'current_lane_ratio': lane_ctr[current_race_lane] / float(max(sum(lane_ctr), 1))})
        return ratios



    def current_lane_total_win_ratio(self, time_delta=None, num_races=99999999):
        """In the current lane, what is the wins/total_races ratio?"""
        now = self.all_races[-1]._event_starts_at
        if time_delta is None:
            max_race_age = datetime(year=2017, month=1, day=1)
        else:
            max_race_age = now - time_delta

        wins_in_lane = losses_in_lane = 0
        current_race_lane = self.all_races[-1].mice_names.index(self.name)

        for race in self.completed_races[::-1]:
            if num_races == 0:
                break
            if race.completed_at >= max_race_age and race.winner_name is not None:
                if race.mice_names.index(self.name) == current_race_lane:
                    if race.winner_name == self.name:
                        wins_in_lane += 1
                    else:
                        losses_in_lane += 1
            num_races -= 1

        return (wins_in_lane, losses_in_lane)

        #if wins_in_lane + losses_in_lane == 0:
        #    return 0.0

        #return wins_in_lane / float(losses_in_lane + wins_in_lane)

    def win_ratio_since(self, time_delta):
        now = self.all_races[-1]._event_starts_at
        max_race_age = now - time_delta

        races_won, races_lost = 0, 0

        for race in self.winning_races[::-1]:
            if race.completed_at >= max_race_age:
                races_won += 1

        for race in self.losing_races[::-1]:
            if race.completed_at >= max_race_age:
                races_lost += 1

        if races_won == 0:
            return 0.0, races_won, races_lost

        ratio = races_won / float(races_won+races_lost)

        return ratio, races_won, races_lost

    def win_times_since(self, time_delta: timedelta):
        now = self.all_races[-1]._event_starts_at
        max_race_age = now - time_delta

        times = []

        while True:
            for race in self.winning_races[::-1]:
                if race.completed_at >= max_race_age:
                    times.append(race.elapsed_time)
            else:
                if not len(times):
                    max_race_age = (max_race_age - timedelta(hours=1))
                else:
                    break

        stats = {
            'min_t': min(times) if len(times) else None,
            'max_t': max(times) if len(times) else None,
            'mean_t': round(statistics.mean(times), 2) if len(times) else None,
            'median_t': round(statistics.median(times), 2) if len(times) else None,
        }

        return stats

    def repeat_wins(self, time_delta=None):
        now = self.all_races[-1]._event_starts_at
        if time_delta is None:
            max_race_age = datetime(year=2017, month=1, day=1)
        else:
            max_race_age = now - time_delta

        curr_repeat_wins = 0
        repeat_win_ctr = 0
        repeat_win_counts = []
        races_lost = 0

        for ctr, race in enumerate(self.completed_races[::-1]):
            if race.completed_at >= max_race_age and race.winner_name is not None:
                if race.winner_name == self.name:
                    repeat_win_ctr += 1
                    if races_lost == 0:
                        curr_repeat_wins += 1
                # If mouse lost
                else:
                    # If mouse on a repeat win streak, reset repeat wins and add repeat win count to the list.
                    if repeat_win_ctr > 0:
                        repeat_win_counts.append(repeat_win_ctr)
                        repeat_win_ctr = 0
                    races_lost += 1
        else:
            if repeat_win_ctr > 0:
                repeat_win_counts.append(repeat_win_ctr)

        if not len(repeat_win_counts):
            average_repeat_wins = 0.0
            median_repeat_wins = 0.0
            max_repeat_wins = 0.0
        else:
            average_repeat_wins = sum(repeat_win_counts) / float(len(repeat_win_counts))
            median_repeat_wins = statistics.median(repeat_win_counts)
            max_repeat_wins = max(repeat_win_counts)

        # Add global stats (all races) to the mouse
        if time_delta is None:
            self.current_repeat_wins = curr_repeat_wins
            self.average_repeat_wins = average_repeat_wins
            self.median_repeat_wins = median_repeat_wins
            self.max_repeat_wins = max_repeat_wins

        return {
            #'current_repeat_wins': self.current_repeat_wins,
            'avg_repeat_w': average_repeat_wins,
            'median_repeat_w': median_repeat_wins,
            'max_repeat_w': max_repeat_wins,
        }

    def get_average_repeat_wins(self, time_delta):
        return self.repeat_wins(time_delta)['avg_repeat_w']

    def populate_global_stats(self):
        pass
        #self.repeat_wins()

    def interval_stats(self, time_delta):
        win_ratio, races_won, races_lost = self.win_ratio_since(time_delta)
        wins_in_lane, losses_in_lane = self.current_lane_total_win_ratio(time_delta)
        stats = {
            #'win_ratio': win_ratio,
            'wins': races_won,
            'losses': races_lost,
            'wins_in_lane': wins_in_lane,
            'losses_in_lane': losses_in_lane,
            'average_repeat_wins': self.get_average_repeat_wins(time_delta),
            #**self.repeat_wins(time_delta),
            **self.win_times_since(time_delta),
            #'lane_win_ratio_vs_others': self.lane_win_vs_other_lane_ratio(time_delta),
        }

        return stats

