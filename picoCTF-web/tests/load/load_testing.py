"""
Load test picoCTF platform functionality.

Requires a connection to a MongoDB database populated with test user
credentials generated by the registration locustfile (registration.py)
"""

import random

from locust import HttpLocust, task, TaskSet

from demographics_generator import (get_affiliation, get_country_code,
                                    get_demographics, get_email, get_password,
                                    get_team_name, get_user_type, get_username)
from registration import register_and_expect_failure
from util import (ADMIN_PASSWORD, ADMIN_USERNAME, CREATE_TEAM_ENDPOINT,
                  FEEDBACK_ENDPOINT, GAME_PAGE_URL, get_db, GROUPS_ENDPOINT,
                  JOIN_TEAM_ENDPOINT, LOGIN_ENDPOINT, LOGOUT_ENDPOINT,
                  MAX_TEAM_SIZE, NEWS_PAGE_URL, PROBLEMS_ENDPOINT,
                  PROBLEMS_PAGE_URL, PROFILE_PAGE_URL, REGISTRATION_ENDPOINT,
                  REGISTRATION_STATS_ENDPOINT, SCOREBOARD_PAGE_URL,
                  SCOREBOARDS_ENDPOINT, SETTINGS_ENDPOINT, SHELL_PAGE_URL,
                  SHELL_SERVERS_ENDPOINT, STATUS_ENDPOINT, SUBMISSIONS_ENDPOINT,
                  TEAM_ENDPOINT, TEAM_SCORE_ENDPOINT,
                  TEAM_SCORE_PROGRESSION_ENDPOINT, USER_DELETE_ACCOUNT_ENDPOINT,
                  USER_ENDPOINT, USER_EXPORT_ENDPOINT,
                  USER_PASSWORD_CHANGE_ENDPOINT)


def generate_user():
    """Generate a set of valid demographics for the given user type."""
    user_fields =  {
        'username': get_username(),
        'password': 'password',
        'email': get_email(),
        'affiliation': get_affiliation(),
        'country': get_country_code(),
        'usertype': get_user_type(),
        'demo': get_demographics(),
    }
    return user_fields

def acquire_user(properties={}):
    """Retrieve an available test user with the specified properties."""
    properties['in_use'] = {'$in': [False, None]}
    properties['deleted'] = {'$in': [False, None]}
    user = get_db().users.find_one_and_update(
        properties, {'$set': {'in_use': True}}, {'_id': 0})
    if not user:
        raise Exception(
            "Could not acquire user with properties " + str(properties))
    return user

def release_user(username):
    """Release a test user for usage by other threads."""
    res = get_db().users.find_one_and_update(
        {'username': username}, {'$set': {'in_use': False}})
    if not res:
        raise Exception("Could not release user " + username)

def login(l, username=None, password=None):
    """Attempt to log in as a provided or randomly selected user."""
    if not username:
        user = acquire_user()
    else:
        user = dict()
        user['username'] = username
        user['password'] = password
    with l.client.post(LOGIN_ENDPOINT, json={
        'username': user['username'],
        'password': user['password']
    }, catch_response = True) as res:
        if res.status_code == 200:
            res.success()
        else:
            res.failure('Could not log in as {}'.format(user['username']))
    return user['username']

def logout(l):
    """Attempt to log out the current user."""
    l.client.get(LOGOUT_ENDPOINT)

def get_valid_scoreboard_base_endpoint(l):
    """
    Return a valid scoreboard base URL (scoreboard or group) for a user.

    This URL should be followed with e.g. /scoreboard, /score_progressions, etc
    """
    scoreboards = l.client.get(SCOREBOARDS_ENDPOINT).json()
    groups = l.client.get(GROUPS_ENDPOINT).json()

    # Load the initial page of one of the scoreboards
    possible_boards = []
    for board in scoreboards:
        possible_boards.append(('scoreboard', board['sid']))
    for group in groups:
        possible_boards.append(('group', group['gid']))

    board = random.choice(possible_boards)
    if board[0] == 'scoreboard':
        endpoint = SCOREBOARDS_ENDPOINT + '/' + board[1]
        call_label = SCOREBOARDS_ENDPOINT + '/[sid]'
    else:
        endpoint = GROUPS_ENDPOINT + '/' + board[1]
        call_label = GROUPS_ENDPOINT + '/[gid]'
    return (endpoint, call_label)

def get_problem_flags(pid):
    """Retrieve a list of all instance flags for a problem from the DB."""
    return get_db().problems.find_one({'pid': pid}).get('flags', [])

def simulate_loading_any_page(l):
    """Simulate the calls made upon loading any frontend page."""
    l.client.get(USER_ENDPOINT)
    l.client.get(STATUS_ENDPOINT)

