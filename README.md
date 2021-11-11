Octopy
======

Octopy is a small application that prints out information from [Octopus Deploy](http://octopus.com/) in CSV format. It's built on top of the
[Octopus REST API](https://octopus.com/docs/octopus-rest-api).

Tested on
- Octopus Deploy ver. 2.4.5.x, 2.5.x, 2.6.2.x, 2019.6.x
- Octopus REST API ver. 3.0.0

Supported Commands
- "--cmd env" - Environments (Id, Name)
- "--cmd proj" - Projects (Id, Name)
- "--cmd rel" - Releases (Id, Version)
- "--cmd dep" - Deployments ([Id], Date, Time, Environment, Project, Release, Specific Machines)
- "--cmd mac" - Machines (Id, Name)

Extras
- Octopy saves/reads data to/from CSV files. Specify "--cache" to read data from files.
- Specify "--headers" to print column names.
- "--crawl" enables link crawl. By default only 30 items per page are returned by API. All resources from the "Link" collection will be crawled by Octopy and data will be saved to cache. 
