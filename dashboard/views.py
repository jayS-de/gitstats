from django.shortcuts import render
# Create your views here.
from github import Github
from enum import Enum
import github
import logging
import datetime

logger = logging.getLogger(__name__)


class State(Enum):
    created = 'created'
    backlog = 'backlog'
    milestone = 'milestone'
    in_progress = 'in_progress'
    in_review = 'in_review'
    merged = 'merged'
    released = 'released'
    none = 'none'
    waiting = 'waiting'


def index(request):
    time_lines = [
        {'stop': State.milestone, 'start': State.backlog},
        {'stop': State.in_progress, 'start': State.milestone},
        {'stop': State.in_review, 'start': State.in_progress},
        {'stop': State.merged, 'start': State.in_progress}
    ]
    github.enable_console_debug_logging()
    g = Github('d0d56d0aeab74b8ef0b0326666dedf406c2c73ee')
    issues = {}

    switcher = {
        'waffle:in progress': State.in_progress,
        'in progress': State.in_progress,
        'in_progress': State.in_progress,
        'milestoned': State.milestone,
        'review': State.in_review,
        'waffle:in review': State.in_review,
        'closed': State.merged,
        'released': State.released
    }
    i = 0
    for issueEvent in g.get_repo('commercetools/commercetools-jvm-sdk').get_issues_events():
    # for issueEvent in g.get_repo('sphereio/commercetools-php-sdk').get_issues_events():
        if issueEvent.issue._rawData.get('pull_request'):
            continue
        event = {
            'created_at': issueEvent.created_at,
            'name': issueEvent.event
        }
        state = switcher.get(issueEvent.event, State.none)

        if (issueEvent.event == 'labeled') | (issueEvent.event == 'unlabeled'):
            event['label'] = issueEvent._rawData.get('label').get('name')
        if issueEvent.event == 'labeled':
            state = switcher.get(event['label'])

        if issueEvent.event == 'milestoned':
            event['milestone'] = issueEvent._rawData.get('milestone').get('title')

        if issueEvent.issue.number not in issues:
            issues[issueEvent.issue.number] = {
                'created_at': issueEvent.issue.created_at,
                'number': issueEvent.issue.number,
                'title': issueEvent.issue.title,
                'events': [],
                'state_history': {
                    State.backlog: {'timestamp': issueEvent.issue.created_at}
                }
            }
        issues[issueEvent.issue.number].get('events').append(event)
        if state != State.none:
            issues[issueEvent.issue.number].get('state_history')[state] = {'timestamp': issueEvent.created_at}
        # i += 1
        # if i > 100:
        #     break
    data = []
    for issue in sorted(issues.keys(), reverse = True):
        issue_data = issues.get(issue)
        issue_data['states'] = [{'name': State.backlog, 'days': 0}]
        start_time = issue_data.get('created_at')
        state_history = issue_data.get('state_history')
        for line in time_lines:
            start_state = line.get('start')
            stop_state = line.get('stop')
            if start_state in state_history:
                start_time = state_history.get(start_state).get('timestamp')
            if stop_state in state_history:
                stop_time = state_history.get(stop_state).get('timestamp')
                time = stop_time - start_time
                total = stop_time - issue_data.get('created_at')
                issue_data.get('states').append({'name': stop_state, 'days': time, 'total': total})
        if State.merged not in state_history:
            time = datetime.datetime.now() - start_time
            total = datetime.datetime.now() - issue_data.get('created_at')
            issue_data.get('states').append({'name': State.waiting, 'days': time, 'total': total})
        data.append(issue_data)

    return render(request, 'dashboard/index.html', {'issues': data})