def simulate_loading_login_page(l):
    """Simulate the calls made upon loading the login page."""
    simulate_loading_any_page(l)
    l.client.get("")
    l.client.get(SETTINGS_ENDPOINT)
    l.client.get(REGISTRATION_STATS_ENDPOINT)

def simulate_loading_problems_page(l):
    """Simulate the calls made upon loading the problems page."""
    simulate_loading_any_page(l)
    l.client.get(PROBLEMS_PAGE_URL)
    l.client.get(TEAM_ENDPOINT)
    l.client.get(FEEDBACK_ENDPOINT)
    l.client.get(TEAM_SCORE_PROGRESSION_ENDPOINT)
    l.client.get(TEAM_SCORE_ENDPOINT)
    l.client.get(PROBLEMS_ENDPOINT)

def simulate_loading_shell_page(l):
    """Simulate the calls made upon loading the shell page."""
    simulate_loading_any_page(l)
    l.client.get(SHELL_PAGE_URL)
    l.client.get(SHELL_SERVERS_ENDPOINT)

def simulate_loading_game_page(l):
    """Simulate the calls made upon loading the game page."""
    simulate_loading_any_page(l)
    l.client.get(GAME_PAGE_URL)
    l.client.get(STATUS_ENDPOINT)

def simulate_loading_scoreboard_page(l):
    """Simulate the calls made upon loading the scoreboard page."""
    simulate_loading_any_page(l)
    l.client.get(SCOREBOARD_PAGE_URL)
    l.client.get(SCOREBOARDS_ENDPOINT)
    l.client.get(TEAM_ENDPOINT)
    l.client.get(GROUPS_ENDPOINT)

def simulate_loading_profile_page(l):
    """Simulate the calls made upon loading the profile page."""
    simulate_loading_any_page(l)
    l.client.get(PROFILE_PAGE_URL)
    l.client.get(TEAM_ENDPOINT)
    l.client.get(SCOREBOARDS_ENDPOINT)
    l.client.get(GROUPS_ENDPOINT)

def simulate_loading_news_page(l):
    """Simulate the calls made upon loading the news page."""
    simulate_loading_any_page(l)
    l.client.get(NEWS_PAGE_URL)

