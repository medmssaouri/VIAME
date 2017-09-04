# kwiver External Project
#
# Required symbols are:
#   VIAME_BUILD_PREFIX - where packages are built
#   VIAME_BUILD_INSTALL_PREFIX - directory install target
#   VIAME_PACKAGES_DIR - location of git submodule packages
#   VIAME_ARGS_COMMON -
##

set( VIAME_PROJECT_LIST ${VIAME_PROJECT_LIST} kwiver )

set( VIAME_KWIVER_DEPS fletch )

if( VIAME_ENABLE_MATLAB )
  FormatPassdowns( "Matlab" VIAME_MATLAB_FLAGS )
endif()

if( VIAME_ENABLE_PYTHON )
  FormatPassdowns( "PYTHON" VIAME_PYTHON_FLAGS )
endif()

if( VIAME_ENABLE_CUDA )
  FormatPassdowns( "CUDA" VIAME_CUDA_FLAGS )
endif()

if( VIAME_ENABLE_CUDNN )
  FormatPassdowns( "CUDNN" VIAME_CUDNN_FLAGS )
endif()

if( VIAME_ENABLE_CUDNN )
  FormatPassdowns( "DOXYGEN" VIAME_DOXYGEN_FLAGS )
endif()

if( VIAME_ENABLE_YOLO )
  set( VIAME_KWIVER_DEPS ${VIAME_KWIVER_DEPS} darknet )
endif()

if( VIAME_ENABLE_BURNOUT )
  set( VIAME_KWIVER_DEPS ${VIAME_KWIVER_DEPS} burnout )
endif()

ExternalProject_Add(kwiver
  DEPENDS ${VIAME_KWIVER_DEPS}
  PREFIX ${VIAME_BUILD_PREFIX}
  SOURCE_DIR ${VIAME_PACKAGES_DIR}/kwiver
  CMAKE_GENERATOR ${gen}
  CMAKE_CACHE_ARGS
    ${VIAME_ARGS_COMMON}
    ${VIAME_ARGS_Boost}
    ${VIAME_ARGS_fletch}
    ${VIAME_ARGS_VXL}
    ${VIAME_ARGS_darknet}
    ${VIAME_ARGS_burnout}
    ${VIAME_ARGS_PROJ4}
    ${VIAME_MATLAB_FLAGS}
    ${VIAME_PYTHON_FLAGS}
    ${VIAME_CUDA_FLAGS}
    ${VIAME_CUDNN_FLAGS}
    ${VIAME_DOXYGEN_FLAGS}

    # Required
    -DBUILD_SHARED_LIBS:BOOL=ON
    -DKWIVER_ENABLE_ARROWS:BOOL=ON
    -DKWIVER_ENABLE_TOOLS:BOOL=ON
    -DKWIVER_ENABLE_SPROKIT:BOOL=ON
    -DKWIVER_ENABLE_PROCESSES:BOOL=ON
    -DKWIVER_INSTALL_SET_UP_SCRIPT:BOOL=OFF

    # Optional
    -DKWIVER_ENABLE_UUID:BOOL=OFF
    -DKWIVER_ENABLE_PROJ4:BOOL=OFF
    -DKWIVER_ENABLE_BURNOUT:BOOL=${VIAME_ENABLE_BURNOUT}
    -DKWIVER_ENABLE_OPENCV:BOOL=${VIAME_ENABLE_OPENCV}
    -DKWIVER_ENABLE_VXL:BOOL=${VIAME_ENABLE_VXL}
    -DKWIVER_ENABLE_MATLAB:BOOL=${VIAME_ENABLE_MATLAB}
    -DKWIVER_ENABLE_DARKNET:BOOL=${VIAME_ENABLE_YOLO}
    -DKWIVER_ENABLE_C_BINDINGS:BOOL=${VIAME_ENABLE_PYTHON}
    -DKWIVER_ENABLE_PYTHON:BOOL=${VIAME_ENABLE_PYTHON}
    -DKWIVER_SYMLINK_PYTHON:BOOL=${VIAME_SYMLINK_PYTHON}
    -DKWIVER_ENABLE_CUDA:BOOL=${VIAME_ENABLE_CUDA}
    -DKWIVER_ENABLE_DOCS:BOOL=${VIAME_ENABLE_DOCS}
    -DENABLE_TESTING:BOOL=${VIAME_BUILD_TESTS}
    -DKWIVER_ENABLE_TESTS:BOOL=${VIAME_BUILD_TESTS}
    -DKWIVER_SYMLINK_PYTHON:BOOL=${VIAME_SYMLINK_PYTHON}
    -DKWIVER_INSTALL_DOCS:BOOL=${VIAME_ENABLE_DOCS}
    -DKWIVER_ENABLE_TRACK_ORACLE:BOOL=${VIAME_ENABLE_KWANT}
    -D KWIVER_ENABLE_TESTS:BOOL=On

  INSTALL_DIR ${VIAME_BUILD_INSTALL_PREFIX}
  )


# Why must we force kwiver to build on every make?
ExternalProject_Add_Step(kwiver forcebuild
  COMMAND ${CMAKE_COMMAND}
    -E remove ${VIAME_BUILD_PREFIX}/src/kwiver-stamp/kwiver-build
  COMMENT "Removing build stamp file for build update (forcebuild)."
  DEPENDEES configure
  DEPENDERS build
  ALWAYS 1
  )

set(VIAME_ARGS_kwiver
  -Dkwiver_DIR:PATH=${VIAME_BUILD_PREFIX}/src/kwiver-build
  )
