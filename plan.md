Python

Configurable options within home assistant intigations (command line switchs)
Outputs to JSON

We will want to let the user know they must be using the latest WWIVD which supports enhanced status endpoints, they must also be enabled.

### WWIVD Options (Common normal WWIVD) 
* HOST:PORT
* Refresh Interval [Default 30s]
* Enable/Disable Endpoints
    * /instances - Enhanced Node Status [Default:Enable]
        * Sensors: used_instances
    * /blocking - IP whitelist/blacklist management [Default:Enable]
        * Sensors: auto_blocked_count
    * /sysop - Sysop and System status [Default:Enable]
        * Sensors: calls_today, email_today, feedback_today, feedback_waiting
    * /laston - Last users who logged on [Default:Enable]
* Live endpoint data for structure can be found at 10.0.2.134:8080





###  Modem Manager (StarDoc 134 Only, not likely to be useful for other people) [Default:Disabled]
* HOST:PORT
* Refresh Interval [Default 30s]
* /modem_status - Status of all modems
* Live endpoint data for structure can be found at 10.0.2.227:8080
