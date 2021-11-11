import sys
import configparser
import requests
import dateutil.parser
import argparse
import csv
import os


def get_configs(conf_file):
    result = {}
    cp = configparser.ConfigParser()
    cp.read(conf_file)
    result['server'] = cp.get('Octopus', 'server')
    result['api_key'] = cp.get('Octopus', 'api_key')
    result['dir_tmp'] = cp.get('Octopus', 'dir_tmp')
    return result


class UrlFactory:
    def __init__(self, server):
        self.server = server

    def url_api(self):
        return self.server + '/api'

    def url_environment(self, env_id='all'):
        return self.url_api() + '/environments/all' if env_id == 'all' else self.url_api() + '/environments/' + env_id

    def url_project(self, proj_id='all'):
        return self.url_api() + '/projects/all' if proj_id == 'all' else self.url_api() + '/projects/' + proj_id

    def url_deployments(self):
        return self.url_api() + '/deployments'

    def url_release(self, rel_id='all'):
        return self.url_api() + '/releases' if rel_id == 'all' else self.url_api() + '/releases/' + rel_id

    def url_next(self, crawl, json):
        if crawl:
            return self.server + json['Links']['Page.Next'] if json['Links'] and 'Page.Next' in json['Links'] else None
        else:
            return False

    def url_machines(self):
        return self.url_api() + '/machines/all'


class OctopyIO:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir

    def save_dict(self, file_name, dictionary):
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)
        with open('%s/%s' % (self.cache_dir, file_name), 'w') as f:
            w = csv.writer(f, delimiter=',', quotechar='|', lineterminator='\n')
            for k in dictionary.keys():
                w.writerow([k, dictionary[k]])

    def read_dict(self, file_name):
        result = {}
        full_path = '%s/%s' % (self.cache_dir, file_name)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                reader = csv.reader(f, delimiter=',', quotechar='|', lineterminator='\n')
                for row in reader:
                    result[row[0]] = row[1]
        return result

    def save_list(self, file_name, list, keys):
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)
        with open('%s/%s' % (self.cache_dir, file_name), 'w') as f:
            w = csv.DictWriter(f, keys, delimiter=',', quotechar='|', lineterminator='\n')
            w.writerows(list)

    def read_list(self, file_name, keys):
        result = []
        full_path = '%s/%s' % (self.cache_dir, file_name)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                reader = csv.DictReader(f, keys, delimiter=',', quotechar='|', lineterminator='\n')
                for row in reader:
                    result.append(row)
        return result

