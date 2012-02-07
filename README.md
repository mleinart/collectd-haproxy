collectd-haproxy
================
This is a collectd plugin to pull HAProxy (<http://haproxy.1wt.eu>) stats from the HAProxy management socket.
It is written in Python and as such, runs under the collectd Python plugin.

Requirements
------------

*HAProxy*  
To use this plugin, HAProxy must be configured to create a management socket with the `stats socket`
configuration option. collectd must have read/write access to the socket.

*collectd*  
collectd must have the Python plugin installed. See (<http://collectd.org/documentation/manpages/collectd-python.5.shtml>)

Options
-------
* `ProxyMonitor`  
Proxy to monitor. If unset, defaults to ['server', 'frontend', 'backend'].
Specify multiple times to specify additional proxies
* `ProxyIgnore`  
One or more Proxies to ignore
 Specify multiple times to specify additional proxies
* `Socket`  
File location of the HAProxy management socket
* `Verbose`  
Enable verbose logging

Example
-------
    <LoadPlugin python>
        Globals true
    </LoadPlugin>

    <Plugin python>
        # haproxy.py is at /usr/lib64/collectd/haproxy.py
        ModulePath "/usr/lib64/collectd/"

        Import "haproxy"

        <Module haproxy>
          Socket "/var/run/haproxy.sock"
          ProxyMonitor "server"
          ProxyMonitor "backend"
        </Module>
    </Plugin>
