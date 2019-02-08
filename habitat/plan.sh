#!/usr/bin/env bash

pkg_name=tor_moderator
pkg_origin=thelonelyghost
pkg_version="3.0.1"
pkg_maintainer="David Alexander <opensource@thelonelyghost.com>"
pkg_license=("MIT")
pkg_source="fake"
pkg_build_deps=(core/git)
pkg_deps=(core/coreutils core/python)


# Opting out of all of these since the source code is in the same repo
do_download() {
  return 0
}
do_verify() {
  return 0
}
do_clean() {
  return 0
}

do_unpack() {
  # Because our habitat files live under `<project-root>/habitat/`
  PROJECT_ROOT="${PLAN_CONTEXT}/.."

  mkdir -p "$pkg_prefix"
  build_line "Copying project data to $pkg_prefix/"

  cp "$PROJECT_ROOT/setup.py" "$pkg_prefix/setup.py"
  cp -r "$PROJECT_ROOT/tor" "$pkg_prefix/tor"
}

do_build() {
  return 0
}

do_install() {
  cd "$pkg_prefix"
  pip install --process-dependency-links .
}


# pkg_filename="${pkg_name}-${pkg_version}.tar.gz"
# pkg_shasum="TODO"
# pkg_deps=(core/glibc)
# pkg_lib_dirs=(lib)
# pkg_include_dirs=(include)
# pkg_bin_dirs=(bin)
# pkg_pconfig_dirs=(lib/pconfig)
# pkg_svc_run="haproxy -f $pkg_svc_config_path/haproxy.conf"
# pkg_exports=(
#   [host]=srv.address
#   [port]=srv.port
#   [ssl-port]=srv.ssl.port
# )
# pkg_exposes=(port ssl-port)
# pkg_binds=(
#   [database]="port host"
# )
# pkg_binds_optional=(
#   [storage]="port host"
# )
# pkg_interpreters=(bin/bash)
# pkg_svc_user="hab"
# pkg_svc_group="$pkg_svc_user"
# pkg_description="Some description."
# pkg_upstream_url="http://example.com/project-name"

