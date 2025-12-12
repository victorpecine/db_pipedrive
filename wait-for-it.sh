#!/usr/bin/env bash
# wait-for-it.sh
# Uso: ./wait-for-it.sh host:port [-t timeout]

set -e

hostport="$1"
shift
timeout=30

if [ "$1" = "-t" ]; then
  timeout="$2"
  shift 2
fi

host=$(echo $hostport | cut -d: -f1)
port=$(echo $hostport | cut -d: -f2)

echo "Waiting for $host:$port..."

for i in $(seq $timeout); do
  nc -z $host $port && echo "$host:$port is available" && exit 0
  sleep 1
done

echo "Timeout reached: $host:$port not available"
exit 1
