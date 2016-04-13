#!/usr/bin/env bash

TEMP_DIR="./build"
OPENCV_PATH="${TEMP_DIR}/opencv"
OPENCV_GIT_REPO="https://github.com/Itseez/opencv.git"
AST_GENERATED_PATH="${TEMP_DIR}/generated_AST/AST_OpenCV"
CSV_RESULT_STAT_PATH="${TEMP_DIR}/opencv_stat.csv"

UML_SMALL_PROJECT_PATH="apps/traincascade"
# TODO need to understand why this file not work in the parser
EXCLUDE_PATH="samples/gpu/performance;samples/gpu/super_resolution.cpp;modules/core/test/test_mat.cpp;modules/core/test/test_ds.cpp;modules/core/test/test_operations.cpp;modules/imgcodecs/src/jpeg_exif.cpp;modules/calib3d/src/calibinit.cpp;modules/ts/src/ts_gtest.cpp;modules/ts/src/ts_perf.cpp"

GENERIC_CMD="python2 ./main.py --root_directory ${OPENCV_PATH} --translation_unit_dir ${AST_GENERATED_PATH} --exclude_path ${EXCLUDE_PATH} --show_metric_time --quiet --graph_path ${TEMP_DIR}"

function clone_OpenCV {
    if [ ! -d "${OPENCV_PATH}" ]; then
        echo "Clone OpenCV repo into : ${OPENCV_PATH}"
        # clone repository, only keep 1 history and update all submodules
        git clone --recurse-submodules --depth 1 ${OPENCV_GIT_REPO} ${OPENCV_PATH}
    fi
}

function generate_stat {
    ${GENERIC_CMD} --csv ${CSV_RESULT_STAT_PATH} --generate_csv_stat $@
}

function generate_UML {
#    echo "${GENERIC_CMD} --generate_uml $@"
    ${GENERIC_CMD} --generate_uml $@
}

function erase_AST_generated {
    rm -fr ${AST_GENERATED_PATH}
}

# Step init, clone OpenCV if not exist
clone_OpenCV

echo "Step 1, Create statistic"

echo "1.1 - Test mono cpu without AST generated"
erase_AST_generated
generate_stat --disable_threading

echo "1.2 - Test parallelism cpu without AST generated"
erase_AST_generated
generate_stat

echo "1.3 - Test parallelism cpu with AST generated"
generate_stat

echo "You can now open csv file ${CSV_RESULT_STAT_PATH}"

echo "Step 2, Generate UML"
echo "2.1 - Generate UML of a small directory."
generate_UML --working_path ${UML_SMALL_PROJECT_PATH}

echo "You can now open UML file build/traincascade.dot_dot.svgz"