import base64, json, os, sys, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.github.com"
tok = open(os.path.join(HERE, "token.txt"), encoding="utf-8").read().strip()
owner, repo = "Maruu1", "xy-content"
branch = "main"

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("User-Agent", "cleanup")
    if data: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)

targets = ["keys/catalog_private.pem", "keys/catalog_public.pem", "keys/catalog_public_b64.txt"]
for rel in targets:
    p = "/repos/%s/%s/contents/%s?ref=%s" % (owner, repo, rel, branch)
    st, cur = api("GET", p)
    if st != 200:
        print("SKIP %-34s GET %s" % (rel, st)); continue
    sha = cur.get("sha")
    st2, resp = api("DELETE", "/repos/%s/%s/contents/%s" % (owner, repo, rel),
                    {"message": "security: remove leaked key material", "sha": sha, "branch": branch})
    print(("OK   " if st2 == 200 else "FAIL ") + "%-34s %s %s" % (rel, st2, "" if st2 == 200 else resp))