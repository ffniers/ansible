#!/usr/bin/env python3

import subprocess
import re
import platform
import operator
import time

INSTANCES = ['niers', 'mo', 'mg']
SUPERNODES = ['node01', 'node02', 'node03', 'node04', 'node05', 'node08', 'map']
L2TPIDS = ['1', '2', '3', '4', '5', '6', '7']

NODENAME = platform.node()

try:
    SUPERNODES.remove(NODENAME)
except:
    pass

NODES_MIN_THRESHOLD = 10

# These are all helper methods for run_test
def print_status(status_items, message_item):
    for item, status in status_items.items():
        print(message_item.format(item, status2str(status)))


def compare_list(list1, list2):
    status = {}
    for list_item2 in list2:
        if list_item2 not in list1:
            status[list_item2] = False
        else:
            status[list_item2] = True
    return status

def compare_int(int1, relate, int2):
    status = {}
    ops = { '>'  : operator.gt,
            '<'  : operator.lt,
            '>=' : operator.ge,
            '<=' : operator.le,
            '='  : operator.eq }
   
    status[int1] = ops[relate](int1, int2)
        
    return status


def status2str(status):
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'

    if status == True:
        return GREEN + '  OK  ' + ENDC
    else:
        return RED + 'FAILED' + ENDC

# This is the generic test execute method
def run_test(**kwargs):
    _status_test = True
    _status_subtests = {}

    try:
        _output = subprocess.check_output(kwargs.get('command'), shell=True, universal_newlines=True)
        _result = re.findall(kwargs.get('regex'), _output)
    
        if kwargs.get('debug') == True:
            print(_output)
            print(_result)
    
        if kwargs.get('compare') == 'count':
            _status_subtests = compare_int(len(_result), kwargs.get('relate'), kwargs.get('value'))
    
        if kwargs.get('compare') == 'int':
            _status_subtests = compare_int(int(_result[0]), kwargs.get('relate'), kwargs.get('value'))
    
        if kwargs.get('compare') == 'list':
            _status_subtests = compare_list(_result, kwargs.get('value'))
    
    except:
        pass

    for subtest, status in _status_subtests.items():
        if status == False:
            _status_test = False

    print('Testing ' + kwargs.get('test_description') + ':')
    print_status(_status_subtests, '[{1}] ' + kwargs.get('subtest_description'))

#
# TESTS START HERE
#

for instance in INSTANCES:
    print('RUNNING CHECKS FOR INSTANCE: ' + instance);
    print('------------------------------------------------------------')

    run_test(test_description='fastd processes', 
                 subtest_description='{0} fast processes running', 
                 command='ps h -o args -C fastd', 
                 regex='\/usr\/bin\/fastd --syslog-level info --config \/etc\/fastd\/fastd-' + instance + '\/fastd.conf',
                 compare='count', 
                 relate='>=',
                 value=1)

    run_test(test_description='batadv-vis processes', 
                 subtest_description='{0} batadv-vis processes running', 
                 command='ps h -o args -C batadv-vis', 
                 regex='\/usr\/local\/sbin\/batadv-vis -i bat0-' + instance + ' -s /tmp/alfred-' + instance + '.sock',
                 compare='count', 
                 relate='>=',
                 value=1)

    run_test(test_description='alfred processes', 
                 subtest_description='{0} alfred processes running', 
                 command='ps h -o args -C alfred', 
                 regex='\/usr\/local\/sbin\/alfred -i alfred0-' + instance + ' -u \/tmp\/alfred-' + instance + '.sock -b bat0-' + instance,
                 compare='count', 
                 relate='>=',
                 value=1)

    run_test(test_description='supernode connections', 
                 subtest_description='Connection to "{0}"', 
                 command='batctl -m bat0-' + instance + ' gwl -H', 
                 regex='.*\[\s*bb' + instance + '-(.*)\].*', 
                 compare='list', 
                 value=L2TPIDS)

    run_test(test_description='interfaces', 
                 subtest_description='Interface "bb' + instance + '-{0}"', 
                 command='batctl -m bat0-' + instance + ' if', 
                 regex='bb' + instance + '-(.*): active', 
                 compare='list', 
                 value=L2TPIDS)

    run_test(test_description='number of connected nodes', 
                 subtest_description='{0} connected nodes', 
                 command='batctl -m bat0-' + instance + ' o -H', 
                 regex='(.*)\n',
                 compare='count', 
                 relate='>=',
                 value=NODES_MIN_THRESHOLD)

    run_test(test_description='IP rule 10', 
                 subtest_description='{0} rules found', 
                 command='ip rule show', 
                 regex='10:\tfrom all iif br0-' + instance + ' lookup 42',
                 compare='count', 
                 relate='>=',
                 value=1)

    print('============================================================\n')

