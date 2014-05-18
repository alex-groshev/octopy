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


class Octopy:
    def __init__(self, config):
        self.environments = {}
        self.projects = {}
        self.releases = {}
        self.deployments = []
        self.config = config
        self.url_factory = UrlFactory(self.config['server'])
        # cache file names
        self.file_environments = 'environments.csv'
        self.file_projects = 'projects.csv'
        self.file_releases = 'releases.csv'
        self.file_deployments = 'deployments.csv'

    def get_environments(self, cache=False):
        if cache:
            return self.__read_objects(self.file_environments)
        self.environments = Octopy.__extract_objects(self.__scrape(self.url_factory.url_environment()), 'Id', 'Name')
        self.__save_objects(self.file_environments, self.environments)
        return self.environments

    def get_projects(self, cache=False):
        if cache:
            return self.__read_objects(self.file_projects)
        self.projects = Octopy.__extract_objects(self.__scrape(self.url_factory.url_project()), 'Id', 'Name')
        self.__save_objects(self.file_projects, self.projects)
        return self.projects

    def get_releases(self, cache=False, crawl=False):
        if cache:
            return self.__read_objects(self.file_releases)

        url = self.url_factory.url_release()
        while url:
            response = self.__scrape(url)
            self.releases.update(Octopy.__extract_objects(response['Items'], 'Id', 'Version'))
            url = self.__get_next_url(crawl, response)

        self.__save_objects(self.file_releases, self.releases)
        return self.releases

    def get_deployments(self, cache=False, crawl=False):
        if cache:
            return self.__read_list(self.file_deployments)

        self.get_environments(cache=False)
        self.get_projects(cache=False)
        self.get_releases(False, crawl)
        self.deployments = []

        url = self.url_factory.url_deployments()
        while url:
            response = self.__scrape(url)
            for dep in response['Items']:
                if not crawl:
                    if dep['ReleaseId'] not in self.releases:
                        release = self.__scrape(self.url_factory.url_release(dep['ReleaseId']))
                        self.releases[release['Id']] = release['Version']

                dt = dateutil.parser.parse(dep['Created'])

                self.deployments.append({
                    'Id': dep['Id'],
                    'Date': dt.date(),
                    'Time': dt.time().strftime('%H:%M'),
                    'Environment': self.environments[dep['EnvironmentId']],
                    'Project': self.projects[dep['ProjectId']],
                    'Release': self.releases[dep['ReleaseId']]
                })
            url = self.__get_next_url(crawl, response)

        self.__save_objects(self.file_projects, self.projects)
        self.__save_objects(self.file_releases, self.releases)
        self.__save_list(self.file_deployments, self.deployments)
        return self.deployments

    def __scrape(self, url):
        return requests.get(url, headers={'X-Octopus-ApiKey': self.config['api_key']}).json()

    @staticmethod
    def __extract_objects(json, o_id, o_value):
        result = {}
        for obj in json:
            result[obj[o_id]] = obj[o_value]
        return result

    def __save_objects(self, file_name, objects):
        if not os.path.isdir(self.config['dir_tmp']):
            os.makedirs(self.config['dir_tmp'])
        with open('%s/%s' % (self.config['dir_tmp'], file_name), 'w') as f:
            w = csv.writer(f, delimiter=',', quotechar='|', lineterminator='\n')
            for k in objects.keys():
                w.writerow([k, objects[k]])

    def __read_objects(self, file_name):
        result = {}
        with open('%s/%s' % (self.config['dir_tmp'], file_name), 'r') as f:
            reader = csv.reader(f, delimiter=',', quotechar='|', lineterminator='\n')
            for row in reader:
                result[row[0]] = row[1]
        return result

    def __save_list(self, file_name, list):
        if not os.path.isdir(self.config['dir_tmp']):
            os.makedirs(self.config['dir_tmp'])
        keys = ['Id', 'Date', 'Time', 'Environment', 'Project', 'Release']
        with open('%s/%s' % (self.config['dir_tmp'], file_name), 'w') as f:
            w = csv.DictWriter(f, keys, delimiter=',', quotechar='|', lineterminator='\n')
            w.writerows(list)

    def __read_list(self, file_name):
        result = []
        keys = ['Id', 'Date', 'Time', 'Environment', 'Project', 'Release']
        with open('%s/%s' % (self.config['dir_tmp'], file_name), 'r') as f:
            reader = csv.DictReader(f, keys, delimiter=',', quotechar='|', lineterminator='\n')
            for row in reader:
                result.append(row)
        return result

    def __get_next_url(self, crawl, json):
        if crawl:
            return self.config['server'] + json['Links']['Page.Next'] if json['Links'] and 'Page.Next' in json['Links'] else None
        else:
            return None


def main():
    config = get_configs('octopy.cfg')

    if not config['server'] or not config['api_key']:
        print 'Please, specify Octopus parameters in configuration file!'
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Octopy is a small application that prints out information from Octopus in a convenient format.')
    parser.add_argument('--cmd', dest='command', help="Octopy command (try `env`, `proj`, `rel` and `dep`).")
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
            print 'Id,Name'
        for key in environments.keys():
            print '%s,%s' % (key, environments[key])
    elif args.command == 'proj':  # projects
        projects = octopy.get_projects(args.cache)
        if args.headers:
            print 'Id,Name'
        for key in projects.keys():
            print '%s,%s' % (key, projects[key])
    elif args.command == 'rel':  # releases
        releases = octopy.get_releases(args.cache, args.crawl)
        if args.headers:
            print 'Id,Version'
        for key in releases.keys():
            print '%s,%s' % (key, releases[key])
    elif args.command == 'dep':  # deployments
        deployments = octopy.get_deployments(args.cache, args.crawl)
        if args.headers:
            print 'Date,Time,Environment,Project,Release'
        for dep in deployments:
            print '%s,%s,%s,%s,%s' % (dep['Date'], dep['Time'], dep['Environment'], dep['Project'], dep['Release'])
    else:
        print "Unknown command '%s'" % args.command
        parser.print_help()


if __name__ == '__main__':
    main()
