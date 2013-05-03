import redis
import os
import commands
import time
import json
import sys
from daemon import Daemon

class MiUp(Daemon):
    rootpath = '/git/miup_python/'
    rpmbuildpath = '/usr/src/rpmbuild/'
    destdir = '/data/www/10.xiaomi.com'
    homepath = '/home/xiaoqing/'
    redis_host = '10.237.93.17'
    redis_port = 6379

    #def __init__(self):
    rds = redis.Redis(host = redis_host, port = redis_port, db = 0)

    #TODO write logs and error handling
    def run(self):
        while (True):

            task = self.rds.lpop('miup_task_' + self.queue_id)
            print 'miup_task_' + self.queue_id
            if not task:
                print 'No task'
                time.sleep(1)
                continue
            print task
            #Step1: floder 'rep/xxx' update to the release version
            print '---up---'
            print self.up_to_version(task_info, task_info['release_ver'])

            #Step2: rsync folder 'rpmsrc/xxx'
            print '---rsync---'
            print self.rsync(task_info['release_exclude'])

            #Step3: make xxx.tar.gz
            srcpath = 'rpmsrc/' + task_info['project_id']
            tarname = task_info['project_id']
            tarversion = task_info['task_id']
            print '---mktar---'
            print self.mktar(srcpath, tarname + '-' + tarversion)

            #Step4: make xxx.rpm
            #Step4.1 make spec file
            print '---mkspec---'
            print self.mkspec(tarname, tarversion, task_info['release_server']['path'])
            #Step4.2 make xxx.rpm
            print '---rpmbuild---'
            print self.rpmbuild(tarname + '-' + tarversion)
            print 'rpmbuild finished'

            #Step5: upload to the package server
            #TODO

    def mkspec(self, tarname, tarversion, destdir):
        content = 'Name:       ' + tarname + '\r\n'
        content += 'Version:    ' + tarversion
        content += '''
Release:    1
Summary:    Just a demo test
Group:      A group
License:    A license
Source0:    %{name}-%{version}.tar.gz
Autoreq:    No
%description
description description description description description
'''
        content += '%define DESTDIR ' + destdir
        content += '''
%prep
%setup -q
%install
rm -rf $RPM_BUILD_ROOT
mkdir -p %{buildroot}/%{DESTDIR}/%{name}-%{version}
cp -r * %{buildroot}/%{DESTDIR}/%{name}-%{version}
%clean
rm -rf $RPM_BUILD_DIR/*
rm -rf $RPM_BUILD_ROOT
%files
%{DESTDIR}/*
%dir %{DESTDIR}/
'''
        #print content
        f = open(self.rpmbuildpath + 'SPECS/' + tarname + '-' + tarversion+ '.spec', 'w')
        f.write(content)
       


    def mktar(self, srcpath, tarname):
        cmd = 'cp -r ' + srcpath + ' ' + self.rpmbuildpath + 'SOURCES/' + tarname
        cmd += '; cd ' + self.rpmbuildpath + 'SOURCES; tar zcf ' + tarname + '.tar.gz ' + tarname
        cmd += '; rm -rf ' + tarname
        #print cmd
        status, output = commands.getstatusoutput(cmd)
        return status, output

    def rpmbuild(self, tarname):
        #TODO: VERIFY SPEC file and tgz file
        cmd = "rpmbuild -ba " + self.rpmbuildpath + 'SPECS/' + tarname + '.spec'
        print cmd
        status, output = commands.getstatusoutput(cmd)
        return status, output

    def checkout_svn(self, task_info, version):
        cmd_version = ""
        if version != 0:
            cmd_version = ' -r ' + version
        cmd = "svn co -q " + cmd_version + " " + task_info['rep_proto']+ "://" +\
                task_info['rep_host'] + ":" + task_info['rep_port'] + "/" + task_info['rep_path'] +\
                " --username " + task_info['rep_user'] + " --password " + task_info['rep_pass'] +\
                " --no-auth-cache --non-interactive rep/" + task_info['project_id'] +\
                " > /dev/null 2>&1"
        print cmd
        status, output = commands.getstatusoutput(cmd)
        return status, output

    def update_svn(self, task_info, version = 0):
        cmd_version = ""
        if version != 0:
            cmd_version = ' -r ' + version
        cmd = "svn up -q " + cmd_version + " --no-auth-cache --non-interactive rep/" + task_info['project_id'] + " > /dev/null 2>&1"
        print cmd
        status, output = commands.getstatusoutput(cmd)
        return status, output

    def svn_up_to_version(self, task_info, version):
        path = "rep/" + task_info['project_id']
        if os.path.exists(path):
            print 'up'
            return self.update_svn(task_info, version)
        else:
            print 'co'
            return self.checkout_svn(task_info, version)

    def git_up_to_version(self, task_info, version):
        path = "rep/" + task_info['project_id']
        if os.path.exists(path):
            print 'pull'
            cmd = "git pull"
        else:
            print 'clone'
            cmd = "git clone " + task_info['rep_proto'] + "://" + task_info['rep_user'] + "@" + task_info['rep_host'] + ":" + task_info['rep_port'] + "/" + task_info['rep_name'] + " rep/" + task_info['project_id']
        print cmd
        status, output = commands.getstatusoutput(cmd)
        #TODO ?? clone and checkout???
        if status:
            return status,project_id
        os.chdir(self.rootpath)
        os.chdir(path)
        cmd = "git checkout " + task_info['release_ver']
        status, output = commands.getstatusoutput(cmd)
        return status, output


    def up_to_version(self, task_info, version):
        if task_info['rep_type1'] == "git":
            return self.git_up_to_version(task_info, version)
        elif task_info['rep_type1'] == 'svn':
            return self.svn_up_to_version(task_info, version)
        else:
            return 'unknown type'

    def rsync(self, exclude_path):
        #rsync -rlt --timeout=300 --exclude='.svn' --exclude='.git' --exclude='.gitignore' --exclude='t.html'  rep/10001/ rpmsrc/10001
        if not os.path.exists('rpmsrc'):
            os.mkdir('rpmsrc')
        exclude_cmd = " --exclude='.git' --exclude='.gitignore' --exclude='.svn'"
        for path in exclude_path:
            exclude_cmd += " --exclude='" + path + "'"
        cmd = "rsync -rlt --timeout=300 " + exclude_cmd + " rep/" + task_info['project_id'] + "/ rpmsrc/" + task_info['project_id']
        #print cmd
        status, output = commands.getstatusoutput(cmd)
        return status, output