print('RUNNING GENERIC CHECKS')
print('------------------------------------------------------------')

run_test(test_description='ISC DHCPD processes', 
             subtest_description='{0} dhcpd processes found', 
             command='ps h -o args -C dhcpd', 
             regex='dhcpd -user dhcpd -group dhcpd -f -(4|6) -pf /run/dhcp-server/dhcpd6?.pid -cf /etc/dhcp/dhcpd6?.conf',
             compare='count', 
             relate='=',
             value=2)

run_test(test_description='age of dhcpd.leases file', 
             subtest_description='leases file was last modified within 500 seconds', 
             command='stat -c %Y /var/lib/dhcp/dhcpd.leases', 
             regex='(.*)',
             compare='int', 
             relate='>',
             value=int(time.time() - 500))

run_test(test_description='age of dhcpd6.leases file', 
             subtest_description='leases file was last modified within 500 seconds', 
             command='stat -c %Y /var/lib/dhcp/dhcpd6.leases', 
             regex='(.*)',
             compare='int', 
             relate='>',
             value=int(time.time() - 500))

run_test(test_description='IP rule 10 for traffic from nodes', 
             subtest_description='{0} rules found', 
             command='ip rule show', 
             regex='10:\tfrom 10.0.0.0/8 lookup 42',
             compare='count', 
             relate='>=',
             value=1)

run_test(test_description='IP rule 10 for traffic to nodes', 
             subtest_description='{0} rules found', 
             command='ip rule show', 
             regex='10:\tfrom all to 10.0.0.0/8 lookup 42',
             compare='count', 
             relate='>=',
             value=1)

run_test(test_description='IP rule 10 marked packets', 
             subtest_description='{0} rules found', 
             command='ip rule show', 
             regex='32765:\tfrom all fwmark 0x1 lookup 42',
             compare='count', 
             relate='>=',
             value=1)


run_test(test_description='IPv4 routes in table 42', 
            subtest_description='{0} IPv4 routes found in table 42', 
            command='ip route show table 42', 
            regex='(.*)\n',
            compare='count', 
            relate='>=',
            value=1)

run_test(test_description='IPv6 routes in table 42', 
             subtest_description='{0} IPv6 routes found in table 42', 
             command='ip -6 route show table 42', 
             regex='(.*)\n',
             compare='count', 
             relate='>=',
             value=1)

run_test(test_description='IPv4 default routes', 
             subtest_description='{0} IPv4 default routes found in table 42', 
             command='ip route show table 42', 
             regex='(.*)default via (.+) dev (.+)  proto (\w+)(.*)',
             compare='count', 
             relate='>=',
             value=1)

run_test(test_description='IPv6 default routes', 
             subtest_description='{0} IPv6 default routes found in table 42', 
             command='ip -6 route show table 42', 
             regex='default via (.+) dev (\w+)  proto (\w+)  metric (\d+)',
             compare='count', 
             relate='>=',
             value=1)

run_test(test_description='IPv4 BGP sessions', 
             subtest_description='{0} IPv4 BGP session not up', 
             command='birdc show proto', 
             regex='(\w+)\s+BGP\s+master\s+(?!.*up).*',
             compare='count', 
             relate='=',
             value=0)

run_test(test_description='IPv6 BGP sessions', 
             subtest_description='{0} IPv6 BGP session not up', 
             command='birdc6 show proto', 
             regex='(\w+)\s+BGP\s+master\s+(?!.*up).*',
             compare='count', 
             relate='=',
             value=0)

print('============================================================\n')
