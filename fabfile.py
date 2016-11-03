# -*- coding: utf-8 -*-


import time

from fabric.contrib.files import exists
from fabric.operations import require, local, sudo, run, put
from fabric.state import env

from conf.production.server import production


env.project_name = 'sitedoicaro'

servers = [production]


def test():
    """ Run test cases before deploying, stops deployment if any error occurs. """
    local('python manage.py test -n')


# noinspection SpellCheckingInspection
def setup():
    """ Setup the machine to receive a new (or first) server instance and then runs deployment. """
    require('hosts', provided_by=servers)
    require('path')
    packages_to_install = ['build-essential', 'python-setuptools', 'python-dev', 'libevent-dev', 'libmysqlclient-dev', 'python-mysqldb', 'libjpeg8-dev', 'nginx', 'git-core', 'upstart', 'upstart-sysv']
    for package in packages_to_install:
        sudo('apt-get install -y ' + package)
    sudo('easy_install pip')
    sudo('pip install virtualenv')
    run('mkdir -p %(path)s; cd %(path)s; virtualenv env;' % env)
    run('cd %(path)s; mkdir releases; mkdir packages; mkdir logs; mkdir static; mkdir media; chmod -R 777 media;' % env)
    deploy()


def deploy():
    """ Deploy the latest version of the site to the servers. Install any required third party modules, install the virtual host and then restart the webserver. """
    test()
    require('hosts', provided_by=servers)
    require('path')
    env.release = time.strftime('%Y-%m-%d-%H-%M')
    upload_tar_from_git()
    install_requirements()
    install_site()
    symlink_current_release()
    migrate()
    collect_static()
    restart_webserver()
    remove_remote_package()


def rollback():
    """ Roll back to the previously current version of the code. Rolling back again will swap between the two latest versions. """
    require('hosts', provided_by=servers)
    require('path')
    run('cd %(path)s; mv releases/current releases/_previous;' % env)
    run('cd %(path)s; mv releases/previous releases/current;' % env)
    run('cd %(path)s; mv releases/_previous releases/previous;' % env)
    restart_webserver()


def upload_tar_from_git():
    """ Create an archive from the current git master branch and upload it. """
    require('release', provided_by=[deploy, setup])
    local('git archive --format=tar %(git_branch)s | gzip > %(release)s.tar.gz' % env)
    run('mkdir %(path)s/releases/%(release)s' % env)
    put('%(release)s.tar.gz' % env, '%(path)s/packages/' % env)
    run('cd %(path)s/releases/%(release)s && tar zxf ../../packages/%(release)s.tar.gz' % env)
    local('rm %(release)s.tar.gz' % env)


def install_site():
    """ Add the virtual host file to NGINX. """
    require('config_dir')
    require('service_name')
    require('site_name')
    require('release', provided_by=[deploy, setup])
    put('conf/%(config_dir)s/service.conf' % env, '/etc/init/%(service_name)s.conf' % env, use_sudo=True)
    put('conf/%(config_dir)s/nginx.conf' % env, '/etc/nginx/sites-available/%(site_name)s' % env, use_sudo=True)
    if not exists('/etc/nginx/sites-enabled/%(site_name)s' % env):
        sudo('ln -s /etc/nginx/sites-available/%(site_name)s /etc/nginx/sites-enabled/%(site_name)s' % env)


def install_requirements():
    """ Install the required packages from the requirements file using pip. """
    require('release', provided_by=[deploy, setup])
    run('source %(path)s/env/bin/activate; cd %(path)s; pip install -r ./releases/%(release)s/conf/requirements.txt' % env)


def symlink_current_release():
    """ Symlink our current release. """
    require('release', provided_by=[deploy, setup])
    if exists('%(path)s/releases/previous' % env):
        run('rm %(path)s/releases/previous' % env)
    if exists("%(path)s/releases/current" % env):
        run('mv %(path)s/releases/current %(path)s/releases/previous' % env)
    run('ln -s %(path)s/releases/%(release)s/ %(path)s/releases/current' % env)
    put('conf/%(config_dir)s/local.py' % env, '%(path)s/releases/current/%(project_name)s/' % env)
    put('conf/%(config_dir)s/wsgi.py' % env, '%(path)s/releases/current/wsgi.py' % env)


def migrate():
    """ Migrate the database if it has changes. """
    require('project_name')
    run('source %(path)s/env/bin/activate; cd %(path)s/releases/current/; python manage.py migrate --noinput' % env)


def collect_static():
    """ Collect static files from all Django apps. """
    run('source %(path)s/env/bin/activate; cd %(path)s/releases/current/; python manage.py collectstatic --noinput' % env)


# noinspection PyBroadException
def restart_webserver():
    """ Restart the webserver to apply changes. """
    require('service_name')
    sudo('service nginx reload')
    try:
        sudo('stop %(service_name)s' % env)
    except:  # Might be already stopped
        pass
    try:
        sudo('start %(service_name)s' % env)
    except:  # Might be already started
        pass


def remove_remote_package():
    u""" Remove the git package for this release. """
    run('rm %(path)s/packages/%(release)s.tar.gz' % env)
