# youth-membership
Backend for youth membership profile

[![status](https://travis-ci.com/City-of-Helsinki/youth-membership.svg)](https://github.com/City-of-Helsinki/youth-membership)
[![pipeline status](https://gitlab.com/City-of-Helsinki/KuVa/github-mirrors/youth-membership/badges/develop/pipeline.svg)](https://gitlab.com/City-of-Helsinki/KuVa/github-mirrors/youth-membership/-/commits/develop)
[![codecov](https://codecov.io/gh/City-of-Helsinki/youth-membership/branch/develop/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/youth-membership)


## Summary

Youth membership profile is implemented using Django and it provides a GraphQL API.

## Development with [Docker](https://docs.docker.com/)

Prerequisites:
* Docker engine: 18.06.0+
* Docker compose 1.22.0+

1. Create a `docker-compose.env.yaml` file in the project folder:
   * Use `docker-compose.env.yaml.example` as a base, it does not need any changes for getting the project running.
   * Set entrypoint/startup variables according to taste.
     * `DEBUG`, controls debug mode on/off
     * `TOKEN_AUTH_*`, settings for [tunnistamo](https://github.com/City-of-Helsinki/tunnistamo) authentication service
     * `OIDC_CLIENT_SECRET` tunnistamo client secret for enabling OIDC admin loging and authorization code flows
     * `GDPR_API_ENABLED`, enable the GDPR API for youth profiles
     * `ENABLE_GRAPHIQL`, enables GraphiQL interface for `/graphql/`
     * `APPLY_MIGRATIONS`, applies migrations on startup
     * `CREATE_ADMIN_USER`, creates an admin user with credentials `kuva-admin`:(password, see below)
     (kuva-admin@hel.ninja)
     * `ADMIN_USER_PASSWORD`, the admin user's password. If this is not given, a random password is generated
     and written into stdout when an admin user is created automatically.
     * `HELSINKI_PROFILE_API_URL` URL for the Helsinki profile GraphQL API
     * `HELSINKI_PROFILE_AUTH_SCOPE` OAuth/OIDC scope for open-city-profile
     * `HELSINKI_PROFILE_AUTH_CALLBACK_URL` Callback URL used by the UI for fetching OAuth/OIDC authorization token
     for open-city-profile
     * `AUDIT_LOGGING_ENABLED`, enable audit logging for the backend
     * `AUDIT_LOG_USERNAME`, audit logs contain the username

2. Run `docker-compose up`
    * The project is now running at [localhost:8081](http://localhost:8081)

**Optional steps**

1. Run migrations:
    * Taken care by the example env
    * `docker exec youth-membership-backend python manage.py migrate`

2. Create superuser:
    * Taken care by the example env
    * `docker exec -it youth-membership-backend python manage.py add_admin_user`


## Development without Docker

Prerequisites:
* PostgreSQL 10
* Python 3.8


### Installing Python requirements

* Run `pip install -r requirements.txt`
* Run `pip install -r requirements-dev.txt` (development requirements)


### Database

To setup a database compatible with default database settings:

Create user and database

    sudo -u postgres createuser -P -R -S youth_membership  # use password `youth_membership`
    sudo -u postgres createdb -O youth_membership youth_membership

Allow user to create test database

    sudo -u postgres psql -c "ALTER USER youth_membership CREATEDB;"


### Daily running

* Create `.env` file: `touch .env`
* Set the `DEBUG` environment variable to `1`.
* Run `python manage.py migrate`
* Run `python manage.py add_admin_user`
* Run `python manage.py runserver 0:8000`

The project is now running at [localhost:8000](http://localhost:8000)


## Keeping Python requirements up to date

1. Install `pip-tools`:
    * `pip install pip-tools`

2. Add new packages to `requirements.in` or `requirements-dev.in`

3. Update `.txt` file for the changed requirements file:
    * `pip-compile requirements.in`
    * `pip-compile requirements-dev.in`

4. If you want to update dependencies to their newest versions, run:
    * `pip-compile --upgrade requirements.in`

5. To install Python requirements run:
    * `pip-sync requirements.txt`

## Code format

This project uses
[`black`](https://github.com/ambv/black),
[`flake8`](https://gitlab.com/pycqa/flake8) and
[`isort`](https://github.com/timothycrosley/isort)
for code formatting and quality checking. Project follows the basic
black config, without any modifications.

Basic `black` commands:

* To let `black` do its magic: `black .`
* To see which files `black` would change: `black --check .`

[`pre-commit`](https://pre-commit.com/) can be used to install and
run all the formatting tools as git hooks automatically before a
commit.


## Running tests

* Set the `DEBUG` environment variable to `1`.
* Run `pytest`.


## Issue tracking

* [Github issue list](https://github.com/City-of-Helsinki/youth-membership/issues)
* [Jira issues](https://helsinkisolutionoffice.atlassian.net/projects/YM/issues/?filter=allissues)


## API documentation

* [Generated GraphiQL documentation](https://jassari-api.test.kuva.hel.ninja/graphql/)


## Environments
Test: https://jassari-api.test.kuva.hel.ninja/graphql/

Production: https://jassari-api.prod.kuva.hel.ninja/graphql/

## CI/CD builds

Project is using [Gitlab](https://gitlab.com/City-of-Helsinki/KuVa/github-mirrors/youth-membership/pipelines)
for automated builds and deployment into the test environment.
The test environment is built automatically from the `develop` branch.

## Dependent services

For a complete service the following additional components are also required:
* [tunnistamo](https://github.com/City-of-Helsinki/tunnistamo) is used as the authentication service
* [open-city-profile](https://github.com/City-of-Helsinki/open-city-profile/) provides open city profile backend UI
* [open-city-profile-ui](https://github.com/City-of-Helsinki/open-city-profile-ui/) provides open city profile UI
* [youth-membership-ui](https://github.com/City-of-Helsinki/youth-membership-ui/) provides youth membership UI
* [youth-membership-admin-ui](https://github.com/City-of-Helsinki/youth-membership-admin-ui/) provides youth membership admin UI
