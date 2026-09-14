"""Run CLASS-aDM on the generated .ini files and organize outputs."""
import subprocess
from pathlib import Path
from config import load_config

CLASS_OUT = Path("output/class")

def run_one(class_exe, ini_path):
  """Run CLASS on a single .ini file."""
  ini_path = Path(ini_path)
  if not Path(class_exe).exists():
    raise FileNotFoundError(f"CLASS binary not found at '{class_exe}' "
                            f"(check paths.class_exe in config.yaml)")
  if not ini_path.exists():
    raise FileNotFoundError(f"CLASS .ini not found: {ini_path} "
                            f"(run generate_class_ini first)")

  print(f"[CLASS] running {ini_path.name} ...")
  result = subprocess.run(
        [str(class_exe), str(ini_path)],
        capture_output=True, text=True,
  )
  if result.returncode != 0:
    print(result.stdout[-2000:])
    print(result.stderr[-2000:])
    raise RuntimeError(f"CLASS failed on {ini_path.name} "
                       f"(exit code {result.returncode}) — see output above")
  print(f"[CLASS] finished {ini_path.name}")
  return result


def run_class(cfg):
    class_exe = cfg["paths"]["class_exe"]
    name = cfg["run"]["name"]
    for gauge in ("newtonian", "synchronous"):
        ini_path = CLASS_OUT / f"{name}_{gauge}.ini"
        run_one(class_exe, ini_path)
    print("[CLASS] runs complete.")


if __name__ == "__main__":
    cfg = load_config()
    run_class(cfg)