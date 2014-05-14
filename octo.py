import sys
from ConfigParser import ConfigParser
import requests
import dateutil.parser
import argparse


class UrlFactory:
    def __init__(self, server):
        self.server = server

    def get_url(self, command):
        if command == 'env' or command == 'environments':
            return self.url_environment(), 1
        elif command == 'dep' or command == 'deployments':
            return self.url_deployments(), 2
        else:
            return None, 0

    def url_api(self):
        return self.server + '/api'

    def url_environment(self, env_id='all'):
        return self.url_api() + '/environments/all' if env_id == 'all' else self.url_api() + '/environments/' + env_id

    def url_deployments(self):
        return self.url_api() + '/deployments'

    def url_release(self, rel_id='all'):
        return self.url_api() + '/releases' if rel_id == 'all' else self.url_api() + '/releases/' + rel_id

    def url_project(self, proj_id='all'):
        return self.url_api() + '/projects' if proj_id == 'all' else self.url_api() + '/projects/' + proj_id


def scrape(url, api_key):
    return requests.get(url, headers={'X-Octopus-ApiKey': api_key}).json()


def get_configs(conf_file):
    result = {}
    cp = ConfigParser()
    cp.read(conf_file)
    result['server'] = cp.get('Octopus', 'server')
    result['api_key'] = cp.get('Octopus', 'api_key')
    return result


def parse_environments(response):
    result = {}
    for env in response:
        result[env['Id']] = env['Name']
    return result


def parse_releases(response):
    result = {}
    for rel in response['Items']:
        result[rel['Id']] = rel['Version']
    return result


def parse_projects(response):
    result = {}
    for proj in response['Items']:
        result[proj['Id']] = proj['Version']
    return result


def main():
    config = get_configs('octopy.cfg')

    if not config['server'] or not config['api_key']:
        print 'Please, specify Octopus parameters in configuration file!'
        sys.exit(1)

    parser = argparse.ArgumentParser(description='OctoPy is a small application that prints out information from Octopus in a convenient format.')
    parser.add_argument('--cmd', dest='command', help="Octopy command (try `env` and `dep`).")
    parser.add_argument('--headings', dest='headings', action='store_true', help='Display headings in output.')
    args = parser.parse_args()

    if args.command is None:
        print "Please specify command"
        parser.print_help()
        sys.exit(1)

    urlFactory = UrlFactory(config['server'])
    url, command_type = urlFactory.get_url(args.command)

    if command_type == 0:
        print "Unknown command '%s'" % args.command
        sys.exit(1)

    environments = parse_environments(scrape(urlFactory.url_environment(), config['api_key']))

    if command_type == 1:
        if args.headings:
            print 'Id,Name'
        for env in environments.keys():
            print '%s,%s' % (env, environments[env])
    elif command_type == 2:
        if args.headings:
            print 'Date,Time,Environment,Project,Release'

        deployments = scrape(url, config['api_key'])
        projects = scrape(urlFactory.url_project(), config['api_key'])
        releases = parse_releases(scrape(urlFactory.url_release(), config['api_key']))

        for dep in deployments['Items']:
            dt = dateutil.parser.parse(dep['Created'])

            if dep['ReleaseId'] not in releases:
                rel = scrape(urlFactory.url_release(dep['ReleaseId']), config['api_key'])
                releases[rel['Id']] = rel['Version']

            if dep['ProjectId'] not in projects:
                proj = scrape(urlFactory.url_project(dep['ProjectId']), config['api_key'])
                projects[proj['Id']] = proj['Name']

            print '%s,%s,%s,%s,%s' %\
                  (dt.date(), dt.time().strftime('%H:%M'), environments[dep['EnvironmentId']], projects[dep['ProjectId']], releases[dep['ReleaseId']])


if __name__ == '__main__':
    main()
