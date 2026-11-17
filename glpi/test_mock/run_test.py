import subprocess, sys, os, json, collections
import mock_glpi
srv = mock_glpi.serve(8765)
url = "http://127.0.0.1:8765"
def run(*extra):
    r = subprocess.run([sys.executable, "../glpi_import.py", "--url", url, "--state", "/tmp/etat_test.json"] + list(extra), capture_output=True, text=True)
    return r.returncode, r.stdout
if os.path.exists("/tmp/etat_test.json"): os.remove("/tmp/etat_test.json")
code, out = run("--user-token", "MAUVAIS"); print("mauvais jeton -> code", code, "|", out.strip()[:0] or "erreur attendue")
code, out = run("--user-token", "BONJETON", "--limit", "3"); print("essai 3 elements -> code", code, "| créés:", out.count("cree "))
code, out = run("--user-token", "BONJETON"); print("complet -> code", code, "| créés:", out.count("cree "), "| échecs:", out.count("ECHEC"))
print(out.strip().splitlines()[-1])
code, out = run("--user-token", "BONJETON"); print("reprise -> code", code, "| créés:", out.count("cree "), "| échecs:", out.count("ECHEC"))
print(out.strip().splitlines()[-1])
c = collections.Counter(t for t, n in mock_glpi.STORE); print("total en base simulée:", len(mock_glpi.STORE), dict(c))
print("doublons:", len(mock_glpi.STORE) - len(set(n for t, n in mock_glpi.STORE)))
