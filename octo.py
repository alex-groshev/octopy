import sys
from ConfigParser import ConfigParser
import requests


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
        print 'Environments'
        for env in response:
            print 'ID: %s, Name: %s' % (env['Id'], env['Name'])
    elif command_type == 2:
        print 'Deployments'
        for dep in response['Items']:
            print 'ID: %s, Name: %s, Created: %s' % (dep['Id'], dep['Name'], dep['Created'])


if __name__ == '__main__':
    main(sys.argv[1])
