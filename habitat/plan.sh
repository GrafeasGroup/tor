pkg_name=tor
pkg_origin=thelonelyghost
pkg_version="3.7.0"
pkg_maintainer="David Alexander <opensource@thelonelyghost.com>"
pkg_license=("MIT")

python_major_version="3.7"
python_minor_version="0"

pkg_lib_dirs=(lib)
pkg_bin_dirs=(bin)
pkg_build_deps=(
  core/inetutils
  core/git
  core/gcc
  core/libffi
  "core/python/${python_major_version}.${python_minor_version}"
)
pkg_deps=(
  core/coreutils
)


do_before() {
  update_pkg_version
}

do_setup_environment() {
  HAB_ENV_LD_LIBRARY_PATH_TYPE="aggregate"
  push_runtime_env   'PYTHONPATH'      "${pkg_prefix}/lib/python${python_major_version}/site-packages"
  push_buildtime_env 'LD_LIBRARY_PATH' "$(pkg_path_for core/gcc)/lib"
  push_buildtime_env 'LD_LIBRARY_PATH' "$(pkg_path_for core/libffi)/lib"
  # push_buildtime_env 'LD_LIBRARY_PATH' "$(pkg_path_for core/pcre)/lib"
  return $?
}

do_prepare() {
  python -m venv "${pkg_prefix}"
  source "${pkg_prefix}/bin/activate"
  return $?
}

do_build() {
  return 0
}

do_install() {
  pushd /src 1>/dev/null

  pip install --quiet --no-cache-dir -r requirements.txt
  export module_version="$(python -c "import ${pkg_name}; print(${pkg_name}.__version__)")"
  build_line "${pkg_name} version: ${module_version}"

  popd 1>/dev/null
}

do_strip() {
  # for module in $(pip freeze | grep -v "${pkg_name}==${pkg_version}" | grep -v 'tor-core'); do
  #   pip uninstall --yes "$module"
  # done

  rm -rf "${pkg_prefix}/lib/python${python_major_version}"/site-packages/pip*
  rm -rf "${pkg_prefix}/lib64/python${python_major_version}"/site-packages/pip*
  rm -rf "${pkg_prefix}/lib/python${python_major_version}"/site-packages/setuptools*
  rm -rf "${pkg_prefix}/lib64/python${python_major_version}"/site-packages/setuptools*
  rm -rf "${pkg_prefix}/bin"/pip*
  rm -rf "${pkg_prefix}/bin"/easy_install*
  return $?
}

do_end() {
  export pkg_origin
  export pkg_name
  export pkg_version
  export pkg_release
}

# Uncomment these lines if you want to setup build hook notifications:
# do_after_success() {
#   $PLAN_CONTEXT/../../functions/notify_build_completed.sh
#   return $?
# }
# do_after_failure() {
#   $PLAN_CONTEXT/../../functions/notify_build_failed.sh
#   return $?
# }


# Opting out of all of these since the source code is in the same repo
do_download() {
  return 0
}
do_verify() {
  return 0
}
do_clean() {
  rm -rf "${pkg_prefix}"/*
  return 0
}

# do_unpack() {
#   # Because our habitat files live under `<project-root>/habitat/`
#   PROJECT_ROOT="${PLAN_CONTEXT}/.."
# 
#   mkdir -p "$pkg_prefix"
#   build_line "Copying project data to $pkg_prefix/"
# 
#   cp "$PROJECT_ROOT/setup.py" "$pkg_prefix/setup.py"
#   cp "$PROJECT_ROOT/commands.json" "$pkg_prefix/commands.json"
#   cp "$PROJECT_ROOT/requirements.txt" "$pkg_prefix/requirements.txt"
#   cp -r "$PROJECT_ROOT/tor" "$pkg_prefix/tor"
# }

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


# vim: ft=bash.sh
