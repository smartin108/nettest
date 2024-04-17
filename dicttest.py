import json

server_def = """
{
    "obtained_local_time": "2022-05-18T18:45:02.335676",
    "obtained": "2022-05-18T22:45:02.335676",
    "servers":
    {
        "wan": "52.144.115.26",
        "gateway": "52.144.115.1"
    }
}
"""

d = json.loads(server_def)
print(d)
s = d.get('servers')
print(s)
for ss in s:
    if ss == 'wan':
        print(s[ss])
