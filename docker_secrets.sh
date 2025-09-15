#!/bin/sh

set -e

mkdir -p ./secrets

while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  case "$key" in
    \#*) continue ;;
  esac
  value=$(echo "$value" | tr -d '\r' | sed 's/^"\(.*\)"$/\1/')
  echo -n "$value" > "./secrets/$(echo "$key" | tr '[:upper:]' '[:lower:]')"
done < .env

echo "Docker secrets created."