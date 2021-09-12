import configparser
import datetime
from typing import Dict, List, Optional, Tuple, Union


def load_access(config: configparser.ConfigParser, username: str,
                now: datetime.datetime
) -> Tuple[datetime.datetime, bool, float]:
    """
    Return a bool indicating whether the submission is providing feedback and
    a float specifying a penalty to apply if the submission is late.
    """
    entries = _get_entries(config)
    due_datetime = _get_due_datetime(config, username, entries["due_time"])
    is_open = _is_open(now, entries["open_before"], entries["close_after"],
                       entries["late_hours"], entries["grace"], due_datetime)
    penalty = _get_penalty(entries["late_hours"], entries["penalty"],
                           due_datetime, now)
    return (due_datetime, is_open, penalty)


def _get_entries(config: configparser.ConfigParser
) -> Dict[str, Union[float, int, str]]:
    """
    Return a dictionary of access rules, listed below. If any access rules
    are not found in the config files, default values (shown in brackets)
    are used.

    due_time: datetime.time [datetime.time(hour=11, minute=59)]
        The hour and minute of the deadline, formatted "HH:MM".

    grace: int [0]
        The number of minutes after the deadline still considered on-time.

    open_before: int [-1]
        The number of days before the deadline that submission is open.
        -1 means the submission is always open before the deadline.

    close_after: int [-1]
        The number of days after the deadline that feedback is provided.
        -1 means feedback is always provided after the deadline.

    late_hours: int [0]
        The number of hours after the deadline submissions are accepted
        with a penalty.

    penalty: float [1.0]
        The penalty for late submissions, between 0.0 and 1.0.
        0.0 means no penalty and 1.0 means no late credit provided.
        A penalty is only effective if late_hours is greater than zero.

        Example: 0.3 means a submission will receive at most 70% if it is
                 submitted late.
    """
    section = "access"
    hour, minute = config.get(section, "due_time", fallback="23:59").split(":")
    return {   "due_time": datetime.time(hour=int(hour), minute=int(minute)),
                  "grace": int(config.get(section, "grace", fallback=0)),
            "open_before": int(config.get(section, "open_before", fallback=-1)),
            "close_after": int(config.get(section, "close_after", fallback=-1)),
             "late_hours": int(config.get(section, "late_hours", fallback=0)),
                "penalty": float(config.get(section, "penalty", fallback=1.0))}


def _get_due_datetime(config: configparser.ConfigParser, username: str,
                      due_time: datetime.time) -> datetime.datetime:
    """
    Read each config section to find the due datetime for the user.

    Sections marking due datetimes follow one of these formats:

           with time: [YYYY-MM-DD HH:MM]
        without time: [YYYY-MM-DD]

    If time is not specified for a user, the global submission time is used.
    """
    user_datetime = None
    for section in config.sections():
        section = section.lower()
        section_date = _parse_date(section, due_time)
        if section_date:
            usernames = config.options(section)
            if username in usernames:
                user_datetime = section_date
            elif not user_datetime and not usernames:
                user_datetime = section_date
    if not user_datetime:
        raise Exception("No due date specified")
    return user_datetime


def _parse_date(section: str,
                due_time: datetime.time) -> Optional[datetime.datetime]:
    try:
        return datetime.datetime.strptime(section, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            due_date = datetime.datetime.strptime(section, "%Y-%m-%d")
            return datetime.datetime.combine(due_date, due_time)
        except ValueError:
            return None


def _is_open(now: datetime.datetime, open_days: int, close_days: int,
             late_hours: int, grace: int, due: datetime.datetime) -> bool:
    due += datetime.timedelta(minutes=grace)
    if open_days < 0:
        # open half a year in advance
        open_datetime = due - datetime.timedelta(weeks=26)
    else:
        open_datetime = due - datetime.timedelta(days=open_days)
    if close_days < 0:
        # provide feedback four years after due
        close_datetime = due + datetime.timedelta(weeks=208)
    else:
        close_datetime = due + datetime.timedelta(days=close_days,
                                                  hours=late_hours)
    return open_datetime <= now <= close_datetime


def _get_penalty(late_hours: int, penalty: float, due: datetime.datetime,
                 now: datetime.datetime) -> float:
    if now <= due:
        return 0.0
    elif now <= due + datetime.timedelta(hours=late_hours):
        return penalty
    else:
        return 1.0
