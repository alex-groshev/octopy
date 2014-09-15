Octopy
======

Octopy is a small application that prints out information from [Octopus Deploy](http://octopusdeploy.com/) in CSV format. It's built on top of the
[Octopus REST API](http://docs.octopusdeploy.com/display/OD/Octopus+REST+API).

Tested on
- Octopus Deploy ver. 2.5.x
- Octopus REST API ver. 3.0.0

Supported Commands
- env - Environments (Id, Name)
- proj - Projects (Id, Name)
- rel - Releases (Id, Version)
- dep - Deployments ([Id], Date, Time, Environment, Project, Release, Specific Machines)
- mac - Machines (Id, Name)

Extras
- Octopy saves/reads data to/from csv files. Specify --cache to read data from files only.
- Specify --headers to print column names.
- crawl By default only 30 items per page are returned by API. This parameter enables link crawl.
  All resources from the "Link" collection will be crawled by Octopy and data will be saved to cache. 