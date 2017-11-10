#!/usr/bin/env python
"""Custom utility to migrate bugzilla issues to github issues.

Issues are exported from bugzilla manually via saving full search
queries as xml. Issues are imported to github via the github API.

Author: Ben Andre <andre@ucar.edu>

"""

from __future__ import print_function
from __future__ import unicode_literals

import sys

if sys.hexversion < 0x02070000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

#
# built-in modules
#
import argparse
import os
import time
import traceback

# in python2, xml.etree.ElementTree returns byte strings, str, instead
# of unicode. We need unicode to be compatible with cfg and json
# parser and python3.
import xml.etree.ElementTree as ET
if sys.version_info[0] >= 3:
    def UnicodeXMLTreeBuilder():
        return None
else:
    class UnicodeXMLTreeBuilder(ET.XMLTreeBuilder):
        # See this thread:
        # http://www.gossamer-threads.com/lists/python/python/728903
        def _fixtext(self, text):
            return text

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

#
# installed dependencies
#
import github

#
# other modules in this package
#


# -------------------------------------------------------------------------------
#
# User input
#
# -------------------------------------------------------------------------------
def commandline_options():
    """Process the command line arguments.

    """
    parser = argparse.ArgumentParser(
        description='migrate bugzilla issues github issues')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--b2g-config', nargs=1, default=['../b2g.cfg'],
                        help='path to b2g config file')

    parser.add_argument('--convert-config', nargs=1, default=['../b2g.cfg'],
                        help='path to config file containing conversion information')

    parser.add_argument('--report-rate-limit', action='store_true', default=False,
                        help='request and report github api rate limit info')

    parser.add_argument('--resume', nargs=1, default=[''],
                        help='request and report github api rate limit info')

    options = parser.parse_args()
    return options


