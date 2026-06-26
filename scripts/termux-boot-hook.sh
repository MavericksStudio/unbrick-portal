#!/data/data/com.termux/files/usr/bin/bash
# Install this at ~/.termux/boot/start-portal.sh (chmod +x) on the device.
# Termux:Boot runs it at device boot; it hands off to the supervisor.
exec ~/portal-agent/scripts/supervise.sh >>~/supervise.log 2>&1
