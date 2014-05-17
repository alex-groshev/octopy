import sys
from ConfigParser import ConfigParser
import requests
import dateutil.parser
import argparse
import csv
import os


def get_configs(conf_file):
    result = {}
    cp = ConfigParser()
    cp.read(conf_file)
    result['server'] = cp.get('Octopus', 'server')
    result['api_key'] = cp.get('Octopus', 'api_key')
    result['dir_tmp'] = cp.get('Octopus', 'dir_tmp')
    return result


class UrlFactory:
    def __init__(self, server):
        self.server = server

    def get_url(self, command):
        if command == 'env':
            return self.url_environment(), 1
        elif command == 'dep':
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


def extract_objects(json, o_id, o_value):
    result = {}
    for obj in json:
        result[obj[o_id]] = obj[o_value]
    return result


def save_objects(dir_name, file_name, objects):
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    with open('%s/%s' % (dir_name, file_name), 'w') as f:
        w = csv.writer(f, delimiter=',', quotechar='|', lineterminator='\n')
        for k in objects.keys():
            w.writerow([k, objects[k]])


def read_objects(dir_name, file_name):
    result = {}
    with open('%s/%s' % (dir_name, file_name), 'r') as f:
        reader = csv.reader(f, delimiter=',', quotechar='|', lineterminator='\n')
        for row in reader:
            result[row[0]] = row[1]
    return result


def save_list(dir_name, file_name, list):
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    keys = ['Id', 'Date', 'Time', 'Environment', 'Project', 'Release']
    with open('%s/%s' % (dir_name, file_name), 'w') as f:
        w = csv.DictWriter(f, keys, delimiter=',', quotechar='|', lineterminator='\n')
        w.writerows(list)


def read_list(dir_name, file_name):
    result = []
    keys = ['Id', 'Date', 'Time', 'Environment', 'Project', 'Release']
    with open('%s/%s' % (dir_name, file_name), 'r') as f:
        reader = csv.DictReader(f, keys, delimiter=',', quotechar='|', lineterminator='\n')
        for row in reader:
            result.append(row)
    return result


def main():
    config = get_configs('octopy.cfg')

    if not config['server'] or not config['api_key']:
        print 'Please, specify Octopus parameters in configuration file!'
        sys.exit(1)

    parser = argparse.ArgumentParser(description='OctoPy is a small application that prints out information from Octopus in a convenient format.')
    parser.add_argument('--cmd', dest='command', help="Octopy command (try `env` and `dep`).")
    parser.add_argument('--cache', dest='cache', action='store_true', help="Read data from cache if available.")
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

    if args.cache:
        environments = read_objects(config['dir_tmp'], 'environments.csv')
    else:
        environments = extract_objects(scrape(urlFactory.url_environment(), config['api_key']), 'Id', 'Name')
        for env in environments.keys():
            environments[env] = environments[env]
        save_objects(config['dir_tmp'], 'environments.csv', environments)

    if command_type == 1:
        if args.headings:
            print 'Id,Name'
        for env in environments.keys():
            print '%s,%s' % (env, environments[env])
    elif command_type == 2:
        if args.headings:
            print 'Date,Time,Environment,Project,Release'

        if args.cache:
            deployments = read_list(config['dir_tmp'], 'deployments.csv')
            for deployment in deployments:
                print '%s,%s,%s,%s,%s' % \
                      (deployment['Date'], deployment['Time'], deployment['Environment'], deployment['Project'], deployment['Release'])
            sys.exit(0)

        projects = extract_objects(scrape(urlFactory.url_project(), config['api_key'])['Items'], 'Id', 'Name')
        releases = extract_objects(scrape(urlFactory.url_release(), config['api_key'])['Items'], 'Id', 'Version')

        response = scrape(url, config['api_key'])
        deployments = []

        for dep in response['Items']:
            dt = dateutil.parser.parse(dep['Created'])

            if dep['ReleaseId'] not in releases:
                rel = scrape(urlFactory.url_release(dep['ReleaseId']), config['api_key'])
                releases[rel['Id']] = rel['Version']

            if dep['ProjectId'] not in projects:
                proj = scrape(urlFactory.url_project(dep['ProjectId']), config['api_key'])
                projects[proj['Id']] = proj['Name']

            deployment = {
                'Id': dep['Id'],
                'Date': dt.date(),
                'Time': dt.time().strftime('%H:%M'),
                'Environment': environments[dep['EnvironmentId']],
                'Project': projects[dep['ProjectId']],
                'Release': releases[dep['ReleaseId']]
            }
            deployments.append(deployment)
            print '%s,%s,%s,%s,%s' %\
                  (deployment['Date'], deployment['Time'], deployment['Environment'], deployment['Project'], deployment['Release'])

        save_objects(config['dir_tmp'], 'projects.csv', projects)
        save_objects(config['dir_tmp'], 'releases.csv', releases)
        save_list(config['dir_tmp'], 'deployments.csv', deployments)


if __name__ == '__main__':
    main()