class LoadTestingTasks(TaskSet):
    """Root set of all load testing tasks."""

    @task
    def load_login_page(l):
        """Simulate loading the login page."""
        simulate_loading_login_page(l)

    @task
    def load_shell_page(l):
        """Simulate loading the shell page."""
        username = login(l)
        try:
            simulate_loading_shell_page(l)
            logout(l)
        finally:
            release_user(username)

    @task
    def load_game_page(l):
        """Simulate loading the Unity game page."""
        username = login(l)
        try:
            simulate_loading_game_page(l)
            logout(l)
        finally:
            release_user(username)

    @task
    def load_news_page(l):
        """Simulate loading the news page."""
        simulate_loading_news_page(l)

    @task
    def call_user_endpoint(l):
        """Just calls the user endpoint, as if updating the score display."""
        username = login(l)
        try:
            l.client.get(USER_ENDPOINT)
            logout(l)
        finally:
            release_user(username)

    @task
    class ProblemTasks(TaskSet):
        """Simulate actions on the problems page."""

        def setup(l):
            """Retrieve all problem flags as an admin user (runs once)."""
            get_db().problems.delete_many({})
            login(l, username=ADMIN_USERNAME, password=ADMIN_PASSWORD)
            all_problems = l.client.get(
                PROBLEMS_ENDPOINT + '?unlocked_only=false').json()
            flag_maps = []
            for problem in all_problems:
                flag_maps.append({
                    'pid': problem['pid'],
                    'flags':  [i['flag'] for i in problem['instances']]
                })
            get_db().problems.insert_many(flag_maps)
            logout(l)

        @task
        def load_problems_page(l):
            """Load the problems page without solving anything."""
            username = login(l)
            try:
                simulate_loading_problems_page(l)
                logout(l)
            finally:
                release_user(username)
                l.interrupt()

        @task
        def submit_problem_solution(l):
            """Submit a solution to a problem."""
            username = login(l)
            try:
                simulate_loading_problems_page(l)

                unlocked_problems = l.client.get(PROBLEMS_ENDPOINT).json()
                problem = random.choice(unlocked_problems)
                # Select a flag from the pool of possible instance flags:
                # probability of a correct submission is 1/(num instances)
                flag = random.choice(get_problem_flags(problem['pid']))
                l.client.post(SUBMISSIONS_ENDPOINT, json={
                    'pid': problem['pid'],
                    'key': flag,
                    'method': 'testing'
                }, headers={
                    'X-CSRF-Token': l.client.cookies['token']
                })
            finally:
                release_user(username)
                l.interrupt()

        @task
        def send_feedback(l):
            """Submit feedback for an unlocked problem."""
            username = login(l)
            try:
                simulate_loading_problems_page(l)

                unlocked_problems = l.client.get(PROBLEMS_ENDPOINT).json()
                problem = random.choice(unlocked_problems)
                l.client.post(FEEDBACK_ENDPOINT, json={
                    'pid': problem['pid'],
                    'feedback': {
                        'liked': random.choice([True, False])
                    }
                }, headers={
                    'X-CSRF-Token': l.client.cookies['token']
                })
            finally:
                release_user(username)
                l.interrupt()

    @task
    class ScoreboardTasks(TaskSet):
        """Simulate actions on the scoreboards page."""

        @task
        def load_scoreboard_pages(l):
            """Load several pages of a random scoreboard."""
            username = login(l)
            try:
                simulate_loading_scoreboard_page(l)

                endpoint, call_label = get_valid_scoreboard_base_endpoint(l)
                l.client.get(endpoint + '/score_progressions',
                    name=(call_label + '/score_progressions'))
                initial_page_res = l.client.get(
                    endpoint + '/scoreboard',
                    name=(call_label + '/scoreboard')).json()
                for i in range(0, random.randrange(1, 10)):
                    p = random.randrange(
                        1, initial_page_res['total_pages'] + 1)
                    l.client.get(endpoint + '/scoreboard?page=' + str(p),
                        name=(call_label + '/scoreboard?page=[p]'))
                logout(l)
            finally:
                release_user(username)
                l.interrupt()

        @task
        def load_filtered_scoreboard_pages(l):
            """Load several pages of a filtered random scoreboard."""
            username = login(l)
            try:
                simulate_loading_scoreboard_page(l)

                endpoint, call_label = get_valid_scoreboard_base_endpoint(l)
                l.client.get(endpoint + '/score_progressions',
                    name=(call_label + '/score_progressions'))
                initial_page_res = l.client.get(
                    endpoint + '/scoreboard',
                    name=(call_label + '/scoreboard')).json()
                search_endpoint = (
                    endpoint + '/scoreboard?search=' + get_affiliation())
                for i in range(0, random.randrange(1, 10)):
                    p = random.randrange(
                        1, initial_page_res['total_pages'] + 1)
                    l.client.get(search_endpoint + '&page=' + str(p),
                        name=(call_label + '/scoreboard?search=[q]&page=[p]'))
                logout(l)
            finally:
                release_user(username)
                l.interrupt()

    @task
    class ProfileTasks(TaskSet):
        """Simulate profile page actions."""

        @task
        def load_profile_page(l):
            """Just load the profile page."""
            username = login(l)
            try:
                simulate_loading_profile_page(l)
                logout(l)
            finally:
                release_user(username)
                l.interrupt()

        @task
        def change_password(l):
            """Change a user's password."""
            user = acquire_user()
            try:
                login(l, username=user['username'], password=user['password'])
                simulate_loading_profile_page(l)

                new_password = get_password()
                with l.client.post(
                        USER_PASSWORD_CHANGE_ENDPOINT,
                        json={
                            'current_password': user['password'],
                            'new_password': new_password,
                            'new_password_confirmation': new_password,
                        }, headers={
                            'X-CSRF-Token': l.client.cookies['token']
                        }, catch_response=True) as res:
                    if res.status_code == 200:
                        get_db().users.find_one_and_update(
                            {'username': user['username']},
                            {'$set': {
                                'password': new_password
                            }})
                        res.success()
                    else:
                        res.failure('Failed to change password')
                logout(l)
                login(l, username=user['username'], password=new_password)
                logout()
            finally:
                release_user(user['username'])
                l.interrupt()

        @task
        def export_account_data(l):
            """Export a user's account data."""
            username = login(l)
            try:
                simulate_loading_profile_page(l)

                l.client.get(USER_EXPORT_ENDPOINT)
                logout(l)
            finally:
                release_user(username)
                l.interrupt()

        @task
        def delete_account(l):
            """Delete a user's account."""
            user = acquire_user()
            try:
                login(l, username=user['username'], password=user['password'])
                simulate_loading_profile_page(l)

                with l.client.post(USER_DELETE_ACCOUNT_ENDPOINT, json={
                            'password': user['password']
                        }, headers={
                            'X-CSRF-Token': l.client.cookies['token']
                        }, catch_response=True) as res:
                    if res.status_code == 200:
                        get_db().users.find_one_and_update({
                            'username': user['username']
                        }, {'$set': {'deleted': True}})
                        res.success()
                    else:
                        res.failure('Failed to delete account')
            finally:
                release_user(user['username'])
                l.interrupt()
    @task
    class TeamTasks(TaskSet):
        """Simulate usage of team functionality."""

        @task(weight=1)
        def create_team(l):
            """Create a custom team for a user."""
            user = acquire_user({
                'usertype': {'$in': ['student', 'college', 'other']},
                'on_team': {'$in': [False, None]}
                })
            if not user:
                l.interrupt()
            try:
                login(l, username=user['username'], password=user['password'])
                simulate_loading_profile_page(l)

                team_name = get_team_name()
                team_password = get_password()
                with l.client.post(CREATE_TEAM_ENDPOINT, json={
                    'team_name': team_name,
                    'team_password': team_password
                }, catch_response=True) as res:
                    if res.status_code == 201:
                        get_db().users.find_one_and_update({
                            'username': user['username']
                        }, {'$set': {
                            'on_team': True,
                            'team_name': team_name
                        }})
                        get_db().teams.insert_one({
                            'team_name': team_name,
                            'team_password': team_password,
                            'number_of_members': 1
                        })
                        res.success()
                    else:
                        res.failure('Failed to create custom team: ' +
                            str(res.json()))
                logout(l)
            finally:
                release_user(user['username'])
                l.interrupt()

        @task(weight=6)
        def join_team(l):
            """Join an existing team with an open space."""
            user = acquire_user({
                'usertype': {'$in': ['student', 'college', 'other']},
                'on_team': {'$in': [False, None]}
                })
            if not user:
                l.interrupt()
            try:
                login(l, username=user['username'], password=user['password'])
                simulate_loading_profile_page(l)

                # Sometimes fails due to race condition - another thread can
                # push a team over the max size while trying to join it
                team = get_db().teams.find_one({
                    'number_of_members': {'$lt': MAX_TEAM_SIZE}
                    })
                if not team:
                    l.interrupt()

                with l.client.post(JOIN_TEAM_ENDPOINT, json={
                        'team_name': team['team_name'],
                        'team_password': team['team_password']
                    }, catch_response=True) as res:
                        if res.status_code == 200:
                            get_db().users.find_one_and_update({
                                'username': user['username']
                            }, {'$set': {
                                'on_team': True,
                                'team_name': team['team_name']
                            }})
                            get_db().teams.find_one_and_update({
                                'team_name': team['team_name']
                            }, {'$inc': {
                                'number_of_members': 1
                            }})
                            res.success()
                        else:
                            res.failure('Failed to join team: ' +
                                str(res.json()))
                logout(l)
            finally:
                release_user(user['username'])
                l.interrupt()

    @task
    class OngoingRegistrationTasks(TaskSet):
        """Simulate registration activity."""

        @task(weight=10)
        def successfully_register(l):
            """Register a valid test user and store credentials in DB."""
            simulate_loading_login_page(l)
            user_demographics = generate_user()
            with l.client.post(REGISTRATION_ENDPOINT, json=user_demographics,
                    catch_response=True) as res:
                if res.status_code == 201:
                    get_db().users.insert_one(user_demographics.copy())
                    res.success()
                else:
                    res.failure('Failed to register user')
            l.interrupt()

        @task(weight=1)
        class RegistrationErrorTasks(TaskSet):
            """Tasks which fail registration for various reasons."""

            @task
            def missing_field_error(l):
                """Fail registration due to a missing required field."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                to_delete = random.choice([
                    'username', 'password', 'email', 'affiliation', 'country',
                    'usertype', 'demo'
                ])
                del user_demographics[to_delete]
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def username_error(l):
                """Fail registration due to an invalid username."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['username'] = ''
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def password_error(l):
                """Fail registration due to an invalid password."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['password'] = 'oo'
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def email_error(l):
                """Fail registration due to an invalid email address."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['email'] = 'invalid_email_address'
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def affiliation_error(l):
                """Fail registration due to an invalid affiliation."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['affiliation'] = ''
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def country_error(l):
                """Fail registration due to an invalid country."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['country'] = 'invalid_country_code'
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def usertype_error(l):
                """Fail registration due to an invalid user type."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['usertype'] = 'invalid_user_type'
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def demo_error(l):
                """Fail registration due to invalid demographics."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['demo']['age'] = 'invalid_age'
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

            @task
            def require_parent_email_error(l):
                """Fail registration due to an invalid parent email."""
                simulate_loading_login_page(l)
                user_demographics = generate_user()
                user_demographics['demo']['age'] = '13-17'
                user_demographics['demo']['parentemail'] = 'invalid_email'
                register_and_expect_failure(l, user_demographics)
                l.interrupt()

class LoadTestingLocust(HttpLocust):
    """Main locust class. Defines the task set and wait interval limits."""

    task_set = LoadTestingTasks
    min_wait = 1000
    max_wait = 4000
