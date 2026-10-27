# ns8-launcher

A home page for a [NethServer 8](https://github.com/NethServer/ns8-core) cluster.
It lists every application published with a host name on any node, with its
name and logo, plus external links and support contacts.

The page works in two modes:

- `public`: no login, every application is visible.
- `ldap`: users of a user domain log in first. Each application can be
  restricted to some LDAP groups; an application with no group is visible to
  every logged in user. Anonymous visitors see only the login form.

The page is always served over HTTPS. Let's Encrypt is optional. Clone, move and
restore turn it off, because the new host may not reach the Internet: enable it
again from the Settings page.

## Install

    add-module ghcr.io/stephdl/launcher:latest 1

The output returns the instance name, like `launcher1`.

## Configure

    api-cli run configure-module --agent module/launcher1 --data - <<EOF
    {
      "host": "home.example.org",
      "lets_encrypt": true,
      "auth_mode": "ldap",
      "ldap_domain": "example.org"
    }
    EOF

`auth_mode` is `public` or `ldap`. `ldap_domain` is required in `ldap` mode.

The page content is set with `set-settings` and read with `get-settings`:
welcome sentence, logo (base64 PNG or JPEG, 512 KB at most), support contacts,
categories, external links, and per-application overrides (hidden, name,
category, groups). The NS8 admin UI of the module covers all of it.

## How the application list is built

`bin/refresh-apps` calls `list-routes` on every Traefik instance of the
cluster and keeps the routes that have a host name. The display name comes
from the instance label, then from the repository metadata; the logo from the
repository metadata, cached locally. The result is `state/launcher/apps.json`.

The list is refreshed:

- on `hosts-changed`, fired by Traefik when the host names of its routes change;
- on `module-removed`, because Traefik drops the routes of a removed module
  without firing `hosts-changed`. The overrides of the removed apps are deleted;
- every hour, to catch events missed while the module was stopped;
- on demand, with the `refresh-apps` action (the Refresh button of the Apps page).

The module needs `traefik@any:routeadm` to read the routes of every node, and
`cluster:reader` to read the repository metadata.

## Logs and CrowdSec

The web server logs each request to the journal with the client address and
the status code, like `192.0.2.10 "POST /api/login" 401 18ms`. A failed login
also logs `login failed user='alice' ip=192.0.2.10`.

Status codes are exact: 401 for a failed login or a missing session, 429 when
an address made 10 failed logins in 15 minutes, 404 for unknown paths.
Traefik logs the same requests, so the CrowdSec `http-generic-401-bf` scenario
bans an address after 5 failed logins in a row.

## Uninstall

    remove-module --no-preserve launcher1

## Debug

    runagent -m launcher1 env
    runagent -m launcher1 systemctl --user status launcher.service launcher-refresh.timer
    journalctl -t launcher -t launcher-refresh
    runagent -m launcher1 cat launcher/apps.json

## Testing

Test the module using the `test-module.sh` script:

    ./test-module.sh <NODE_ADDR> ghcr.io/stephdl/launcher:latest

The tests are made using [Robot Framework](https://robotframework.org/).
Cases tagged `ui` take screenshots of the admin pages and of the launcher page.

## UI translation

Translated with [Weblate](https://hosted.weblate.org/projects/ns8/).
