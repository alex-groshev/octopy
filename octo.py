import sys
from ConfigParser import ConfigParser
import requests
import dateutil.parser


def prepare_url(server, command):
    command_type = 0
    url = server + '/api'
    if command == 'env' or command == 'environments':
        url += '/environments/all'
        command_type = 1
    elif command == 'dep' or command == 'deployments':
        url += '/deployments'
        command_type = 2
    return url, command_type


def cmd_environments(response):
    for env in response:
        print 'ID: %s, Name: %s' % (env['Id'], env['Name'])


def cmd_deployments(response):
    for dep in response['Items']:
        dt = dateutil.parser.parse(dep['Created'])
        print 'ID: %s, Name: %s, Created: %s at %s' %\
              (dep['Id'], dep['Name'], dt.date(), dt.time().strftime('%H:%M'))



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

    url, command_type = prepare_url(server, command)
    if command_type == 0:
        print 'Unknown command'
        sys.exit(1)

    response = requests.get(url, headers=headers).json()

    if command_type == 1:
        cmd_environments(response)
    elif command_type == 2:
        cmd_deployments(response)


if __name__ == '__main__':
    main(sys.argv[1])
