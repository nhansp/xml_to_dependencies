#!/usr/bin/env python3

import xml.etree.ElementTree as et
import json
import sys

depname = 'evolution'
known_remotes = {
    "github-non-los": "https://github.com",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",
    "aosp": "https://android.googlesource.com",
    "github": "..",
    "private": "ssh://git@github.com",
    "evo": "https://github.com/Evolution-X",
    "evo-devices": "https://github.com/Evolution-X-Devices",
    "evo-bitbucket": "https://bitbucket.com/evo-x",
    "evo-main": "https://git.mainlining.org/EvolutionX",
    "evo-gitlab": "https://gitlab.com/EvoX",
    "evo-codeberg": "https://codeberg.org/Evolution-X",
}
xml_remotes = {}
other_tags_dt = []

def SortDict(d: dict) -> dict:
    ord = [
        'repository',
        'target_path',
        'branch',
        'remote',
        'clone_depth'
    ]
    u = {}
    for k in ord:
        if k in d: u[k] = d[k]
    return u

def FormatDict(d: dict) -> dict:
    p = {
        'name': 'repository',
        'path': 'target_path',
        'remote': 'remote',
        'revision': 'branch',
        'clone-depth': 'clone_depth'
    }
    ans = {}
    for x in d: 
        if (x in p.keys()):
            if x == 'remote':
                print(x, d[x])
                if (d[x] not in xml_remotes.keys()):
                    ans[p[x]] = (d[x] if (d[x] in known_remotes.keys())
                                else '!!!!!!idk')
                else:
                    for u, v in known_remotes.items():
                        if (xml_remotes[d[x]] == v):
                            ans[p[x]] = u
                            break
                    if p[x] not in ans: ans[p[x]] = d[x]
            else: ans[p[x]] = d[x]
    return SortDict(ans)

def OtherTags(tagname: str, d: dict):
    f = {'tagname': tagname}
    for u, v in d.items(): f[u] = v
    other_tags_dt.append(f)

def Parser(fn: str):
    a = []
    for entries in et.parse(fn).getroot():
        u, v = entries.tag, entries.attrib
        if u == 'project': a.append(FormatDict(v))
        elif u == 'remote': xml_remotes[v['name']] = v['fetch']
        else: OtherTags(u, v)
    fi = a
    if (len(other_tags_dt) > 0): fi = [('unknown_tags', other_tags_dt)] + a
    return json.dumps(fi, indent=2)

if len(sys.argv) > 1:
    filename = sys.argv[1]
    try:
        with open(f'{depname}.dependencies', 'w') as _: 
            _.write(Parser(filename))
            print(xml_remotes)
    except FileNotFoundError:
        print(f'Error: "{filename}" not found')
else:
    print(f'Usage: python {sys.argv[0]} <filename>')
