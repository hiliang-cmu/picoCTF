"""Module for calculating gameplay statistics."""

import datetime

import pymongo

import api.achievement
import api.annotations
import api.cache
import api.db
import api.group
import api.problem
import api.problem_feedback
import api.stats
import api.team
from api.common import InternalException

top_teams = 5


def _get_problem_names(problems):
    """Extract the names from a list of problems."""
    return [problem['name'] for problem in problems]


@api.cache.memoize()
def get_score(tid=None, uid=None):
    """
    Get the score for a user or team.

    Args:
        tid: The team id
        uid: The user id
    Returns:
        The users's or team's score
    """
    score = sum([
        problem['score']
        for problem in api.problem.get_solved_problems(tid=tid, uid=uid)
    ])
    return score


def get_team_review_count(tid=None, uid=None):
    """
    Get the count of reviewed problems for a user or team.

    Args:
        tid: team to get count of
        uid: user to get count of (overrides tid)

    Returns: review count
    """
    if uid is not None:
        return len(api.problem_feedback.get_reviewed_pids(uid=uid))
    elif tid is not None:
        count = 0
        for member in api.team.get_team_members(tid=tid):
            count += len(
                api.problem_feedback.get_reviewed_pids(uid=member['uid']))
        return count


# This is on the /scoreboard handler hot path and should be cached. Stored by
# the cache_stats daemon.
@api.cache.memoize()
def get_group_scores(gid=None, name=None):
    """
    Get the group scores.

    Args:
        gid: The group id
        name: The group name
    Returns:
        A dictionary containing name, tid, and score
    """
    members = [
        api.team.get_team(tid=tid)
        for tid in api.group.get_group(gid=gid, name=name)['members']
    ]

    result = []
    for team in members:
        if team["size"] > 0:
            result.append({
                "name": team['team_name'],
                "tid": team['tid'],
                "affiliation": team["affiliation"],
                "eligible": team["eligible"],
                "score": get_score(tid=team['tid'])
            })

    return sorted(result, key=lambda entry: entry['score'], reverse=True)


def get_group_average_score(gid=None, name=None):
    """
    Get the average score of teams in a group.

    Args:
        gid: The group id
        name: The group name
    Returns:
        The total score of the group
    """
    group_scores = get_group_scores(gid=gid, name=name)
    total_score = sum([entry['score'] for entry in group_scores])
    return int(total_score / len(group_scores)) if len(group_scores) > 0 else 0


# Stored by the cache_stats daemon
@api.cache.memoize()
def get_all_team_scores(eligible=None, country=None, show_ineligible=False):
    """
    Get the score for every team in the database.

    Args:
        eligible: required boolean field
        show_ineligible: ignore eligibility, show all
        country: optional restriction by country

    Returns:
        A list of dictionaries with name and score

    """
    if show_ineligible:
        teams = api.team.get_all_teams(show_ineligible=True)
    else:
        if eligible is None:
            raise InternalException("Eligible must be set to either " +
                                    "true or false")
        if eligible:
            teams = api.team.get_all_teams(
                eligible=True, country=country, ineligible=False)
        else:
            teams = api.team.get_all_teams(
                eligible=False, country=country, ineligible=True)

    db = api.db.get_conn()

    result = []
    all_groups = api.group.get_all_groups()
    for team in teams:
        # Get the full version of the group.
        groups = [
            group for group in all_groups if team["tid"] in group["members"] or
            team["tid"] in group["teachers"] or team["tid"] == group["owner"]
        ]

        # Determine if the user is exclusively a member of hidden groups.
        # If they are, they won't be processed.
        if (len(groups) == 0 or
                any([not (group["settings"]["hidden"]) for group in groups])):
            team_query = db.submissions.find({
                'tid': team['tid'],
                'correct': True
            })
            if team_query.count() > 0:
                lastsubmit = team_query.sort(
                    'timestamp', direction=pymongo.DESCENDING)[0]['timestamp']
            else:
                lastsubmit = datetime.datetime.now()
            score = get_score(tid=team['tid'])
            if score > 0:
                result.append({
                    "name": team['team_name'],
                    "tid": team['tid'],
                    "score": score,
                    "affiliation": team["affiliation"],
                    "lastsubmit": lastsubmit
                })
    time_ordered = sorted(result, key=lambda entry: entry['lastsubmit'])
    time_ordered_time_removed = [{
        'name': x['name'],
        'tid': x['tid'],
        'score': x['score'],
        'affiliation': x['affiliation']
    } for x in time_ordered]
    return sorted(
        time_ordered_time_removed,
        key=lambda entry: entry['score'],
        reverse=True)


def get_all_user_scores():
    """
    Get the score for every user in the database.

    Returns:
        A list of dictionaries with name and score

    """
    users = api.user.get_all_users()

    result = []
    for user in users:
        result.append({
            "name": user['username'],
            "score": get_score(uid=user['uid'])
        })

    return sorted(result, key=lambda entry: entry['score'], reverse=True)


@api.cache.memoize(timeout=120, fast=True)
def get_problems_by_category():
    """
    Get the list of all problems divided into categories.

    Returns:
        A dictionary of category:[problem list]

    """
    result = {
        cat: _get_problem_names(api.problem.get_all_problems(category=cat))
        for cat in api.problem.get_all_categories()
    }

    return result


@api.cache.memoize(timeout=120, fast=True)
def get_pids_by_category():
    """Return a dict of {category: [problems]}."""
    result = {
        cat: [x['pid'] for x in api.problem.get_all_problems(category=cat)
             ] for cat in api.problem.get_all_categories()
    }
    return result