def read_config_file(filename):
    """Read the configuration file and process

    """
    print("Reading configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)

    return config


# -------------------------------------------------------------------------------
#
# work functions
#
# -------------------------------------------------------------------------------
def view_user(gh):
    """experiment with users
    """
    gh_user = gh.get_user()

    print("{0}".format(gh_user.login))
    for repo in gh_user.get_repos():
        print("  {0} - {1}".format(repo.name, repo.owner))


def view_org(gh, org_name):
    """experiment with organizations
    """
    org = gh.get_organization(org_name)
    for member in org.get_members():
        print("{0} : {1}".format(org.login, member.login))

    for repo in org.get_repos():
        print("  {0} - ".format(repo.name), end='')
        for collab in repo.get_collaborators():
            print("{0}, ".format(collab.login), end='')
        print()


def add_collaborator(gh, org_name, login, repos):
    """
    """
    print('-'*70)
    print("add_colloborator - {org} : {login} : {repos}".format(
        org=org_name, login=login, repos=repos))

    # verify we have a valid login name
    user = gh.get_user(login)
    if not user:
        raise RuntimeError('invalid user login')

    gh_org = gh.get_organization(org_name)
    for repo in repos:
        gh_repo = gh_org.get_repo(repo)
        gh_repo.add_to_collaborators(login)


def remove_collaborator(gh, org_name, login, repos):
    """
    """
    print('-'*70)
    print("remove_colloborator - {org} : {login} : {repos}".format(
        org=org_name, login=login, repos=repos))

    # verify we have a valid login name
    user = gh.get_user(login)
    if not user:
        raise RuntimeError('invalid user login')

    gh_org = gh.get_organization(org_name)
    for repo in repos:
        gh_repo = gh_org.get_repo(repo)
        gh_repo.remove_from_collaborators(login)


def view_collaborators(gh, org_name, repos):
    """
    """
    print('-'*70)
    print("view_colloborators - {org} : {repos}".format(
        org=org_name, repos=repos))


    gh_org = gh.get_organization(org_name)
    for repo in repos:
        gh_repo = gh_org.get_repo(repo)
        print("  {0} collaborators : ".format(repo))
        for collab in gh_repo.get_collaborators():
            print("    {0}".format(collab))


def view_repo(gh, org_name, repo):
    """
    """
    print('-'*70)
    print("view_repo : {repo}".format(
        org=org_name, repo=repo))

    gh_user = gh.get_user(org_name)

    gh_repo = gh_user.get_repo(repo)
    print("  {0}  ".format(gh_repo))
    return gh_repo


def read_bugzilla_xml(file_name):
    """
    """
    file_path = os.path.abspath(file_name)
    if not os.path.exists(file_name):
        msg = ('ERROR: bug list xml does not '
               'exist at {0}'.format(file_path))
        raise RuntimeError(msg)

    with open(file_path, 'r') as filehandle:
        xml_tree = ET.parse(filehandle, parser=UnicodeXMLTreeBuilder())
        xml_root = xml_tree.getroot()
    return xml_root


abuse_pause_delta = 30
abuse_pause = 2*abuse_pause_delta


def check_for_abuse_error(status, data):
    global abuse_pause
    if (status == 403 and 'abuse' in data['message']):
        print('Abuse pause for {0} seconds....'.format(abuse_pause))
        time.sleep(abuse_pause)
        abuse_pause += abuse_pause_delta
    else:
        raise error


def update_issue_label_list(bug, field, gh_labels, label_map, new_labels):
    bugz_item = bug.find('./{0}'.format(field))
    if bugz_item is not None:
        item = bugz_item.text
        item = item.lower()
        try:
            label = label_map[item]
        except KeyError:
            # not mapped, ignore
            label = None
        if label:
            try:
                ghlabel = gh_labels[label]
                new_labels.append(ghlabel)
            except KeyError:
                msg = "mapped bugzill label '{0}' was not found in github label list: {1}.".format(label, gh_labels.keys())
                raise RuntimeError(msg)


def create_attachment_list(bug):
    new_list = []
    attachments = bug.findall('./attachment')
    for attachment in attachments:
        name = attachment.find('./filename').text.strip()
        description = attachment.find('./desc').text.strip()
        text = "{name} - {desc}".format(
            name=name, desc=description)
        new_list.append(text)
    return new_list


def optional_list(bug, field):
    new_list = []
    list_xml = bug.findall('./{0}'.format(field))
    for item in list_xml:
        new_list.append(item.text)
    return new_list


def optional_text(data_list, header_text):
    text = ''
    if data_list:
        text = header_text
        for item in data_list:
            text = "{0} {1}, ".format(text, item)
        text = "{0}\n".format(text)
    return text


def b2g_comment(bug_id, comment, main_issue=False, cc_list=[],
                blocks_list=[], depends_list=[],
                attachment_list=[]):
    xml_who = comment.find('./who')
    who_text = '{0} < {1} >'.format(
        xml_who.get('name'), xml_who.text)
    when_text = comment.find('./bug_when').text
    comment_text = comment.find('./thetext').text

    id_text = ''
    blocks_text = ''
    depends_text = ''
    cc_text = ''
    attachment_text = ''
    if main_issue:
        base_url = "http://bugz.cgd.ucar.edu/show_bug.cgi?id"
        id_text = "**Bugzilla Id:** [{bugid}]({url}={bugid})\n".format(
            bugid=bug_id, url=base_url)

        blocks_text = optional_text(blocks_list, "**Bugzilla Blocks:** ")
        depends_text = optional_text(depends_list, "**Bugzilla Depends:** ")
        cc_text = optional_text(cc_list, "**Bugzilla CC:** ")

        if attachment_list:
            attachment_base = '**Bugzilla Attachment:** '
            for attachment in attachment_list:
                txt = '{0} {1}\n'.format(attachment_base, attachment)
                attachment_text = '{0}{1}'.format(attachment_text, txt)

    body_text = '''**{who} - {when}**
{bugid}{blocks}{depends}{cc}{attachment}
{cmmnt}'''.format(
        bugid=id_text, who=who_text, when=when_text,
        cc=cc_text, blocks=blocks_text, depends=depends_text,
        cmmnt=comment_text, attachment=attachment_text)
    return body_text

# -----------------------------------------------------------------------
#
# main
#
# -----------------------------------------------------------------------

def main(options):
    b2g_config = read_config_file(options.b2g_config[0])
    _user = b2g_config.get("github", "user")
    _token = b2g_config.get("github", "token")

    if options.debug:
        github.enable_console_debug_logging()
    gh = github.Github(_user, _token)

    if options.report_rate_limit:
        rl = gh.get_rate_limit()
        print(rl)
        return 0

    resume = options.resume[0]
    
    friendly_pause = 5

    convert_config = read_config_file(options.convert_config[0])
    _organization = convert_config.get("github", "organization")
    _repository = convert_config.get("github", "repository")

    # get the authorized user
    gh_auth_user = gh.get_user()

    gh_repo = gh_auth_user.get_repo(_repository)
    if not resume:
        # delete existing test repository
        print('Deleting existing repository: {0}'.format(_repository))
        try:
            gh_repo.delete()
        except github.UnknownObjectException:
            # repository doesn't exist
            pass
        
        time.sleep(friendly_pause)
        
        # recreate test repo
        print('Creating repository: {0}'.format(_repository))
        gh_repo = gh_auth_user.create_repo(
            _repository,
            description=convert_config.get('github', 'description'),
            has_issues=True, auto_init=False)
        
        time.sleep(friendly_pause)


    if False:
        # create a lookup table of xml users?
        # fetch user list
        gh_users_all = gh.search_users('bandre-ucar')
        gh_users = {}
        for user in gh_users_all:
            gh_users[user.login] = user
        print(gh_users)

    # add new milestones to the repo
    print("Processing milestones.")
    new_milestones = convert_config.get('github', 'milestones').split(',')
    gh_milestones = gh_repo.get_milestones()
    for name in new_milestones:
        name = name.strip().lower()
        found_milestone = False
        for milestone in gh_milestones:
            if name == milestone.title.lower():
                found_milestone = True
        if not found_milestone:
            gh_repo.create_milestone(name)
    # save the updated list
    gh_milestones = gh_repo.get_milestones()
    milestones = {}
    for ghm in gh_milestones:
        milestones[ghm.title.lower()] = ghm
    # create map for converting bugzilla milestones to github
    milestone_map = {}
    mm = convert_config.options('milestone_map')
    for m in mm:
        milestone_map[m] = convert_config.get('milestone_map', m)

    # add new labels to the repo
    print("Processing labels")
    label_names = convert_config.get('github', 'labels').split(',')
    labels = {}
    gh_labels = gh_repo.get_labels()
    for ghl in gh_labels:
        labels[ghl.name] = ghl
    for name in label_names:
        name = name.strip().lower()
        if name not in labels:
            label = gh_repo.create_label(name, 'ef13e8')
            labels[name] = label
    # create map for tranlating bugzilla labels to github
    label_map = {}
    lm = convert_config.options('label_map')
    for l in lm:
        label_map[l.lower()] = convert_config.get('label_map', l).strip()

    # create the xml bug list
    xml_bug_list = convert_config.get('bugzilla', 'xml_bug_list')
    bugz_list_xml = read_bugzilla_xml(xml_bug_list)

    # add bugs to the repo
    max_attempts = 100
    found_start_bug = True
    if resume:
        found_start_bug = False
    for bug in bugz_list_xml.findall('./bug'):
        bug_id = bug.find('./bug_id').text
        if bug_id == resume:
            found_start_bug = True
        if not found_start_bug:
            print("Skipping bug {0}".format(bug_id))
            continue
        else:
            print('Processing bug {0}'.format(bug_id))

        issue_title = bug.find('./short_desc')
        # check for labels
        new_labels = []
        update_issue_label_list(bug, 'priority', labels, label_map, new_labels)
        update_issue_label_list(bug, 'bug_severity', labels, label_map, new_labels)
        # check for milestone
        new_milestone = None
        target_milestone = bug.find('./target_milestone')
        if target_milestone is not None:
            tmilestone = target_milestone.text
            tmilestone = tmilestone.strip().lower()
            new_milestone = milestones[milestone_map[tmilestone]]

        # search for optional fields that don't directly translate to gh
        cc_list = optional_list(bug, 'cc')
        blocks_list = optional_list(bug, 'blocks')
        depends_list = optional_list(bug, 'dependson')
        attachment_list = create_attachment_list(bug)
        # all text is contained in comments. comment 0 is the main
        # issue text.
        gh_issue = None
        for comment in bug.findall('./long_desc'):
            time.sleep(friendly_pause)
            comment_count = comment.find('./comment_count').text
            object_created = False
            attempts = 0
            if comment_count == '0':
                # create the issue, comment 0 is main issue text
                body_text = b2g_comment(bug_id, comment, main_issue=True,
                                        cc_list=cc_list,
                                        blocks_list=blocks_list,
                                        depends_list=depends_list,
                                        attachment_list=attachment_list)

                while (not object_created) and (attempts < max_attempts):
                    try:
                        gh_issue = gh_repo.create_issue(
                            issue_title.text, body=body_text,
                            milestone=new_milestone,
                            labels=new_labels)
                        object_created = True
                    except github.GithubException as error:
                        check_for_abuse_error(error.status, error.data)
                        attempts += 1
            else:
                # additional comments to the issue
                body_text = b2g_comment(bug_id, comment)
                while (not object_created) and (attempts < max_attempts):
                    try:
                        gh_issue.create_comment(body_text)
                        object_created = True
                    except github.GithubException as error:
                        check_for_abuse_error(error.status, error.data)
                        attempts += 1

    return 0


if __name__ == "__main__":
    options = commandline_options()
    try:
        status = main(options)
        sys.exit(status)
    except Exception as error:
        print(str(error))
        if options.backtrace:
            traceback.print_exc()
        sys.exit(1)
