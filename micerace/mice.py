from enum import Enum
from datetime import datetime
import statistics


class MouseColors(Enum):
    brown = 1
    black = 2
    grey = 3
    gray = 3
    yellow = 4
    white = 5
    orange = 6
    silver = 7


class Mouse:
    def __init__(self, **kwargs):
        self.name = kwargs['name'].lower()
        self.family = int(kwargs['family'])
        self.site_rating = kwargs['rating']
        self.color = kwargs['color'].lower()
        self.color_num = getattr(MouseColors, self.color)

        self.kwargs = kwargs

        self.all_races = dict()
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

        if races_won == 0 or races_lost == 0:
            return 0.0, 0

        ratio = round(races_won / float(races_lost), 3)
        total_races = races_won + races_lost

        return ratio, total_races


    def win_times_since(self, time_delta):
        now = datetime.utcnow()
        max_race_age = now - time_delta

        times = []
        for race in self.winning_races:
            if race.completed_at >= max_race_age:
                times.append(race.elapsed_time)

        stats = {
            #'min_win_time': min(times) if len(times) else None,
            #'max_win_time': max(times) if len(times) else None,
            'mean_win_time': round(statistics.mean(times), 2) if len(times) else None,
            'median_win_time': statistics.median(times) if len(times) else None,
        }

        # TODO / NOTE removing None values for human-readability
        return {k: v for k, v in stats.items() if v is not None}

    def interval_stats(self, time_delta):
        win_ratio, total_races = self.win_ratio_since(time_delta)
        return {
            'win_ratio': win_ratio,
            'total_races': total_races,
            **self.win_times_since(time_delta)
        }

