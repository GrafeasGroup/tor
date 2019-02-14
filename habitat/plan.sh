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

  # Add all of the python deps we install to the PYTHONPATH
  # so we can `import` them at runtime. With Habitat we need
  # to specify the PYTHONPATH since it doesn't do that for us
  push_runtime_env   'PYTHONPATH'      "${pkg_prefix}/lib/python${python_major_version}/site-packages"

  # Some magic compile-time stuff to make sure GCC and FFI
  # are auto-discovered when python native deps need them
  push_buildtime_env 'LD_LIBRARY_PATH' "$(pkg_path_for core/gcc)/lib"
  push_buildtime_env 'LD_LIBRARY_PATH' "$(pkg_path_for core/libffi)/lib"
  # push_buildtime_env 'LD_LIBRARY_PATH' "$(pkg_path_for core/pcre)/lib"

  return $?
}

do_prepare() {
  # Virtualenv (venv) is a nicer way of redirecting where python
  # packages are installed. It works for Habitat especially since
  # there is no real "global" installation of python. This also
  # makes it much more self-contained by including the version of
  # python in the `bin/` directory we generate for this package.
  #
  # Additionally, virtualenv rewrites the shebangs at the top of
  # the executables for those installed packages to use the python
  # executable in the virtualenv, so no funky patching needs to
  # occur for this to work with Habitat.
  python -m venv "${pkg_prefix}"
  . "${pkg_prefix}/bin/activate"
  return $?
}

do_build() {
  return 0
}

do_install() {
  pushd /src 1>/dev/null

  # This is the install step
  pip install --quiet --no-cache-dir -r requirements.txt

  # Dynamically fetch the version
  module_version="$(python -c "import ${pkg_name}; print(${pkg_name}.__version__)")"
  export module_version
  build_line "${pkg_name} version: ${module_version}"

  popd 1>/dev/null
}

do_strip() {
  # We don't need `pip`, `setuptools`, or `easy_install` after the package is installed
  rm -rf "${pkg_prefix}/lib/python${python_major_version}"/site-packages/pip*
  rm -rf "${pkg_prefix}/lib64/python${python_major_version}"/site-packages/pip*
  rm -rf "${pkg_prefix}/lib/python${python_major_version}"/site-packages/setuptools*
  rm -rf "${pkg_prefix}/lib64/python${python_major_version}"/site-packages/setuptools*
  rm -rf "${pkg_prefix}/bin"/pip*
  rm -rf "${pkg_prefix}/bin"/easy_install*

  # Any other trimming down steps between installation and runtime can happen here.
  return $?
}

do_clean() {
  # This trigger is invoked if we're in the Habitat Studio and need
  # to cleanup between attempted builds. This makes sure one build
  # attempt does not taint the next one by cleaning up all of the
  # prior build attempt remnants. The best way to do that is still
  # the scorched earth approach and starting fresh, but for doing
  # "dirty upgrades" where it's not a clean environment, we can
  # optimize by only removing the stuff we _think_ would poison
  # things for the next build and otherwise reuse the cache for,
  # e.g., dependencies that have not changed between builds.
  
  # That said, we keep things pretty sandboxed in the `$pkg_prefix`,
  # thanks to virtualenv, but if there are additional remnants from
  # the prior build, here is where we'd clean them up.
  rm -rf "${pkg_prefix:?}"/*
  return 0
}

do_end() {
  # since we're dynamically setting these in the build, let's export
  # them so Habitat can write the artifact information out nicely
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

# vim: ft=bash syn=sh