@api.cache.memoize(timeout=120, fast=True)
def get_pid_categories():
    """Return a dict of {pid: category}."""
    pid_map = {}
    for cat in api.problem.get_all_categories():
        for p in api.problem.get_all_problems(category=cat):
            pid_map[p['pid']] = cat
    return pid_map


def get_team_member_stats(tid):
    """
    Get the solved problems for each member of a given team.

    Args:
        tid: the team id

    Returns:
        A dict of username:[problem list]

    """
    members = api.team.get_team_members(tid=tid)

    return {
        member['username']: _get_problem_names(
            api.problem.get_solved_problems(uid=member['uid']))
        for member in members
    }


def get_problem_submission_stats(pid=None, name=None):
    """
    Retrieve the number of valid and invalid submissions for a given problem.

    Args:
        pid: the pid of the problem
        name: the name of the problem
    Returns:
        Dict of {valid: #, invalid: #}
    """
    problem = api.problem.get_problem(pid=pid, name=name)

    return {
        "valid":
        len(api.problem.get_submissions(pid=problem["pid"], correctness=True)),
        "invalid":
        len(
            api.problem.get_submissions(pid=problem["pid"], correctness=False))
    }


@api.cache.memoize()
def get_score_progression(tid=None, uid=None, category=None):
    """
    Find the score and time after each correct submission of a team or user.

    NOTE: this is slower than get_score.
          Do not use this for getting current score.

    Args:
        tid: the tid of the user
        uid: the uid of the user
        category: category filter
    Returns:
        A list of dictionaries containing score and time
    """
    solved = api.problem.get_solved_problems(
        tid=tid, uid=uid, category=category)

    result = []
    score = 0

    problems_counted = set()

    for problem in sorted(solved, key=lambda prob: prob["solve_time"]):
        if problem['pid'] not in problems_counted:
            score += problem["score"]
            problems_counted.add(problem['pid'])
        result.append({
            "score": score,
            "time": int(problem["solve_time"].timestamp())
        })

    return result


def get_top_teams(gid=None, eligible=None, country=None,
                  show_ineligible=False):
    """
    Find the top teams.

    Args:
        gid: if specified, return the top teams from this group only
        eligible: required boolean field

    Returns:
        The top teams and their scores

    """
    if gid is None:
        if eligible is None:
            raise InternalException(
                "Eligible must be set to either true or false")
        all_teams = api.stats.get_all_team_scores(
            eligible=eligible,
            country=country,
            show_ineligible=show_ineligible)
    else:
        all_teams = api.stats.get_group_scores(gid=gid)
    return all_teams if len(all_teams) < top_teams else all_teams[:top_teams]


# Stored by the cache_stats daemon
@api.cache.memoize()
def get_problem_solves(name=None, pid=None):
    """
    Return the number of solves for a particular problem.

    Must supply either pid or name.

    Args:
        name: name of the problem
        pid: pid of the problem
    """
    if not name and not pid:
        raise InternalException(
            "You must supply either a pid or name of the problem.")

    db = api.db.get_conn()

    problem = api.problem.get_problem(name=name, pid=pid)

    return db.submissions.find({
        'pid': problem["pid"],
        'correct': True
    }).count()


@api.cache.memoize()
def get_top_teams_score_progressions(gid=None,
                                     eligible=True,
                                     country=None,
                                     show_ineligible=False):
    """
    Get the score progressions for the top teams.

    Args:
        gid: If specified, compute the progressions for the top teams
             from this group only
        country: If specified, limit teams by country
        eligible: If specified, limit teams to eligible ones
        show_ineligible: if specified, show all teams, eligible and eligible

    Returns:
        The top teams and their score progressions.
        A dict of {name: name, score_progression: score_progression}

    """
    return [{
        "name": team["name"],
        "affiliation": team["affiliation"],
        "score_progression": get_score_progression(tid=team["tid"]),
    } for team in get_top_teams(
        gid=gid,
        eligible=eligible,
        country=country,
        show_ineligible=show_ineligible)]


@api.cache.memoize(timeout=300)
def check_invalid_instance_submissions(gid=None):
    """Get submissions of keys for the wrong problem instance."""
    db = api.db.get_conn()
    shared_key_submissions = []

    group = None
    if gid is not None:
        group = api.group.get_group(gid=gid)

    for problem in api.problem.get_all_problems(show_disabled=True):
        valid_keys = [instance['flag'] for instance in problem['instances']]
        incorrect_submissions = db.submissions.find({
            'pid': problem['pid'],
            'correct': False
        }, {"_id": 0})
        for submission in incorrect_submissions:
            if submission['key'] in valid_keys:
                # make sure that the key is still invalid
                if not api.problem.grade_problem(
                        submission['pid'],
                        submission['key'],
                        tid=submission['tid'])['correct']:
                    if group is None or submission['tid'] in group['members']:
                        submission['username'] = api.user.get_user(
                            uid=submission['uid'])['username']
                        submission["problem_name"] = problem["name"]
                        shared_key_submissions.append(submission)

    return shared_key_submissions


@api.cache.memoize()
def get_registration_count():
    """Get the user, team, and group counts."""
    db = api.db.get_conn()
    users = db.users.count()
    stats = {
        "users": users,
        "teams": db.teams.count() - users,
        "groups": db.groups.count()
    }
    usernames = set(db.users.find({}).distinct("username"))
    team_names = set(db.teams.find({}).distinct("team_name"))

    real_team_names = team_names - usernames
    real_team_ids = list(
        db.teams.find({
            "team_name": {
                "$in": list(real_team_names)
            }
        }).distinct("tid"))

    teamed_users = db.users.count({"tid": {"$in": real_team_ids}})
    stats["teamed_users"] = teamed_users

    return stats
