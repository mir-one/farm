## Daemon Not Running

-   Check the Logs: From the `[Gear Icon] -> Farm Logs` page, check the Daemon Log for any errors. If the issue began after an upgrade, also check the Upgrade Log for indications of an issue.
-   Determine if the Daemon is Running: Execute `ps aux | grep '/var/farm-root/env/bin/python /var/farm-root/farm/farm_daemon.py'` in a terminal and look for an entry to be returned. If nothing is returned, the daemon is not running.
-   Daemon Lock File: If the daemon is not running, make sure the daemon lock file is deleted at `/var/lock/farm.pid`. The daemon cannot start if the lock file is present.
-   If a solution could not be found after investigating the above suggestions, submit a [New Farm Issue](https://github.com/mir-one/Farm/issues/new) on github.

## Incorrect Database Version

-   Check the `[Gear Icon] -> System Information` page or select the farm logo in the top-left.
-   An incorrect database version error means the version stored in the Farm settings database (`~/Farm/databases/farm.db`) is not correct for the latest version of Farm, determined in the Farm config file (`~/Farm/farm/config.py`).
-   This can be caused by an error in the upgrade process from an older database version to a newer version, or from a database that did not upgrade during the Farm upgrade process.
-   Check the Upgrade Log for any issues that may have occurred. The log is located at `/var/log/farm/farmupgrade.log` but may also be accessed from the web UI (if you're able to): select `[Gear Icon] -> Farm Logs -> Upgrade Log`.
-   Sometimes issues may not immediately present themselves. It is not uncommon to be experiencing a database issue that was actually introduced several Farm versions ago, before the latest upgrade.
-   Because of the nature of how many versions the database can be in, correcting a database issue may be very difficult. It may be much easier to delete your database and let Farm generate a new one.
-   Use the following commands to rename your database and restart the web UI. If both commands are successful, refresh your web UI page in your browser in order to generate a new database and create a new Admin user.

```bash
mv ~/Farm/databases/farm.db ~/Farm/databases/farm.db.backup
sudo service farmflask restart
```

## More

Check out the [Diagnosing Farm Issues Wiki Page](https://github.com/mir-one/Farm/wiki/Diagnosing-Issues) on github for more information about diagnosing issues.
