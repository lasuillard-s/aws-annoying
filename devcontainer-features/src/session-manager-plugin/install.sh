#!/bin/sh

set -o errexit
set -o nounset

ARCH="$(dpkg --print-architecture)"

if ! command -v curl; then
  echo "Installing curl"
  apt update && apt install --yes curl
fi

case $ARCH in
amd64)
  download_url='https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb'
  ;;
arm64)
  download_url='https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_arm64/session-manager-plugin.deb'
  ;;
*)
  echo "Unsupported architecture: $ARCH"
  exit 1
  ;;
esac

echo "Installing plugin from $download_url"

curl --fail --silent --location "$download_url" --output /tmp/session-manager-plugin.deb &&
  dpkg --install /tmp/session-manager-plugin.deb &&
  rm /tmp/session-manager-plugin.deb
