# -*- encoding: utf-8 -*-

import os
import sys
import subprocess
import json
import re
from pygments import highlight
from pygments.lexers import JavaLaxer
from pygments.formatters import RawTokenFormatter


def get_file_contents_by_hash(hash_code):
    """ 根据提供的hash短码使用'git cat-file -p'命令从repo中获取完整文件.

    Arguments:
        hash_code {str} -- hash短码

    Returns:
        str -- 包含整个文件的字符串
    """
    command = 'git cat-file -p ' + hash_code
    child = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    ret = child.stdout.read().decode('utf-8', 'ignore')
    child.wait()
    return ret


def get_commits_in_repo(repo_dir='./'):
    """ 根据提供的repo的路径,提取出所有涉及到java文件变动的commits,
        每个commit只提取了java文件名和对应的hash短码,
        具体是读取'git log -p'命令的输出并提取必要信息.

    Arguments:
        repo_dir {str} -- 项目的目录

    Returns:
        list -- 由commit组成的list.
    """
    os.chdir(repo_dir)
    child1 = subprocess.Popen(['git', 'log', '-p'], stdout=subprocess.PIPE)
    header_start = False
    commits = []
    commit = {}
    files = []
    hash_code = ''
    message = ''
    file_pair = {}
    file1, file2 = '', ''
    line = child1.stdout.readline().decode('utf-8', 'ignore')
    count1, count2, count3 = 0, 0, 0
    while line:
        if line.startswith('commit'):
            count1 += 1
            # new commit, save the old one
            if file1 and file2:
                file_pair['file1'] = file1
                file_pair['file2'] = file2
                files.append(file_pair)
            if message and files and hash_code:
                commit['hash'] = hash_code
                commit['message'] = message.strip('\r\n')
                commit['files'] = files
            if commit:
                count2 += 1
                if is_message_contain_code(commit):
                    count3 += 1
                    commits.append(commit)
            file1, file2 = '', ''
            file_pair = {}
            message = ''
            files = []
            commit = {}
            header_start = True
            hash_code = line[7: -1]
        if header_start and line[0] in ' \r\n\t':
            message += line
        if line.startswith('diff --git'):
            # new files, save the old ones
            if file1 and file2:
                file_pair['file1'] = file1
                file_pair['file2'] = file2
                files.append(file_pair)
            file1, file2 = '', ''
            file_pair = {}
            header_start = False
            lt = line[:-1].split(' ')
            if len(lt) == 4 and lt[-2].endswith('.java') and \
                    lt[-1].endswith('.java'):
                file1 = lt[-2][2:]
                file2 = lt[-1][2:]
        if line.startswith('index') and file1 and file2:
            index = line.split(' ')[1]
            indexs = index.split('..')
            if len(indexs) == 2:
                file1 = file1 + '\t' + indexs[0]
                file2 = file2 + '\t' + indexs[1]
        line = child1.stdout.readline().decode('utf-8', 'ignore')
    json.dump(commits, open("/mnt/data1/kingxu/commits.json", 'w'))
    print("All no-merges commits: {}".format(count1))
    print("Commits with java file: {}".format(count2))
    print("Commits message contain code: {}".format(count3))
    return commits


def write_files_in_directory(commits, base_path):
    """ 将commits中的每组文件对提取到base_path指定的文件夹中,
        给文件对赋一个index,并以index为文件名存储两个文件

    Arguments:
        commits {list} -- 由get_commits_in_repo函数返回的列表
        base_path {string} -- 以string指定的文件路径
    """
    index = 1
    for commit in commits:
        for file_pair in commit['files']:
            file1, file2 = file_pair['file1'], file_pair['file2']
            l1, l2 = file1.split('\t'), file2.split('\t')
            if len(l1) == 2 and len(l2) == 2:
                f1_content = get_file_contents_by_hash(l1[1])
                f2_content = get_file_contents_by_hash(l2[1])
                if f1_content and f2_content:
                    file_pair['index'] = index
                    dir = os.path.join(base_path, str(index))
                    if not os.path.exists(dir):
                        os.mkdir(dir)
                    file1_name = os.path.join(dir, 'old.java')
                    file2_name = os.path.join(dir, 'new.java')
                    with open(file1_name, 'w') as f1:
                        f1.write(f1_content)
                    with open(file2_name, 'w') as f2:
                        f2.write(f2_content)
                    index += 1
    json_file = os.path.join(base_path, 'commits1.json')
    with open(json_file, 'w') as f:
        json.dump(commits, f)
q

def is_message_contain_code(commit):
    """ 给定一个commit,判断commit message中是否包括了代码片段的commit.
        代码片段包括class name,method name,variable name等.
        准备采用get_file_contents_by_hash提取变动的java文件的内容,
        使用pygments从java文件中获取name.
    
    Arguments:
        commit {dict} -- commits中的元素

    Returns:
        bool -- True如果包含
    """

    names, words = set(), set()
    for file_pair in commit['files']:
        file1, file2 = file_pair['file1'], file_pair['file2']
        l1, l2 = file1.split('\t'), file2.split('\t')
            if len(l1) == 2 and len(l2) == 2:
                f1_content = get_file_contents_by_hash(l1[1])
                f2_content = get_file_contents_by_hash(l2[1])
                x = highlight(f1_content, JavaLaxer(), RawTokenFormatter())
                for y in str(x, encoding='utf-8').splitlines():
                    ys = y.split('\t'):
                    if ys[0].startswith('Token.Name') and \
                        ys[0] != 'Token.Name.Decorator':
                        names.add(eval(ys[1]))
                x = highlight(f2_content, JavaLaxer(), RawTokenFormatter())
                for y in str(x, encoding='utf-8').splitlines():
                    ys = y.split('\t'):
                    if ys[0].startswith('Token.Name') and \
                        ys[0] != 'Token.Name.Decorator':
                        names.add(eval(ys[1]))
    message = commit['message'].splitlines()[0]
    pattern = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')
    words = set(pattern.findall(message))
    return words.intersection(names)