class Octopy:
    def __init__(self, config):
        self.environments = {}
        self.projects = {}
        self.releases = {}
        self.machines = {}
        self.deployments = []
        self.config = config
        self.url_factory = UrlFactory(self.config['server'])
        self.io = OctopyIO(self.config['dir_tmp'])
        # keys for csv
        self.keys_deployments = ['Id', 'Date', 'Time', 'Environment', 'Project', 'Release', 'SpecificMachines']
        # cache file names
        self.file_environments = 'environments.csv'
        self.file_projects = 'projects.csv'
        self.file_releases = 'releases.csv'
        self.file_deployments = 'deployments.csv'
        self.file_machines = 'machines.csv'

    def get_environments(self, cache=False):
        if cache:
            return self.io.read_dict(self.file_environments)
        self.environments = Octopy.__extract_objects(self.__scrape(self.url_factory.url_environment()), 'Id', 'Name')
        self.io.save_dict(self.file_environments, self.environments)
        return self.environments

    def get_projects(self, cache=False):
        if cache:
            return self.io.read_dict(self.file_projects)
        self.projects = Octopy.__extract_objects(self.__scrape(self.url_factory.url_project()), 'Id', 'Name')
        self.io.save_dict(self.file_projects, self.projects)
        return self.projects

    def get_machines(self, cache=False):
        if cache:
            return self.io.read_dict(self.file_machines)
        self.machines = Octopy.__extract_objects(self.__scrape(self.url_factory.url_machines()), 'Id', 'Name')
        self.io.save_dict(self.file_machines, self.machines)
        return self.machines

    def get_releases(self, cache=False, crawl=False):
        self.releases = self.io.read_dict(self.file_releases)

        if cache:
            return self.releases

        url = self.url_factory.url_release()
        while url:
            response = self.__scrape(url)
            releases = Octopy.__extract_objects(response['Items'], 'Id', 'Version')
            diff = set(releases.keys()) - set(self.releases.keys())
            if len(diff) > 0:
                for d in list(diff):
                    self.releases.update({d: releases[d]})
            # Abort crawling when no updates found
            url = False if len(diff) == 0 and crawl else self.url_factory.url_next(crawl, response)

        self.io.save_dict(self.file_releases, self.releases)
        return self.releases

    def get_deployments(self, cache=False, crawl=False):
        self.deployments = self.io.read_list(self.file_deployments, self.keys_deployments)

        if cache:
            return self.deployments

        self.get_environments(cache=False)
        self.get_projects(cache=False)
        self.get_machines(cache=False)
        self.get_releases(False, crawl)

        abort = False
        ids = {d['Id'] for d in self.deployments}
        url = self.url_factory.url_deployments()
        while url:
            response = self.__scrape(url)
            for dep in response['Items']:
                if Octopy.__get_numeric_deployment_id(dep['Id']) in ids:
                    # Stop processing, deployment is already saved
                    abort = True
                    break

                if not crawl:
                    if dep['ReleaseId'] not in self.releases:
                        release = self.__scrape(self.url_factory.url_release(dep['ReleaseId']))
                        self.releases[release['Id']] = release['Version']

                dt = dateutil.parser.parse(dep['Created'])

                self.deployments.append({
                    'Id': Octopy.__get_numeric_deployment_id(dep['Id']),
                    'Date': dt.date(),
                    'Time': dt.time().strftime('%H:%M'),
                    'Environment': self.environments[dep['EnvironmentId']],
                    'Project': self.projects[dep['ProjectId']],
                    'Release': self.releases[dep['ReleaseId']],
                    'SpecificMachines': self.__extract_machines(dep['SpecificMachineIds'])
                })
            url = False if abort else self.url_factory.url_next(crawl, response)

        self.io.save_dict(self.file_projects, self.projects)
        self.io.save_dict(self.file_releases, self.releases)
        self.io.save_list(self.file_deployments, self.deployments, self.keys_deployments)
        return self.deployments

    def __extract_machines(self, machine_ids):
        if machine_ids:
            for m_id in machine_ids:
                if m_id not in self.machines:
                    # Assume machine is deleted if it doesn't exist in 'machines' array.
                    self.machines[m_id] = 'DEL-' + m_id
            return ','.join([self.machines[x] for x in machine_ids])
        else:
            return ''

    def __scrape(self, url):
        if __debug__:
            print('GET:', url)
        return requests.get(url, headers={'X-Octopus-ApiKey': self.config['api_key']}).json()

    @staticmethod
    def __extract_objects(json, o_id, o_value):
        result = {}
        for obj in json:
            result[obj[o_id]] = obj[o_value]
        return result

    @staticmethod
    def __get_numeric_deployment_id(an_deployment_id):
        return an_deployment_id[12:]


def main():
    config = get_configs('octopy.cfg')

    if not config['server'] or not config['api_key']:
        print('Please, specify Octopus parameters in configuration file!')
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Octopy is a small application that prints out information from Octopus in a convenient format.')
    parser.add_argument('--cmd', dest='command', help="Octopy command (try `env`, `proj`, `rel`, `dep` and `mac`).")
    parser.add_argument('--cache', dest='cache', action='store_true', help="Read data from cache if available.")
    parser.add_argument('--headers', dest='headers', action='store_true', help='Display headers in output.')
    parser.add_argument('--crawl', dest='crawl', action='store_true',
        help='By default only 30 items per page are returned by API. This parameter enables link crawl. '
             'All resources from the `Link` collection will be crawled by Octopy and data will be saved to cache. '
             'This parameter has no effect on `env` and `proj` commands.')
    args = parser.parse_args()

    octopy = Octopy(config)

    if args.command == 'env':  # environments
        environments = octopy.get_environments(args.cache)
        if args.headers:
            print('Id,Name')
        for key in environments.keys():
            print('%s,%s' % (key, environments[key]))
    elif args.command == 'proj':  # projects
        projects = octopy.get_projects(args.cache)
        if args.headers:
            print('Id,Name')
        for key in projects.keys():
            print('%s,%s' % (key, projects[key]))
    elif args.command == 'rel':  # releases
        releases = octopy.get_releases(args.cache, args.crawl)
        if args.headers:
            print('Id,Version')
        for key in releases.keys():
            print('%s,%s' % (key, releases[key]))
    elif args.command == 'mac': # machines
        machines = octopy.get_machines(args.cache)
        if args.headers:
            print('Id,Name')
        for key in machines.keys():
            print('%s,%s' % (key, machines[key]))
    elif args.command == 'dep':  # deployments
        deployments = octopy.get_deployments(args.cache, args.crawl)
        if args.headers:
            print('Date,Time,Environment,Project,Release,SpecificMachines')
        for dep in deployments:
            print('%s,%s,%s,%s,%s,%s' %\
                  (dep['Date'], dep['Time'], dep['Environment'], dep['Project'], dep['Release'], dep['SpecificMachines']))
    else:
        print("Unknown command '%s'" % args.command)
        parser.print_help()


if __name__ == '__main__':
    main()
