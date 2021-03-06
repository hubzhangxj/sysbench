#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pdb
import re
import json
from caliper.server.parser_process import parser_log

SYSBENCH_RESULT_NAME_LATENCY = 'sysbench latency'
NA_UNIT = 'NA'
SECONDS_UNIT = 'seconds'
MS_UNIT = 'milliseconds'
RESPONSE_TIME_TOKENS = ['min', 'avg', 'max', 'percentile']

def sysbench_oltp_parser(content, outfp):

    sysbench_dic = {}
    response_times = {}

    seen_general_statistics = False
    seen_response_time = False

    for line in content.splitlines():
        if re.search('General\s+statistics:', line):
            seen_general_statistics = True
            continue
        if seen_general_statistics:
            if re.match('^ +response time:.*', line):
                seen_response_time = True
                continue

        if seen_general_statistics and seen_response_time:
            for token in RESPONSE_TIME_TOKENS:
                search_string = '.*%s: +(.*)ms' % token
                if re.findall(search_string, line):
                    response_times[token] = float(re.findall(search_string,
                                                    line)[0])
                    sysbench_dic[token] = response_times[token]

    for token in RESPONSE_TIME_TOKENS:
        metric_name = '%s %s' % (SYSBENCH_RESULT_NAME_LATENCY, token)

        metric_name = '%s' % (metric_name)
        outfp.write(metric_name + '  ' + str(response_times[token]) + ' ' +
                    MS_UNIT + '\n')
    return sysbench_dic

def sysbench_cpu_parser(content,outfp):
    result = 0
    dic = {}
    dic['cpu_sincore'] = {}
    dic['cpu_multicore'] = {}
    dic['cpu_sincore']['sincore_misc'] = {}
    dic['cpu_multicore']['multicore_misc'] = {}
    dic['cpu_sincore']['sincore_misc']['sysbench_prime'] = 0
    dic['cpu_multicore']['multicore_misc']['sysbench_prime'] = 0
    contents = content.split("evaluation benchmark")[1].split("~/caliper")[0]
    version = re.search(r'(sysbench \d+\.\d+: .*)',content)
    outfp.write(version.group(1))
    outfp.write(contents)
    contents = content.split("execution time (avg/stddev)")
    for item in contents:
        if re.search(r'Number of threads:',item):
            if re.search(r'Number of threads: 1\n',item):
                result = re.search(r'\s+total time:\s+(\d+\.\d+)s',item)
                dic['cpu_sincore']['sincore_misc']['sysbench_prime'] = result.group(1)
            else:
                result = re.search(r'\s+total time:\s+(\d+\.\d+)s',item)
                dic['cpu_multicore']['multicore_misc']['sysbench_prime'] = result.group(1)
    return dic

def sysbench_parser(content,outfp):
    if re.search("\[test: sysbench_cpu\]",content):
       result = sysbench_cpu_parser(content,outfp)
    else:
       result = sysbench_oltp_parser(content, outfp)
    return result

def sysbench(filePath, outfp):
    cases = parser_log.parseData(filePath)
    result = []
    for case in cases:
        caseDict = {}
        caseDict[parser_log.BOTTOM] = parser_log.getBottom(case)
        titleGroup = re.search('\[([\S\ ]+)\]\n', case)
        if titleGroup != None:
            caseDict[parser_log.TOP] = titleGroup.group(0)
            caseDict[parser_log.BOTTOM] = parser_log.getBottom(case)
        tables = []
        tableContent = {}
        centerTopGroup = re.search("(sysbench\s\d[\S\ ]+\n)", case)
        tableContent[parser_log.CENTER_TOP] = centerTopGroup.groups()[0]
        tableGroup = re.search("Threads started\!([\s\S]+)\/\d+\.\d+\n", case)
        if tableGroup is not None:
            tableGroupContent_temp = tableGroup.groups()[0].strip()
            tableGroupContent = re.sub('\+?sysbench[\-\ ]?0.5[\S\ ]+\n', '', tableGroupContent_temp)
            tableGroupContent_temp2 = re.sub('\+', '', tableGroupContent)
            table = parser_log.parseTable(tableGroupContent_temp2, ":{1,}")
            tableContent[parser_log.I_TABLE] = table
        tables.append(tableContent)
        caseDict[parser_log.TABLES] = tables
        result.append(caseDict)
    outfp.write(json.dumps(result))
    return result
if __name__ == "__main__":
    infile = "sysbench_output.log"
    outfile = "sysbench_json.txt"
    outfp = open(outfile, "a+")
    sysbench(infile, outfp)
    outfp.close()
