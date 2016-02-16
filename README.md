# python_clang_parser
Python application with Clang python wrapper to parse static code c++

## Feature
- Analyse static c++ code only with source file and emplacement of header file.
- Create csv with statistic analyse
- Parallelism execution

## Dependency
python2
libclang, the Clang python binding

### Ubuntu
This dependence is to generate the UML
```{r, engine='bash', count_lines}
sudo apt-get install python-pip
sudo python-pip install graphviz
```

## Clang
I choose to compile the code source of Clang, because you can choose the version you need.
I tested this code with branch release_37

https://github.com/llvm-mirror/clang

This is a good guide for installation : http://clang.llvm.org/get_started.html

Personally, I install it in /opt on Linux

## HOW TO
I test this code with OpenCV project : https://github.com/Itseez/opencv
In this example, we assume you clone in your home directory. "~/" is not supported :-(

```{r, engine='bash', count_lines}
ROOT_DIRECTORY=/home/user/opencv
python2 main.py --root_directory ${ROOT_DIRECTORY} -d -I "build" --find_include
```

For more information
```{r, engine='bash', count_lines}
python2 main.py -h
```

## Why not python3?
Officially, libClang is only supported in python2.

## License
Project under MIT

## Contributors
1. Mathieu Benoit - mathben
