#!/bin/bash

set -e

sudo apt-get update

# 安装 pip（如果未安装）
echo "检查 pip 是否已安装..."
if ! command -v pip &> /dev/null then
    echo "pip 未安装。正在安装 pip..."
    sudo apt-get install -y python3-pip
fi

# 安装 autopep8
echo "正在安装 autopep8..."
pip3 install --user autopep8

# 验证安装
if command -v autopep8 &> /dev/null
then
    echo "autopep8 安装成功！"
else
    echo "autopep8 安装失败，请检查错误信息。"
fi
