#!/bin/bash

#
# Copyright (C) 2023 Nethesis S.r.l. (ns8-kickstart template)
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Terminate on error
set -e

# Prepare variables for later use
images=()
# The image will be pushed to GitHub container registry
repobase="${REPOBASE:-ghcr.io/nethserver}"
# Configure the image name
reponame="dnsapi"
# Node.js 25+ no longer ships Corepack, install it from npm
# renovate: datasource=npm packageName=corepack
corepack_version=0.36.0

# Create a new empty container image
container=$(buildah from scratch)

# Reuse existing nodebuilder-dnsapi container, to speed up builds
if ! buildah containers --format "{{.ContainerName}}" | grep -q nodebuilder-dnsapi; then
    echo "Pulling NodeJS runtime..."
    buildah from --name nodebuilder-dnsapi -v "${PWD}:/usr/src:Z" docker.io/library/node:26.13.1-slim
    buildah run nodebuilder-dnsapi sh -c "npm install -g corepack@${corepack_version} && corepack enable"
fi

echo "Build static UI files with node..."
buildah run \
    --workingdir=/usr/src/ui \
    --env="NODE_OPTIONS=--openssl-legacy-provider" \
    nodebuilder-dnsapi \
    sh -c "yarn install && yarn build"

# Add imageroot directory to the container image
buildah add "${container}" imageroot /imageroot
buildah add "${container}" ui/dist /ui

# The API service image (server/Containerfile). It is published beside the
# module image under the same tag, so a branch build runs its own service.
imagetag=$(printf '%s' "${IMAGETAG:-latest}" | tr '/' '-')
serverimage="${repobase}/${reponame}-server"
buildah build --tag "${serverimage}" -f server/Containerfile server
images+=("${serverimage}")

# Run the service's unit tests inside the image just built. --pull=never:
# test this build, not an image of the same name pulled from the registry.
echo "Running the server unit tests..."
testcontainer=$(buildah from --pull=never "${serverimage}")
buildah copy "${testcontainer}" server/tests /tmp/tests
buildah run --workingdir=/tmp/tests "${testcontainer}" -- python3 -m unittest discover
buildah rm "${testcontainer}" >/dev/null

# Setup the entrypoint, ask to reserve one TCP port with the label and set a rootless container
buildah config --entrypoint=/ \
    --label="org.nethserver.authorizations=dnshelper@any:dnswriter traefik@node:routeadm node:reader" \
    --label="org.nethserver.tcp-ports-demand=1" \
    --label="org.nethserver.rootfull=0" \
    --label="org.nethserver.min-core=3.23.0" \
    --label="org.nethserver.images=${serverimage}:${imagetag}" \
    "${container}"
# Commit the image
buildah commit "${container}" "${repobase}/${reponame}"

# Append the image URL to the images array
images+=("${repobase}/${reponame}")

#
# NOTICE:
#
# It is possible to build and publish multiple images.
#
# 1. create another buildah container
# 2. add things to it and commit it
# 3. append the image url to the images array
#

#
# Setup CI when pushing to Github. 
# Warning! docker::// protocol expects lowercase letters (,,)
if [[ -n "${CI}" ]]; then
    # Set output value for Github Actions
    printf "images=%s\n" "${images[*],,}" >> "${GITHUB_OUTPUT}"
else
    # Just print info for manual push
    printf "Publish the images with:\n\n"
    for image in "${images[@],,}"; do printf "  buildah push %s docker://%s:%s\n" "${image}" "${image}" "${IMAGETAG:-latest}" ; done
    printf "\n"
fi
