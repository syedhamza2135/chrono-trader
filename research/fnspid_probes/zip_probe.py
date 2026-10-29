"""List a remote zip's contents with HTTP range requests (no full download), and read a few members.

Usage: python -I zip_probe.py <url> <out_dir> [TICKER ...]
"""
import io
import os
import sys
import urllib.request
import zipfile


class RangeFile:
    def __init__(self, url):
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as resp:
            self.url = resp.geturl()
            self.size = int(resp.headers["Content-Length"])
        self.pos = 0
        self.fetched = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        self.pos += len(data)
        self.fetched += len(data)
        return data


def main():
    url, out_dir, wanted = sys.argv[1], sys.argv[2], [t.upper() for t in sys.argv[3:]]
    f = RangeFile(url)
    z = zipfile.ZipFile(f)
    names = z.namelist()
    print(f"zip size {f.size:,} bytes; {len(names)} members; fetched {f.fetched:,} bytes to list them")
    print("first members:", names[:8])
    stems = {os.path.splitext(os.path.basename(n))[0].upper(): n for n in names if not n.endswith("/")}
    print("distinct tickers:", len(stems))
    present = [t for t in wanted if t in stems]
    missing = [t for t in wanted if t not in stems]
    print("present:", present)
    print("missing:", missing)
    os.makedirs(out_dir, exist_ok=True)
    for t in present:
        info = z.getinfo(stems[t])
        data = z.read(info)
        path = os.path.join(out_dir, f"{t}.csv")
        open(path, "wb").write(data)
        lines = data.decode("utf-8", errors="replace").splitlines()
        first, last = lines[1].split(",")[0], lines[-1].split(",")[0]
        print(f"{t}: {len(lines) - 1} rows, {last} to {first}; header: {lines[0]}")


if __name__ == "__main__":
    main()
