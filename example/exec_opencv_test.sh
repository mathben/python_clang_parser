#!/usr/bin/env bash

TEMP_DIR="./build"
OPENCV_PATH="${TEMP_DIR}/opencv"
OPENCV_GIT_REPO="https://github.com/Itseez/opencv.git"
AST_GENERATED_PATH="${TEMP_DIR}/generated_AST/AST_OpenCV"
CSV_RESULT_STAT_PATH="${TEMP_DIR}/opencv_stat.csv"

# TODO need to understand why this file not work in the parser
EXCLUDE_PATH="samples/gpu/performance;samples/gpu/super_resolution.cpp;modules/core/test/test_mat.cpp;modules/core/test/test_ds.cpp;modules/core/test/test_operations.cpp;modules/imgcodecs/src/jpeg_exif.cpp;modules/calib3d/src/calibinit.cpp;modules/ts/src/ts_gtest.cpp;modules/ts/src/ts_perf.cpp"

function clone_OpenCV {
    if [ ! -d "${OPENCV_PATH}" ]; then
        echo "Clone OpenCV repo into : ${OPENCV_PATH}"
        # clone repository, only keep 1 history and update all submodules
        git clone --recurse-submodules --depth 1 ${OPENCV_GIT_REPO} ${OPENCV_PATH}
    fi
}

function generate_stat {
    python2 ./main.py --root_directory ${OPENCV_PATH} --find_include --translation_unit_dir ${AST_GENERATED_PATH} --csv ${CSV_RESULT_STAT_PATH} --generate_csv_stat $@
#    echo "python2 ./main.py --root_directory ${OPENCV_PATH} --find_include --translation_unit_dir ${AST_GENERATED_PATH} --csv ${CSV_RESULT_STAT_PATH} --generate_csv_stat $@"
}

function erase_AST_generated {
    rm -fr ${AST_GENERATED_PATH}
}

# Step init, clone OpenCV if not exist
clone_OpenCV

echo "Step 1, Create statistic"

echo "1.1 - Test mono cpu without AST generated"
erase_AST_generated
generate_stat --disable_threading --show_metric_time --quiet --exclude_path ${EXCLUDE_PATH}

echo "1.2 - Test parallelism cpu without AST generated"
erase_AST_generated
generate_stat --show_metric_time --quiet --exclude_path ${EXCLUDE_PATH}

echo "1.3 - Test parallelism cpu with AST generated"
generate_stat --show_metric_time --quiet --exclude_path ${EXCLUDE_PATH}
