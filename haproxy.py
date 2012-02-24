# haproxy-collectd-plugin - haproxy.py
#
# Author: Michael Leinartas
# Description: This is a collectd plugin which runs under the Python plugin to
# collect metrics from haproxy.
# Plugin structure and logging func taken from https://github.com/phrawzty/rabbitmq-collectd-plugin

import collectd
import socket
import csv

NAME = 'haproxy'
RECV_SIZE = 1024
METRIC_TYPES = {
  'bin': ('bytes_in', 'derive'),
  'bout': ('bytes_out', 'derive'),
  'chkfail': ('failed_checks', 'counter'),
  'CurrConns': ('connections', 'gauge'),
  'downtime': ('downtime', 'counter'),
  'dresp': ('denied_response', 'derive'),
  'dreq': ('denied_request', 'derive'),
  'econ': ('error_connection', 'derive'),
  'ereq': ('error_request', 'derive'),
  'eresp': ('error_response', 'derive'),
  'hrsp_1xx': ('response_1xx', 'derive'),
  'hrsp_2xx': ('response_2xx', 'derive'),
  'hrsp_3xx': ('response_3xx', 'derive'),
  'hrsp_4xx': ('response_4xx', 'derive'),
  'hrsp_5xx': ('response_5xx', 'derive'),
  'hrsp_other': ('response_other', 'derive'),
  'PipesUsed': ('pipes_used', 'gauge'),
  'PipesFree': ('pipes_free', 'gauge'),
  'qcur': ('queue_current', 'gauge'),
  'Tasks': ('tasks', 'gauge'),
  'Run_queue': ('run_queue', 'gauge'),
  'rate': ('session_rate', 'gauge'),
  'req_rate': ('request_rate', 'gauge'),
  'stot': ('session_total', 'counter'),
  'scur': ('session_current', 'gauge'),
  'wredis': ('redistributed', 'derive'),
  'wretr': ('retries', 'counter'),
  'Uptime_sec': ('uptime_seconds', 'counter')
}

METRIC_DELIM = '.' # for the frontend/backend stats

DEFAULT_SOCKET = '/var/lib/haproxy/stats'
DEFAULT_PROXY_MONITORS = [ 'server', 'frontend', 'backend' ]
VERBOSE_LOGGING = False

class HAProxySocket(object):
  def __init__(self, socket_file=DEFAULT_SOCKET):
    self.socket_file = socket_file

  def connect(self):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(self.socket_file)
    return s

  def communicate(self, command):
    ''' Send a single command to the socket and return a single response (raw string) '''
    s = self.connect()
    if not command.endswith('\n'): command += '\n'
    s.send(command)
    result = ''
    buf = ''
    buf = s.recv(RECV_SIZE)
    while buf:
      result += buf
      buf = s.recv(RECV_SIZE)
    s.close()
    return result

  def get_server_info(self):
    result = {}
    output = self.communicate('show info')
    for line in output.splitlines():
      try:
        key,val = line.split(':')
      except ValueError, e:
        continue
      result[key.strip()] = val.strip()
    return result

  def get_server_stats(self):
    output = self.communicate('show stat')
    #sanitize and make a list of lines
    output = output.lstrip('# ').strip()
    output = [ l.strip(',') for l in output.splitlines() ]
    csvreader = csv.DictReader(output)
    result = [ d.copy() for d in csvreader ]
    return result

def get_stats():
  stats = dict()
  haproxy = HAProxySocket(HAPROXY_SOCKET)

  try:
    server_info = haproxy.get_server_info()
    server_stats = haproxy.get_server_stats()
  except socket.error, e:
    logger('warn', "status err Unable to connect to HAProxy socket at %s" % HAPROXY_SOCKET)
    return stats

  if 'server' in PROXY_MONITORS:
    for key,val in server_info.items():
      try:
        stats[key] = int(val)
      except (TypeError, ValueError), e:
        pass

  for statdict in server_stats:
    if not (statdict['svname'].lower() in PROXY_MONITORS or statdict['pxname'].lower() in PROXY_MONITORS):
      continue
    if statdict['pxname'] in PROXY_IGNORE:
      continue
    for key,val in statdict.items():
      metricname = METRIC_DELIM.join([ statdict['svname'].lower(), statdict['pxname'].lower(), key ])
      try:
        stats[metricname] = int(val)
      except (TypeError, ValueError), e:
        pass
  return stats

def configure_callback(conf):
  global PROXY_MONITORS, PROXY_IGNORE, HAPROXY_SOCKET, VERBOSE_LOGGING
  PROXY_MONITORS = [ ]
  PROXY_IGNORE = [ ]
  HAPROXY_SOCKET = DEFAULT_SOCKET
  VERBOSE_LOGGING = False

  for node in conf.children:
    if node.key == "ProxyMonitor":
      PROXY_MONITORS.append(node.values[0])
    elif node.key == "ProxyIgnore":
      PROXY_IGNORE.append(node.values[0])
    elif node.key == "Socket":
      HAPROXY_SOCKET = node.values[0]
    elif node.key == "Verbose":
      VERBOSE_LOGGING = bool(node.values[0])
    else:
      logger('warn', 'Unknown config key: %s' % node.key)

  if not PROXY_MONITORS:
    PROXY_MONITORS += DEFAULT_PROXY_MONITORS
  PROXY_MONITORS = [ p.lower() for p in PROXY_MONITORS ]

def read_callback():
  logger('verb', "beginning read_callback")
  info = get_stats()

  if not info:
    logger('warn', "%s: No data received" % NAME)
    return

  for key,value in info.items():
    key_prefix = ''
    key_root = key
    if not value in METRIC_TYPES:
      try:
        key_prefix, key_root = key.rsplit(METRIC_DELIM,1)
      except ValueError, e:
        pass
    if not key_root in METRIC_TYPES:
      continue

    key_root, val_type = METRIC_TYPES[key_root]
    key_name = METRIC_DELIM.join([key_prefix, key_root])
    val = collectd.Values(plugin=NAME, type=val_type)
    val.type_instance = key_name
    val.values = [ value ]
    val.dispatch()

def logger(t, msg):
    if t == 'err':
        collectd.error('%s: %s' % (NAME, msg))
    elif t == 'warn':
        collectd.warning('%s: %s' % (NAME, msg))
    elif t == 'verb':
        if VERBOSE_LOGGING:
            collectd.info('%s: %s' % (NAME, msg))
    else:
        collectd.notice('%s: %s' % (NAME, msg))

collectd.register_config(configure_callback)
collectd.register_read(read_callback)
