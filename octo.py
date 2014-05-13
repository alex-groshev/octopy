import sys
from ConfigParser import ConfigParser
import requests
import dateutil.parser


class OctopyUrlFactory:
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


class OctoScraper:
    @staticmethod
    def scrape(url, headers):
        return requests.get(url, headers=headers).json()


def cmd_environments(response):
    for env in response:
        print 'ID: %s, Name: %s' % (env['Id'], env['Name'])


def main(command):
    config = ConfigParser()
    config.read('octopy.cfg')

    server = config.get('Octopus', 'server')
    api_key = config.get('Octopus', 'api_key')

    if not server or not api_key:
        print 'Please, specify Octopus parameters in configuration file!'
        sys.exit(1)

    headers = {
        'X-Octopus-ApiKey': api_key
    }

    octopyUrlFactory = OctopyUrlFactory(server)
    url, command_type = octopyUrlFactory.get_url(command)

    if command_type == 0:
        print "Unknown command '%s'" % command
        sys.exit(1)

    response = OctoScraper.scrape(url, headers)

    if command_type == 1:
        cmd_environments(response)
    elif command_type == 2:
        print 'Date,Time,Environment'
        for dep in response['Items']:
            #TBD: get rid of factory and get a link from Links?
            env = OctoScraper.scrape(octopyUrlFactory.url_environment(dep['EnvironmentId']), headers)
            dt = dateutil.parser.parse(dep['Created'])
            print '%s,%s,%s' % (dt.date(), dt.time().strftime('%H:%M'), env['Name'])


if __name__ == '__main__':
    main(sys.argv[1])