if __name__ == "__main__":

    daemon = MiUp('/tmp/miup_py.pid')
    #task data struct
    task_info = {}
    task_info['task_id'] = '10112'
    task_info['rep_host'] = 'b2code.xiaomi.com'
    task_info['rep_port'] = '443'
    task_info['rep_path'] = '/repos/10.xiaomi.com/'
    task_info['rep_user'] = 'wanghaiquan'
    task_info['rep_pass'] = 'haiquan82@186'
    task_info['rep_type1'] = 'svn'
    task_info['rep_proto'] = 'https'
    task_info['project_id'] = '10001'
    task_info['project_name'] = '10.xiaomi.com'
    task_info['rsync_delete'] = '0'
    task_info['release_root'] = '/'
    task_info['release_exclude'] = ['/js/', '/none.txt', '/robots.txt', '/t.html']
    task_info['release_push'] = '0'
    task_info['release_thread'] = '15'
    task_info['release_restart'] = '0'
    task_info['release_rescript'] = ''
    task_info['release_ver'] = '32'
    task_info['current_ver'] = '30'
    task_info['release_server'] = {}
    task_info['release_server']['ip'] = '10.237.93.43'
    task_info['release_server']['port'] = '22'
    task_info['release_server']['path'] = '/data/www/10.xiaomi.com'
    #print task_info
    daemon.queue_id = sys.argv[1]
    daemon.rds.lpush('miup_task_' + daemon.queue_id, task_info)
    
    daemon.run()
    #if len(sys.argv) > 2:
    #    if 'start' == sys.argv[1]:
    #        daemon.start()
    #    elif 'stop' == sys.argv[1]:
    #        daemon.stop()
    #    elif 'restart' == sys.argv[1]:
    #        daemon.restart()
    #    else:
    #        print "Unknown command"
    #        sys.exit(2)
    #    sys.exit(0)
    #else:
    #    print "usage: %s {start|stop|restart}" % sys.argv[0]
    #    sys.exit(2)
